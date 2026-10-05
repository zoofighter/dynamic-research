import os
import sys
import json
import time
import glob
from pathlib import Path
from datetime import datetime
import streamlit as st

# 루트 디렉토리 경로 추가
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.providers.search import get_search_provider
from src.providers.scraper import get_scraper_provider
from src.providers.llm import get_chat_model
from src.utils.dedup import deduplicate_results
from src.utils.config import get_config
from src.engines.baseline_engine import BaselineDataEngine
from src.engines.llamaindex_engine import LlamaIndexDataEngine
from scripts.run_local_dls import run_dls

st.set_page_config(
    page_title="DLS Dynamic Deep Research Studio",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E88E5, #7E57C2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 18px;
        border-left: 4px solid #1E88E5;
        margin-bottom: 10px;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ 엔진 및 모델 설정")
    provider_option = st.selectbox(
        "기본 LLM 프로바이더",
        options=["opencode", "gemini", "ollama"],
        index=0,
        help="OpenCode Muse Spark는 로컬 CLI/API 연동으로 토큰 비용이 0원(무료)입니다."
    )

    if provider_option == "opencode":
        model_name = st.text_input("모델명", value="opencode/muse-spark-1.3-contributor-free")
        st.success("🟢 토큰 비용: 0원 (OpenCode Muse Spark)")
    elif provider_option == "gemini":
        model_name = st.text_input("모델명", value="gemini-2.5-flash")
    else:
        model_name = st.text_input("모델명", value="qwen2.5:14b")

    engine_option = st.radio(
        "DLS 데이터 엔진",
        options=["LlamaIndex (청킹 & 동적 재순위화)", "Baseline (프롬프트 스터핑)"],
        index=0,
        help="LlamaIndex 엔진은 문장 단위 분할과 팩트 밀도 필터링을 통해 환각을 억제합니다."
    )

    max_pages = st.slider("검색 수집 문서 수 (Depth)", min_value=2, max_value=8, value=4)

    st.markdown("---")
    st.markdown("### 📡 수집 파이프라인")
    st.markdown("- **검색**: DuckDuckGo News + Google RSS")
    st.markdown("- **추출**: Trafilatura (로컬 본문 파서)")
    st.markdown("- **인용**: [^번호] 문장 단위 팩트 매핑")

# Title Header
st.markdown("<div class='main-title'>🔬 DLS Dynamic Deep Research Studio</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>뉴스 전용 이중 수집기(DuckDuckGo + Google RSS)와 LlamaIndex 기반 자율 리서치 플랫폼</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "💡 1. 토픽 발굴 & 목차 생성",
    "🚀 2. DLS 심층 리서치",
    "📊 3. A/B 엔진 벤치마크",
    "📑 4. 완성된 리포트 열람실"
])

