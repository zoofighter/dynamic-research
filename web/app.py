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
    st.markdown("### 📡 실시간 구글 뉴스 RSS 스캔 및 후보 토픽 발굴")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔍 최신 뉴스 트렌드 스캔", type="primary", use_container_width=True):
            with st.spinner("구글 뉴스 RSS 및 최신 산업 이슈를 스캔 중..."):
                try:
                    from src.providers.rss import NewsRSSProvider
                    rss_provider = NewsRSSProvider()
                    articles = rss_provider.fetch_headlines("반도체 OR AI OR HBM", limit=10)
                    scanned_titles = [f"[{a.source}] {a.title}" for a in articles]

                    st.session_state["scanned_titles"] = scanned_titles
                    st.success(f"최신 뉴스 {len(scanned_titles)}건 감지 완료!")
                except Exception as e:
                    st.error(f"스캔 실패: {e}")

    with col2:
        if "scanned_titles" in st.session_state:
            st.markdown("**최근 수집된 헤드라인:**")
            for t in st.session_state["scanned_titles"][:5]:
                st.markdown(f"- {t}")

    st.markdown("---")
    st.markdown("### 📝 추천 리서치 토픽 & 다각도 아웃라인(A/B) 제안")
    
    candidate_topics = [
        "마이크론 12단 HBM3E 엔비디아 공급 및 양산 일정",
        "엔비디아 차세대 GB200 서버 랙 수랭 쿨링 및 발열 동향",
        "삼성전자 파운드리 2나노 공정 수율 및 엑시노스 탑재 현황",
        "SK하이닉스 M15X 팹 증설 및 차세대 HBM4 로드맵",
        "반도체 유리 기판(Glass Substrate) 상용화 경쟁 및 인텔·삼성 협력"
    ]
    
    selected_topic = st.selectbox("리서치할 토픽 선택 또는 직접 입력", options=candidate_topics)
    custom_topic = st.text_input("직접 토픽 입력 시 여기에 작성 (비워두면 위 선택 토픽 사용)", value="")
    final_topic = custom_topic.strip() if custom_topic.strip() else selected_topic

    if st.button("📋 목차(Outline) 후보 A/B 생성"):
        with st.spinner(f"'{final_topic}'에 대한 복수 관점 목차 생성 중..."):
            llm = get_chat_model(provider=provider_option, model=model_name)
            prompt = f"""당신은 수석 리서치 디렉터입니다.
주제: {final_topic}

위 주제에 대해 2가지 상이한 분석 관점의 목차(Outline A, Outline B)를 각각 4개 핵심 섹션으로 제안하세요.
Outline A: 산업 및 비즈니스 전략 관점
Outline B: 기술 사양 및 양산/수율 관점

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
      "theme": "기술 사양 및 양산/수율 관점",
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
                    st.success("목차 후보 A/B 생성 완료!")
                except Exception as e:
                    st.error(f"JSON 파싱 실패: {e}")
            else:
                st.warning("목차 텍스트 응답 수신:")
                st.code(cleaned)

    if "current_outlines" in st.session_state:
        outlines = st.session_state["current_outlines"].get("outlines", [])
        col_a, col_b = st.columns(2)
        with col_a:
            if len(outlines) > 0:
                oa = outlines[0]
                st.markdown(f"#### 🅰️ {oa.get('theme', 'Outline A')}")
                for s in oa.get("sections", []):
                    st.markdown(f"**• {s.get('title')}**")
                    for q in s.get("target_questions", []):
                        st.markdown(f"  - {q}")
                if st.button("✅ Outline A 최종 승인 및 확정", use_container_width=True):
                    approved = {"topic": final_topic, "theme": oa.get("theme"), "sections": oa.get("sections")}
                    os.makedirs("temp", exist_ok=True)
                    with open("temp/latest_approved_outline.json", "w", encoding="utf-8") as f:
                        json.dump(approved, f, ensure_ascii=False, indent=2)
                    st.success(f"Outline A가 승인되었습니다! (temp/latest_approved_outline.json 저장 완료)")

        with col_b:
            if len(outlines) > 1:
                ob = outlines[1]
                st.markdown(f"#### 🅱️ {ob.get('theme', 'Outline B')}")
                for s in ob.get("sections", []):
                    st.markdown(f"**• {s.get('title')}**")
                    for q in s.get("target_questions", []):
                        st.markdown(f"  - {q}")
                if st.button("✅ Outline B 최종 승인 및 확정", use_container_width=True):
                    approved = {"topic": final_topic, "theme": ob.get("theme"), "sections": ob.get("sections")}
                    os.makedirs("temp", exist_ok=True)
                    with open("temp/latest_approved_outline.json", "w", encoding="utf-8") as f:
                        json.dump(approved, f, ensure_ascii=False, indent=2)
                    st.success(f"Outline B가 승인되었습니다! (temp/latest_approved_outline.json 저장 완료)")

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

    if st.button("🚀 DLS 심층 리서치 시작", type="primary"):
        status_box = st.status("🔍 리서치 파이프라인 가동 중...", expanded=True)
        try:
            status_box.write("1️⃣ 뉴스 전용 이중 수집기(DuckDuckGo + Google RSS) 가동...")
            outline_file = "temp/latest_approved_outline.json" if use_approved_outline else None
            
            # 리서치 실행
            run_dls(
                topic=research_topic,
                max_pages=max_pages,
                provider=provider_option,
                model=model_name,
                outline_path=outline_file
            )
            status_box.update(label="✅ 리서치 보고서 생성 완료!", state="complete", expanded=False)
            st.success("심층 리서치 완료! 아래 또는 '리포트 열람실' 탭에서 확인하세요.")
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