# ========================================================
# TAB 1: 토픽 발굴 & 목차 생성기
# ========================================================
with tab1:
    st.markdown("### 📡 실시간 구글 뉴스 RSS 스캔 및 AI 추천 토픽 발굴")
    
    col_kw, col_scan_btn = st.columns([3, 1])
    with col_kw:
        scan_keyword = st.text_input(
            "트렌드 탐색 키워드 (원하는 산업/기술 키워드로 자유롭게 변경 가능)",
            value="반도체 OR AI OR 에이전트 OR 빅테크",
            help="이 키워드로 구글 뉴스 RSS를 실시간 조회하여 최신 속보를 수집하고 추천 토픽을 자동 생성합니다."
        )
    with col_scan_btn:
        st.write("")
        st.write("")
        scan_clicked = st.button("🔍 최신 뉴스 스캔 & 토픽 추출", type="primary", use_container_width=True)

    if scan_clicked:
        with st.spinner("구글 뉴스 RSS 스캔 및 AI 트렌드 토픽 클러스터링 중..."):
            try:
                from src.providers.rss import NewsRSSProvider
                rss_provider = NewsRSSProvider()
                articles = rss_provider.fetch_headlines(scan_keyword, limit=12)
                scanned_titles = [f"[{a.source}] {a.title}" for a in articles]
                st.session_state["scanned_titles"] = scanned_titles
                
                # LLM을 활용해 실시간 헤드라인으로부터 5대 최적 추천 토픽 자동 생성
                if scanned_titles:
                    llm = get_chat_model(provider=provider_option, model=model_name)
                    headlines_prompt_text = "\n".join(scanned_titles[:8])
                    cluster_prompt = f"""당신은 산업 분석 수석 에디터입니다.
아래 실시간 최신 뉴스 헤드라인들을 분석하여, 가장 산업적 파급력이 크고 심층 리서치가 시급한 '핵심 리서치 주제 5개'를 명확하고 완성된 단일 문장으로 요약하여 JSON 배열로 출력하세요.

[실시간 뉴스 헤드라인]
{headlines_prompt_text}

반드시 아래 JSON 배열 형식으로만 응답하세요 (코드블록 없이):
[
  "추천 토픽 1 제목",
  "추천 토픽 2 제목",
  "추천 토픽 3 제목",
  "추천 토픽 4 제목",
  "추천 토픽 5 제목"
]
"""
                    res = llm.invoke(cluster_prompt)
                    raw = res.content if isinstance(res.content, str) else str(res.content)
                    import re
                    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
                    if match:
                        generated_topics = json.loads(match.group(0))
                        st.session_state["dynamic_candidate_topics"] = generated_topics
                        st.success(f"최신 뉴스 {len(scanned_titles)}건 분석 기반 5대 추천 토픽 자동 갱신 완료!")
                    else:
                        st.session_state["dynamic_candidate_topics"] = [a.title for a in articles[:5]]
                else:
                    st.warning("수집된 뉴스가 없습니다.")
            except Exception as e:
                st.error(f"스캔 실패: {e}")

    if "scanned_titles" in st.session_state and st.session_state["scanned_titles"]:
        with st.expander(f"📰 감지된 실시간 뉴스 헤드라인 원문 ({len(st.session_state['scanned_titles'])}건)", expanded=False):
            for t in st.session_state["scanned_titles"]:
                st.markdown(f"- {t}")

    st.markdown("---")
    st.markdown("### 📝 추천 리서치 토픽 & 다각도 아웃라인(A/B/C/D) 제안")
    
    # 세션 상태에 저장된 동적 토픽이 있으면 우선 적용, 없으면 기본값
    default_topics = [
        "마이크론 12단 HBM3E 엔비디아 공급 및 양산 일정",
        "엔비디아 차세대 GB200 서버 랙 수랭 쿨링 및 발열 동향",
        "삼성전자 파운드리 2나노 공정 수율 및 엑시노스 탑재 현황",
        "SK하이닉스 M15X 팹 증설 및 차세대 HBM4 로드맵",
        "반도체 유리 기판(Glass Substrate) 상용화 경쟁 및 인텔·삼성 협력"
    ]
    candidate_topics = st.session_state.get("dynamic_candidate_topics", default_topics)

    col_topic_sel, col_topic_reset = st.columns([4, 1])
    with col_topic_sel:
        is_dynamic = "dynamic_candidate_topics" in st.session_state
        badge = "🟢 [실시간 뉴스 자동 추출]" if is_dynamic else "⚪ [기본 추천 목록]"
        selected_topic = st.selectbox(
            f"리서치할 토픽 선택 {badge}",
            options=candidate_topics,
            help="상단 '최신 뉴스 스캔'을 실행하면 최신 속보 헤드라인에 맞추어 이 목록이 실시간 자동 갱신됩니다."
        )
    with col_topic_reset:
        st.write("")
        st.write("")
        if st.button("🔄 기본 목록 복원", use_container_width=True, help="기본 반도체 5대 목록으로 초기화합니다."):
            st.session_state.pop("dynamic_candidate_topics", None)
            st.rerun()

    custom_topic = st.text_input("또는 직접 토픽 입력 (원하는 주제를 자유롭게 작성)", value="")
    final_topic = custom_topic.strip() if custom_topic.strip() else selected_topic

    col_mode, col_btn = st.columns([3, 2])
    with col_mode:
        outline_mode = st.radio(
            "목차 관점 모드 선택",
            options=[
                "다각도 4대 관점 (A/B/C/D - 비즈니스 / 기술 / 생태계 / 규제·전망)",
                "핵심 2대 관점 (A/B - 비즈니스 vs 기술)"
            ],
            index=0,
            horizontal=False
        )
    with col_btn:
        st.write("")
        is_4_mode = "4대" in outline_mode
        btn_label = "📋 4대 목차 후보(A/B/C/D) 생성" if is_4_mode else "📋 2대 목차 후보(A/B) 생성"
        gen_clicked = st.button(btn_label, type="primary", use_container_width=True)

    if gen_clicked:
        with st.spinner(f"'{final_topic}'에 대한 {'4대(A/B/C/D)' if is_4_mode else '2대(A/B)'} 심층 목차 생성 중..."):
            llm = get_chat_model(provider=provider_option, model=model_name)
            
            if is_4_mode:
                prompt = f"""당신은 수석 리서치 디렉터입니다.
주제: {final_topic}

위 주제의 특성(예: 반도체 하드웨어, AI 소프트웨어/에이전트, 딥테크, 플랫폼 비즈니스 등)을 심층 분석하여, 서로 다른 4가지 차별화된 심층 분석 관점의 목차(Outline A, B, C, D)를 각각 4개 핵심 섹션으로 제안하세요.

[4대 관점 가이드]
- Outline A: 산업 및 비즈니스 전략 관점 (시장 규모, 고객사 포지셔닝, 수익/가격 모델, GTM 전략)
- Outline B: 기술 아키텍처 및 공정/엔지니어링 관점 (하드웨어 공정/수율 또는 소프트웨어 모델 구조/성능 벤치마크/비용)
- Outline C: 경쟁 구도 및 생태계/밸류체인 관점 (빅테크 경쟁, 파트너십, 시장 대체/보완 효과, 밸류체인 재편)
- Outline D: 규제·정책·투자 리스크 및 미래 전망 관점 (규제/법적 이슈, 안전성/저작권, 투자 판단 요인 및 1~3년 전망)

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "topic": "{final_topic}",
  "outlines": [
    {{
      "id": "A",
      "theme": "산업 및 비즈니스 전략 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }},
    {{
      "id": "B",
      "theme": "기술 아키텍처 및 공정/엔지니어링 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }},
    {{
      "id": "C",
      "theme": "경쟁 구도 및 생태계/밸류체인 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }},
    {{
      "id": "D",
      "theme": "규제·정책·투자 리스크 및 미래 전망 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }}
  ]
}}
"""
            else:
                prompt = f"""당신은 수석 리서치 디렉터입니다.
주제: {final_topic}

위 주제에 대해 2가지 상이한 분석 관점의 목차(Outline A, Outline B)를 각각 4개 핵심 섹션으로 제안하세요.
Outline A: 산업 및 비즈니스 전략 관점
Outline B: 기술 사양 및 엔지니어링/수율 관점

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "topic": "{final_topic}",
  "outlines": [
    {{
      "id": "A",
      "theme": "산업 및 비즈니스 전략 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }},
    {{
      "id": "B",
      "theme": "기술 사양 및 엔지니어링/수율 관점",
      "sections": [
        {{"title": "섹션 1 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 2 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 3 제목", "target_questions": ["질문 1", "질문 2"]}},
        {{"title": "섹션 4 제목", "target_questions": ["질문 1", "질문 2"]}}
      ]
    }}
  ]
}}
"""
            res = llm.invoke(prompt)
            raw = res.content if isinstance(res.content, str) else str(res.content)
            import re
            cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    outline_obj = json.loads(match.group(0))
                    st.session_state["current_outlines"] = outline_obj
                    st.success(f"목차 후보 {'4대(A/B/C/D)' if is_4_mode else '2대(A/B)'} 생성 완료!")
                except Exception as e:
                    st.error(f"JSON 파싱 실패: {e}")
            else:
                st.warning("목차 텍스트 응답 수신:")
                st.code(cleaned)

    if "current_outlines" in st.session_state:
        outlines = st.session_state["current_outlines"].get("outlines", [])
        emojis = {"A": "🅰️", "B": "🅱️", "C": "🅲", "D": "🅳"}
        
        # 2열 그리드로 렌더링
        for row_start in range(0, len(outlines), 2):
            cols = st.columns(2)
            for idx, outline_item in enumerate(outlines[row_start:row_start+2]):
                col = cols[idx]
                oid = outline_item.get("id", chr(65 + row_start + idx))
                theme = outline_item.get("theme", f"Outline {oid}")
                emoji = emojis.get(oid, "📌")
                with col:
                    with st.container(border=True):
                        st.markdown(f"#### {emoji} Outline {oid}: {theme}")
                        for s in outline_item.get("sections", []):
                            st.markdown(f"**• {s.get('title')}**")
                            for q in s.get("target_questions", []):
                                st.markdown(f"  - {q}")
                        if st.button(f"✅ Outline {oid} 최종 승인 및 확정", key=f"btn_approve_{oid}", use_container_width=True):
                            approved = {
                                "topic": final_topic,
                                "theme": theme,
                                "sections": outline_item.get("sections")
                            }
                            os.makedirs("temp", exist_ok=True)
                            with open("temp/latest_approved_outline.json", "w", encoding="utf-8") as f:
                                json.dump(approved, f, ensure_ascii=False, indent=2)
                            st.success(f"Outline {oid} ({theme}) 승인 완료! (temp/latest_approved_outline.json 저장)")

# ========================================================
# TAB 2: DLS 심층 리서치 파이프라인
# ========================================================
with tab2:
    st.markdown("### 🚀 DLS 자율 심층 리서치 실행 파이프라인")
    
    approved_topic = final_topic
    has_outline = False
    if os.path.exists("temp/latest_approved_outline.json"):
        try:
            with open("temp/latest_approved_outline.json", "r", encoding="utf-8") as f:
                saved_outline = json.load(f)
                if saved_outline.get("topic"):
                    approved_topic = saved_outline["topic"]
                    has_outline = True
                    st.info(f"📑 현재 사전 승인된 목차 연동 중: **'{saved_outline.get('theme')}'** (주제: {approved_topic})")
        except:
            pass

    research_topic = st.text_input("리서치 실행 주제", value=approved_topic)
    use_approved_outline = st.checkbox("사전 승인된 목차 파일 연동 (temp/latest_approved_outline.json)", value=has_outline)

    if has_outline and use_approved_outline:
        with st.expander(f"📑 승인된 목차 구성 ({len(saved_outline.get('sections', []))}개 핵심 섹션) 미리보기", expanded=True):
            st.markdown(f"**분석 관점/테마**: {saved_outline.get('theme', '')}")
            for idx, s in enumerate(saved_outline.get("sections", []), 1):
                st.markdown(f"**{idx}. {s.get('title')}**")
                for q in s.get("target_questions", []):
                    st.markdown(f"  - {q}")

    pipeline_mode = st.radio(
        "실행 파이프라인 엔진 모드",
        options=[
            "🌟 LangGraph DLS 자율 심층 에이전트 (섹션별 독립 탐색 & 반추 루프 - 압도적 고밀도 심층 리포트)",
            "⚡ DLS 고속 리서치 (단일 패스 일괄 합성 - 빠른 확인용)"
        ],
        index=0,
        help="LangGraph 에이전트는 승인된 목차의 각 섹션마다 검색-스크랩-반추(Reflection) 루프를 돌며 30~50KB 분량의 완결 보고서를 자율 합성합니다."
    )

    if st.button("🚀 DLS 심층 리서치 시작", type="primary"):
        status_box = st.status("🔍 리서치 파이프라인 가동 중...", expanded=True)
        try:
            gen_report_path = None
            if "LangGraph DLS" in pipeline_mode:
                from src.graphs.dls_research_graph import dls_research_app
                from src.utils.config import get_config
                
                cfg = get_config()
                run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                thread_id = f"thread_web_{run_id}"
                g_config = {"configurable": {"thread_id": thread_id}}
                
                sections = saved_outline.get("sections", []) if (use_approved_outline and has_outline) else []
                g_initial_state = {
                    "topic": research_topic,
                    "outline": sections,
                    "config": cfg,
                    "run_id": run_id
                }
                
                status_box.write("🤖 [LangGraph Stage 2] DLS 자율 심층 에이전트 초기화 완료...")
                final_state = None
                for event in dls_research_app.stream(g_initial_state, g_config, stream_mode="values"):
                    final_state = event
                    curr_sec = event.get("current_section", {})
                    curr_title = curr_sec.get("title", "")
                    r_count = event.get("reflection_count", 0)
                    if curr_title:
                        status_box.write(f"📖 섹션 자율 탐색 및 반추 중: **{curr_title}** (Reflection 루프: {r_count}회)")
                
                gen_report_path = final_state.get("output_path") if final_state else None
            else:
                status_box.write("1️⃣ 뉴스 전용 이중 수집기(DuckDuckGo + Google RSS) 가동...")
                outline_file = "temp/latest_approved_outline.json" if use_approved_outline else None
                gen_report_path = run_dls(
                    topic=research_topic,
                    max_pages=max_pages,
                    provider=provider_option,
                    model=model_name,
                    outline_path=outline_file
                )

            status_box.update(label="✅ DLS 자율 심층 리서치 완료!", state="complete", expanded=False)
            st.success("심층 리서치 완료! 아래에서 생성된 리포트를 바로 확인하실 수 있습니다.")
            if gen_report_path and os.path.exists(gen_report_path):
                with open(gen_report_path, "r", encoding="utf-8") as rf:
                    res_text = rf.read()
                st.download_button(
                    label="📥 마크다운 리포트 다운로드",
                    data=res_text,
                    file_name=os.path.basename(gen_report_path),
                    mime="text/markdown"
                )
                st.markdown("---")
                st.markdown(res_text)
        except Exception as e:
            status_box.update(label="❌ 실행 오류 발생", state="error")
            st.error(f"오류: {e}")

# ========================================================
# TAB 3: A/B 엔진 벤치마크
# ========================================================
with tab3:
    st.markdown("### 📊 Baseline (Prompt Stuffing) vs LlamaIndex (SentenceSplitter & Rerank) A/B 벤치마크")
    st.markdown("원시 본문 직접 주입 방식과 LlamaIndex 문장 단위 청킹 & 동적 재순위화 방식의 속도, 비용, 인용 정밀도를 비교합니다.")

    bm_topic = st.text_input("벤치마크 테스트 주제", value="마이크론 12단 HBM3E 엔비디아 공급 및 양산")
    bm_question = st.text_input("벤치마크 질문", value="마이크론의 12단 HBM3E 공급 시점과 엔비디아 납품 관련 최신 팩트는 무엇인가?")

    if st.button("🔬 A/B 벤치마크 즉시 실행"):
        with st.spinner("두 엔진(Baseline vs LlamaIndex)을 실시간 문서로 평가 중..."):
            from scripts.benchmark_runner import run_benchmark
            run_benchmark(
                topic=bm_topic,
                question=bm_question,
                provider=provider_option,
                model=model_name,
                max_docs=3,
                output_path="output/benchmark_report.md"
            )
            st.success("A/B 벤치마크 평가 완료! 결과가 output/benchmark_report.md에 저장되었습니다.")

    if os.path.exists("output/benchmark_report.md"):
        st.markdown("---")
        with open("output/benchmark_report.md", "r", encoding="utf-8") as f:
            bm_md = f.read()
        st.markdown(bm_md)

# ========================================================
# TAB 4: 완성된 리포트 열람실
# ========================================================
with tab4:
    st.markdown("### 📑 생성된 심층 리포트 아카이브")
    report_files = sorted(glob.glob("output/*.md"), key=os.path.getmtime, reverse=True)
    if not report_files:
        st.info("아직 생성된 리포트가 없습니다. 2번 탭에서 심층 리서치를 실행해보세요.")
    else:
        selected_file = st.selectbox("열람할 리포트 파일 선택", options=report_files)
        if selected_file and os.path.exists(selected_file):
            with open(selected_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            st.download_button(
                label="📥 마크다운 파일 다운로드",
                data=content,
                file_name=os.path.basename(selected_file),
                mime="text/markdown"
            )
            st.markdown("---")
            st.markdown(content)
