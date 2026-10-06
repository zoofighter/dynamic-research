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

# Hot-reload src.utils.markdown_parser in long-running Streamlit processes
import importlib
import src.utils.markdown_parser
importlib.reload(src.utils.markdown_parser)
from src.utils.markdown_parser import (
    parse_report_for_dashboard,
    sections_to_markdown_outline,
    markdown_outline_to_sections
)
import src.utils.outline_history
importlib.reload(src.utils.outline_history)
from src.utils.outline_history import (
    save_outline_history,
    list_outline_history,
    load_outline_history,
    delete_outline_history,
    set_active_approved_outline,
    sync_existing_latest_to_history
)
from src.utils.bundle_packager import get_available_bundles, create_report_bundle
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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💡 1. 토픽 발굴 & 목차 생성",
    "🚀 2. DLS 심층 리서치",
    "📑 3. 완성된 리포트 열람실",
    "📊 4. A/B 엔진 벤치마크",
    "💎 5. 스마트 리포트 분석실 (Dashboard & Q&A)"
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

    # ----------------------------------------------------
    # 🎯 [옵션] 핵심 질문 (Core Questions) 설정
    # ----------------------------------------------------
    has_existing_cq = bool(st.session_state.get("core_questions_text", "").strip())
    with st.expander("🎯 핵심 질문 (Core Questions) 옵션 설정 (선택 사항 — AI 추천 또는 직접 작성)", expanded=has_existing_cq):
        st.markdown(
            "리서치를 통해 **반드시 답을 찾아야 하는 3~5가지 핵심 질문**을 설정할 수 있습니다.\n"
            "핵심 질문을 입력하면 아래 목차 생성 시 각 섹션과 세부 탐색 질문이 이 핵심 질문들을 집중 해결하도록 정밀하게 연계됩니다."
        )
        col_cq_ai, col_cq_clear = st.columns([3, 1])
        with col_cq_ai:
            if st.button("🤖 주제 맞춤 핵심 질문 AI 자동 추천 (3개)", use_container_width=True, help="현재 선택된 주제를 바탕으로 날카로운 핵심 질문 3개를 AI가 추천합니다."):
                with st.spinner(f"'{final_topic}' 맞춤 핵심 질문 3개 도출 중..."):
                    cq_llm = get_chat_model(provider=provider_option, model=model_name)
                    cq_prompt = f"""당신은 수석 테크 리서치 애널리스트입니다.
주제: {final_topic}

위 주제에 대해 리서치 리포트를 작성할 때 반드시 답을 찾아야 하는 가장 날카롭고 구체적인 핵심 질문 3개를 한국어로 작성하세요.
각 질문은 수치, 일정, 수율, 시장 점유율, 고객사 계약 등 구체적 팩트를 파고들어야 합니다.

반드시 아래와 같이 번호(1., 2., 3.)와 함께 한 줄에 하나씩 질문만 출력하세요. 다른 설명이나 머리말은 일절 생략하세요:
1. ...
2. ...
3. ..."""
                    cq_res = cq_llm.invoke(cq_prompt)
                    cq_text_raw = cq_res.content if isinstance(cq_res.content, str) else str(cq_res.content)
                    import re
                    cq_text_cleaned = re.sub(r"<think>.*?</think>", "", cq_text_raw, flags=re.DOTALL).strip()
                    st.session_state["core_questions_text"] = cq_text_cleaned
                    st.success("핵심 질문 3개가 추천되었습니다! 아래 입력창에서 확인하거나 수정할 수 있습니다.")
                    st.rerun()
        with col_cq_clear:
            if st.button("🗑️ 질문 비우기", use_container_width=True):
                st.session_state["core_questions_text"] = ""
                st.rerun()

        core_q_input = st.text_area(
            "핵심 질문 목록 (한 줄에 질문 하나씩 입력, 비워두면 AI 기본 목차 알고리즘 적용)",
            value=st.session_state.get("core_questions_text", ""),
            height=100,
            placeholder="예시:\n1. 주요 공급사 및 12단/16단 양산 일정 및 출하 규모는?\n2. 엔비디아 등 주요 고객사 퀄 승인 여부와 공급 비중은?\n3. 경쟁사 대비 공정 수율 및 발열/전력 효율 격차는?",
            help="한 줄에 질문 하나씩 입력하세요. 번호(1., 2.)는 자동으로 인식됩니다."
        )
        st.session_state["core_questions_text"] = core_q_input
        active_core_questions = [q.strip() for q in core_q_input.splitlines() if q.strip()]
        st.session_state["active_core_questions"] = active_core_questions

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
            
            active_cq = st.session_state.get("active_core_questions", [])
            core_q_prompt_block = ""
            if active_cq:
                cq_bullets = "\n".join([f"  - {q}" for q in active_cq])
                core_q_prompt_block = f"""
[사용자 정의 핵심 질문 (Core Questions) - 최우선 반영 요구사항]
다음 핵심 질문들에 대한 구체적 해답, 실증 팩트, 비교 데이터가 각 목차의 섹션과 세부 질문(target_questions)에 유기적으로 배치되도록 반드시 아웃라인을 설계하세요:
{cq_bullets}
"""

            if is_4_mode:
                prompt = f"""당신은 수석 리서치 디렉터입니다.
주제: {final_topic}
{core_q_prompt_block}
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
{core_q_prompt_block}
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
                    outline_obj["core_questions"] = active_cq
                    st.session_state["current_outlines"] = outline_obj
                    st.session_state["active_core_questions"] = active_cq
                    msg = f"목차 후보 {'4대(A/B/C/D)' if is_4_mode else '2대(A/B)'} 생성 완료! (🎯 핵심 질문 {len(active_cq)}개 반영됨)" if active_cq else f"목차 후보 {'4대(A/B/C/D)' if is_4_mode else '2대(A/B)'} 생성 완료!"
                    st.success(msg)
                except Exception as e:
                    st.error(f"JSON 파싱 실패: {e}")
            else:
                st.warning("목차 텍스트 응답 수신:")
                st.code(cleaned)

    if "current_outlines" in st.session_state:
        outlines = st.session_state["current_outlines"].get("outlines", [])
        emojis = {"A": "🅰️", "B": "🅱️", "C": "🅲", "D": "🅳"}
        
        active_cqs = st.session_state.get("active_core_questions", [])
        if active_cqs:
            with st.container(border=True):
                st.markdown("🎯 **목차 후보에 반영된 핵심 질문 (Core Questions)**")
                for cq_i, cq_txt in enumerate(active_cqs, 1):
                    st.markdown(f"**{cq_i}.** {cq_txt}")

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
                        col_app, col_edit = st.columns([1, 1])
                        with col_app:
                            if st.button(f"✅ Outline {oid} 바로 승인 및 저장", key=f"btn_approve_{oid}", use_container_width=True):
                                approved = save_outline_history(
                                    topic=final_topic,
                                    theme=theme,
                                    sections=outline_item.get("sections", []),
                                    source=f"ai_outline_{oid}",
                                    memo=f"AI 추천 Outline {oid} 채택",
                                    core_questions=st.session_state.get("active_core_questions", [])
                                )
                                st.success(f"Outline {oid} ({theme}) 승인 및 히스토리 저장 완료! (ID: {approved['id']})")
                        with col_edit:
                            if st.button(f"✏️ Outline {oid} 편집기로 열기", key=f"btn_load_{oid}", use_container_width=True):
                                st.session_state["editing_outline"] = {
                                    "topic": final_topic,
                                    "theme": theme,
                                    "core_questions": st.session_state.get("active_core_questions", []),
                                    "sections": [dict(s) for s in outline_item.get("sections", [])]
                                }
                                st.session_state["outline_editor_open"] = True
                                st.rerun()

    # 수동 목차 편집기 (Human-in-the-Loop Editor)
    st.markdown("---")
    with st.expander("✍️ 나만의 맞춤형 목차 수동 편집기 (Human-in-the-Loop Editor)", expanded=st.session_state.get("outline_editor_open", False)):
        st.markdown("AI가 제안한 목차를 불러와 수정하거나, 직접 원하는 섹션과 질문을 자유롭게 추가/삭제/편집할 수 있습니다.")
        
        if "editing_outline" not in st.session_state:
            st.session_state["editing_outline"] = {
                "topic": final_topic,
                "theme": "사용자 맞춤형 분석 관점",
                "core_questions": st.session_state.get("active_core_questions", []),
                "sections": [
                    {"section_id": "sec_0", "title": "핵심 시장 동향 및 공급망 현황", "target_questions": ["주요 공급사 및 양산 일정", "고객사 계약 및 퀄테스트 현황"]},
                    {"section_id": "sec_1", "title": "기술 사양 및 공정 수율 분석", "target_questions": ["공정 노드 및 패키징 기술", "수율 이슈 및 개선 로드맵"]}
                ]
            }
            
        edit_mode = st.radio(
            "편집 모드 선택",
            options=["📋 섹션별 폼 편집 (추천)", "📝 마크다운 텍스트 직접 입력/수정 (자유 메모장)"],
            horizontal=True,
            key="outline_edit_mode_radio"
        )
        
        cur_topic = st.text_input("목차 대상 주제", value=st.session_state["editing_outline"].get("topic", final_topic), key="edit_outline_topic")
        cur_theme = st.text_input("분석 테마/관점 명칭", value=st.session_state["editing_outline"].get("theme", "맞춤형 분석 관점"), key="edit_outline_theme")
        
        cur_editor_cq_list = st.session_state["editing_outline"].get("core_questions", [])
        cur_editor_cq_str = "\n".join(cur_editor_cq_list)
        edit_cq_input = st.text_area(
            "🎯 목표 핵심 질문 (Core Questions - 선택 사항, 줄바꿈으로 구분)",
            value=cur_editor_cq_str,
            key="edit_outline_core_questions",
            height=75,
            help="이 목차가 집중 해결하고자 하는 3~5가지 핵심 질문을 작성합니다."
        )
        editor_active_core_questions = [q.strip() for q in edit_cq_input.splitlines() if q.strip()]
        st.session_state["editing_outline"]["core_questions"] = editor_active_core_questions

        if edit_mode == "📋 섹션별 폼 편집 (추천)":
            sections = st.session_state["editing_outline"].get("sections", [])
            sec_to_remove = None
            for s_idx, sec in enumerate(sections):
                with st.container(border=True):
                    col_t, col_del = st.columns([5, 1])
                    with col_t:
                        sec["title"] = st.text_input(f"섹션 {s_idx + 1} 제목", value=sec.get("title", ""), key=f"sec_title_{s_idx}")
                    with col_del:
                        st.write("")
                        st.write("")
                        if st.button("🗑️ 삭제", key=f"del_sec_{s_idx}"):
                            sec_to_remove = s_idx
                            
                    q_text = "\n".join(sec.get("target_questions", []))
                    new_q_text = st.text_area(f"섹션 {s_idx + 1} 세부 탐색 질문 (줄바꿈으로 구분)", value=q_text, key=f"sec_q_{s_idx}", height=75)
                    sec["target_questions"] = [q.strip() for q in new_q_text.splitlines() if q.strip()]
                    sec["section_id"] = f"sec_{s_idx}"
                    
            if sec_to_remove is not None and len(sections) > 1:
                del sections[sec_to_remove]
                st.session_state["editing_outline"]["sections"] = sections
                st.rerun()
                
            col_add, col_save = st.columns([1, 2])
            with col_add:
                if st.button("➕ 새 섹션 추가", key="btn_add_section", use_container_width=True):
                    new_idx = len(sections)
                    sections.append({
                        "section_id": f"sec_{new_idx}",
                        "title": f"새 섹션 {new_idx + 1}",
                        "target_questions": ["상세 팩트 및 현황 확인"]
                    })
                    st.session_state["editing_outline"]["sections"] = sections
                    st.rerun()
                    
            with col_save:
                if st.button("💾 이 목차 최종 승인 및 히스토리 저장", type="primary", key="btn_save_manual_form", use_container_width=True):
                    approved = save_outline_history(
                        topic=cur_topic,
                        theme=cur_theme,
                        sections=sections,
                        source="manual_form",
                        memo="수동 폼 직접 편집",
                        core_questions=editor_active_core_questions
                    )
                    st.success(f"'{cur_theme}' 맞춤형 목차 승인 및 히스토리 영구 저장 완료! (ID: {approved['id']})")
                    st.session_state["editing_outline"] = approved
                    st.session_state["outline_editor_open"] = False
                    st.rerun()
                    
        else:
            cur_sections = st.session_state["editing_outline"].get("sections", [])
            init_md = sections_to_markdown_outline(cur_theme, cur_sections)
            
            md_input = st.text_area(
                "마크다운 목차 내용 (자유롭게 입력 및 수정 가능)",
                value=init_md,
                height=280,
                help="## 번호. 섹션명 및 하위 불릿(- 질문) 형식으로 자유롭게 편집하세요."
            )
            
            if st.button("💾 마크다운 목차 파싱 및 히스토리 저장", type="primary", key="btn_save_manual_md", use_container_width=True):
                parsed_theme, parsed_sections = markdown_outline_to_sections(md_input)
                approved = save_outline_history(
                    topic=cur_topic,
                    theme=parsed_theme if parsed_theme else cur_theme,
                    sections=parsed_sections,
                    source="manual_markdown",
                    memo="마크다운 직접 입력",
                    core_questions=editor_active_core_questions
                )
                st.success(f"'{approved['theme']}' 맞춤형 목차 ({len(parsed_sections)}개 섹션) 승인 및 히스토리 저장 완료! (ID: {approved['id']})")
                st.session_state["editing_outline"] = approved
                st.session_state["outline_editor_open"] = False
                st.rerun()

    # ========================================================
    # 📚 토픽 & 목차 히스토리 보관소 (Topic & Outline Archive)
    # ========================================================
    st.markdown("---")
    with st.expander("📚 토픽 & 목차 히스토리 보관소 (Topic & Outline Archive)", expanded=False):
        st.markdown("과거에 승인하거나 직접 작성하여 보관된 모든 토픽 및 목차 히스토리를 조회하고, 원클릭으로 다시 불러와 재사용할 수 있습니다.")
        
        sync_existing_latest_to_history()
        history_records = list_outline_history()
        
        if not history_records:
            st.info("아직 저장된 목차 히스토리가 없습니다. 위에서 목차를 승인하거나 수동 편집기를 통해 저장해보세요.")
        else:
            col_search, col_cnt = st.columns([3, 1])
            with col_search:
                hist_search = st.text_input("🔍 토픽 또는 테마 검색", placeholder="검색할 키워드 입력...", key="hist_search_kw")
            with col_cnt:
                st.metric("저장된 목차 수", f"{len(history_records)}개")
                
            filtered_history = [
                h for h in history_records 
                if not hist_search or (hist_search.lower() in h.get("topic", "").lower() or hist_search.lower() in h.get("theme", "").lower())
            ]
            
            if not filtered_history:
                st.warning("검색 결과와 일치하는 목차 히스토리가 없습니다.")
            else:
                for h_idx, h_item in enumerate(filtered_history):
                    h_id = h_item["id"]
                    h_topic = h_item.get("topic", "제목 없음")
                    h_theme = h_item.get("theme", "맞춤형 테마")
                    h_time = str(h_item.get("saved_at", ""))[:19].replace("T", " ")
                    h_cnt = h_item.get("section_count", len(h_item.get("sections", [])))
                    h_memo = h_item.get("memo", "")
                    
                    with st.container(border=True):
                        col_info, col_act1, col_act2, col_act3 = st.columns([4, 1.3, 1.3, 0.8])
                        with col_info:
                            memo_badge = f" `[{h_memo}]`" if h_memo else ""
                            st.markdown(f"**📌 {h_topic}** {memo_badge}")
                            st.caption(f"🕒 저장: {h_time} &nbsp;|&nbsp; 🏷️ 테마: **{h_theme}** &nbsp;|&nbsp; 📑 핵심 섹션: **{h_cnt}개**")
                            
                            with st.expander(f"섹션 구성 ({h_cnt}개) 미리보기", expanded=False):
                                if h_item.get("core_questions"):
                                    st.markdown("🎯 **연동된 핵심 질문:**")
                                    for cq in h_item["core_questions"]:
                                        st.markdown(f"  - {cq}")
                                    st.markdown("---")
                                for s_i, s in enumerate(h_item.get("sections", []), 1):
                                    st.markdown(f"**{s_i}. {s.get('title')}**")
                                    for q in s.get("target_questions", []):
                                        st.markdown(f"  - {q}")
                                        
                        with col_act1:
                            if st.button("🔄 활성화 & 리서치 연동", key=f"btn_act_hist_{h_idx}_{h_id}", use_container_width=True):
                                set_active_approved_outline(h_item)
                                st.session_state["editing_outline"] = h_item
                                st.session_state["active_core_questions"] = h_item.get("core_questions", [])
                                st.session_state["core_questions_text"] = "\n".join(h_item.get("core_questions", []))
                                st.success(f"'{h_topic}' 목차가 활성화되었습니다! 2번 리서치 탭에서 바로 실행할 수 있습니다.")
                                st.rerun()
                                
                        with col_act2:
                            if st.button("✏️ 편집기로 불러오기", key=f"btn_edit_hist_{h_idx}_{h_id}", use_container_width=True):
                                st.session_state["editing_outline"] = h_item
                                st.session_state["active_core_questions"] = h_item.get("core_questions", [])
                                st.session_state["core_questions_text"] = "\n".join(h_item.get("core_questions", []))
                                st.session_state["outline_editor_open"] = True
                                st.success(f"'{h_topic}' 목차를 수동 편집기로 불러왔습니다.")
                                st.rerun()
                                
                        with col_act3:
                            if st.button("🗑️ 삭제", key=f"btn_del_hist_{h_idx}_{h_id}", use_container_width=True):
                                delete_outline_history(h_id)
                                st.success("목차 히스토리가 삭제되었습니다.")
                                st.rerun()

# ========================================================
# TAB 2: DLS 심층 리서치 파이프라인
# ========================================================
with tab2:
    st.markdown("### 🚀 DLS 자율 심층 리서치 실행 파이프라인")
    
    approved_topic = final_topic
    has_outline = False
    
    sync_existing_latest_to_history()
    history_records = list_outline_history()
    
    if history_records:
        st.markdown("#### 📑 리서치 실행 목차 선택")
        hist_mode = st.radio(
            "목차 소스 선택",
            options=["⚡ 최근 활성화된 목차 사용", "📚 저장된 목차 히스토리 보관소에서 선택"],
            horizontal=True,
            key="tab2_hist_mode_radio"
        )
        if hist_mode == "📚 저장된 목차 히스토리 보관소에서 선택":
            hist_map = {
                f"[{h.get('saved_at', '')[:16].replace('T', ' ')}] {h.get('topic', '')} ({h.get('theme', '')})": h['id']
                for h in history_records
            }
            selected_hist_label = st.selectbox("적용할 히스토리 목차 선택", options=list(hist_map.keys()), key="tab2_hist_picker")
            selected_h_id = hist_map[selected_hist_label]
            selected_record = load_outline_history(selected_h_id)
            if selected_record:
                set_active_approved_outline(selected_record)
                saved_outline = selected_record
                approved_topic = selected_record.get("topic", approved_topic)
                has_outline = True
                st.info(f"📑 히스토리 목차 연동됨: **'{selected_record.get('theme')}'** (주제: {approved_topic})")

    if not has_outline and os.path.exists("temp/latest_approved_outline.json"):
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
        with st.expander(f"📑 승인된 목차 구성 ({len(saved_outline.get('sections', []))}개 핵심 섹션) 미리보기 및 수정", expanded=True):
            st.markdown(f"**분석 관점/테마**: {saved_outline.get('theme', '')}")
            if saved_outline.get("core_questions"):
                with st.container(border=True):
                    st.markdown("🎯 **해결 목표 핵심 질문 (Core Questions)**")
                    for cq_i, cq_txt in enumerate(saved_outline["core_questions"], 1):
                        st.markdown(f"**{cq_i}.** {cq_txt}")
            tab2_edit_toggle = st.toggle("✏️ 리서치 실행 전 목차 세부 수정", value=False, key="tab2_toggle_edit")
            if not tab2_edit_toggle:
                for idx, s in enumerate(saved_outline.get("sections", []), 1):
                    st.markdown(f"**{idx}. {s.get('title')}**")
                    for q in s.get("target_questions", []):
                        st.markdown(f"  - {q}")
            else:
                st.info("실행 직전 각 섹션의 제목이나 세부 질문을 즉시 수정할 수 있습니다.")
                tab2_sections = saved_outline.get("sections", [])
                for idx, s in enumerate(tab2_sections):
                    st.markdown(f"**섹션 {idx+1}**")
                    s["title"] = st.text_input(f"제목 #{idx+1}", value=s.get("title", ""), key=f"t2_sec_title_{idx}")
                    q_str = "\n".join(s.get("target_questions", []))
                    new_q_str = st.text_area(f"세부 질문 #{idx+1} (줄바꿈 구분)", value=q_str, key=f"t2_sec_q_{idx}", height=70)
                    s["target_questions"] = [q.strip() for q in new_q_str.splitlines() if q.strip()]
                    
                if st.button("💾 수정한 목차 저장 및 히스토리 보관", key="btn_save_tab2_outline", type="primary"):
                    saved_rec = save_outline_history(
                        topic=saved_outline.get("topic", research_topic),
                        theme=saved_outline.get("theme", "실행 직전 수정 목차"),
                        sections=tab2_sections,
                        source="tab2_pre_execution_edit",
                        memo="2번 탭 실행 직전 세부 수정",
                        core_questions=saved_outline.get("core_questions", [])
                    )
                    st.success(f"수정된 목차가 활성화되고 히스토리에 저장되었습니다! (ID: {saved_rec['id']})")
                    st.rerun()

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
                    "core_questions": saved_outline.get("core_questions", []) if (use_approved_outline and has_outline) else [],
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
            st.success("심층 리서치 및 4대 전문 보고서 번들 생성 완료!")
            if gen_report_path and os.path.exists(gen_report_path):
                with open(gen_report_path, "r", encoding="utf-8") as rf:
                    res_text = rf.read()
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button(
                        label="📥 원본 마크다운 리포트 다운로드",
                        data=res_text,
                        file_name=os.path.basename(gen_report_path),
                        mime="text/markdown",
                        key="tab2_dl_single"
                    )
                with col_d2:
                    bundles = get_available_bundles()
                    if bundles and os.path.exists(bundles[0].get("zip_path", "")):
                        with open(bundles[0]["zip_path"], "rb") as zf:
                            st.download_button(
                                label="📦 4대 보고서 번들 ZIP 다운로드",
                                data=zf.read(),
                                file_name=os.path.basename(bundles[0]["zip_path"]),
                                mime="application/zip",
                                key="tab2_dl_zip"
                            )
                st.markdown("---")
                st.markdown(res_text)
        except Exception as e:
            status_box.update(label="❌ 실행 오류 발생", state="error")
            st.error(f"오류: {e}")

# ========================================================
# TAB 3: 완성된 리포트 열람실 (4대 번들 & 단일 리포트)
# ========================================================
with tab3:
    st.markdown("### 📑 생성된 심층 리포트 아카이브")
    
    view_mode = st.radio(
        "열람 모드 선택",
        ["📦 4대 전문 보고서 패키지 (Multi-Tier Bundle)", "📄 단일 원본 리포트 (.md)"],
        horizontal=True,
        key="tab3_view_mode"
    )
    
    if view_mode == "📦 4대 전문 보고서 패키지 (Multi-Tier Bundle)":
        bundles = get_available_bundles()
        if not bundles:
            st.info("아직 생성된 4대 보고서 번들이 없습니다. 아래 버튼을 눌러 기존 최신 리포트를 4대 보고서 번들로 즉시 변환해 보세요!")
            report_files = sorted(glob.glob("output/*.md"), key=os.path.getmtime, reverse=True)
            if report_files:
                col_gen_src, col_gen_btn = st.columns([3, 1])
                with col_gen_src:
                    src_to_convert = st.selectbox("변환할 원본 리포트 선택", report_files, key="tab3_convert_sel")
                with col_gen_btn:
                    st.write("")
                    st.write("")
                    if st.button("🚀 4대 보고서 번들 생성", type="primary", key="tab3_btn_convert"):
                        with st.spinner("4대 전문 보고서(전략 브리프, 기술보고서, 벤치마크, 리스크/DD) 패키징 중..."):
                            try:
                                with open(src_to_convert, "r", encoding="utf-8") as f:
                                    raw_c = f.read()
                                llm = get_chat_model(provider=provider_option, model=model_name)
                                b_res = create_report_bundle(
                                    topic=os.path.basename(src_to_convert).replace(".md", "").replace("report_", ""),
                                    technical_report=raw_c,
                                    llm=llm
                                )
                                st.success(f"번들 생성 완료! ({b_res['bundle_id']})")
                                st.rerun()
                            except Exception as e:
                                st.error(f"번들 생성 실패: {e}")
        else:
            with st.expander("➕ 기존 단일 리포트를 4대 전문 보고서 번들로 추가 변환하기", expanded=False):
                st.caption("기존에 생성된 단일 마크다운 리포트를 분석하여 4대 전문 보고서(전략 브리프, 기술보고서, 벤치마크, 리스크/DD) 패키지로 즉시 파생·저장합니다.")
                report_files = sorted(glob.glob("output/*.md"), key=os.path.getmtime, reverse=True)
                if report_files:
                    col_gen_src, col_gen_btn = st.columns([3, 1])
                    with col_gen_src:
                        src_to_convert = st.selectbox("변환할 원본 리포트 선택", report_files, key="tab3_convert_sel_exist")
                    with col_gen_btn:
                        st.write("")
                        st.write("")
                        if st.button("🚀 4대 번들 즉시 생성", type="primary", key="tab3_btn_convert_exist"):
                            with st.spinner("4대 전문 보고서 패키징 중..."):
                                try:
                                    with open(src_to_convert, "r", encoding="utf-8") as f:
                                        raw_c = f.read()
                                    llm = get_chat_model(provider=provider_option, model=model_name)
                                    b_res = create_report_bundle(
                                        topic=os.path.basename(src_to_convert).replace(".md", "").replace("report_", ""),
                                        technical_report=raw_c,
                                        llm=llm
                                    )
                                    st.success(f"번들 생성 완료! ({b_res['bundle_id']})")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"번들 생성 실패: {e}")

            bundle_options = {f"📦 {b.get('topic', '리서치')} ({b.get('created_at', '')[:16]})": b for b in bundles}
            sel_bundle_label = st.selectbox("열람할 보고서 번들 선택", list(bundle_options.keys()), key="sel_bundle")
            chosen_bundle = bundle_options[sel_bundle_label]
            b_dir = Path(chosen_bundle["dir_path"])
            
            # Bundle Header with ZIP download
            col_b_info, col_b_zip = st.columns([3, 1])
            with col_b_info:
                st.markdown(f"#### 📦 **{chosen_bundle.get('topic')}**")
                st.caption(f"생성일시: {chosen_bundle.get('created_at')} | 포함 문서 수: {chosen_bundle.get('reports_count')}개 | 출처 수: {chosen_bundle.get('total_sources_count')}개")
            with col_b_zip:
                zip_path = chosen_bundle.get("zip_path")
                if zip_path and os.path.exists(zip_path):
                    with open(zip_path, "rb") as zf:
                        st.download_button(
                            label="📦 번들 전체 ZIP 다운로드",
                            data=zf.read(),
                            file_name=f"{chosen_bundle.get('bundle_id')}.zip",
                            mime="application/zip",
                            key="btn_dl_bundle_zip",
                            use_container_width=True
                        )
            
            st.markdown("---")
            
            # 5 Sub-Tabs for Specialized Reports
            sub1, sub2, sub3, sub4, sub5 = st.tabs([
                "👔 1. 경영진 전략 1-Pager",
                "🔬 2. 심층 기술·산업 보고서",
                "📊 3. 경쟁사 벤치마크 매트릭스",
                "⚠️ 4. 리스크 & Due-Diligence",
                "📰 5. 한경 심층 기획 기사"
            ])
            
            sub_files = [
                (sub1, "01_executive_brief.md", "👔 경영진 전략 브리프"),
                (sub2, "02_technical_deepdive.md", "🔬 심층 기술 분석서"),
                (sub3, "03_competitive_benchmark.md", "📊 경쟁사 벤치마크"),
                (sub4, "04_risk_due_diligence.md", "⚠️ 리스크 및 검증 과제"),
                (sub5, "05_hankyung_article.md", "📰 한경 심층 기획 기사")
            ]
            
            for tab_target, fname, tab_title in sub_files:
                with tab_target:
                    f_path = b_dir / fname
                    if f_path.exists():
                        with open(f_path, "r", encoding="utf-8") as rf:
                            doc_text = rf.read()
                        
                        col_doc_dl, _ = st.columns([1, 3])
                        with col_doc_dl:
                            st.download_button(
                                label=f"📥 {fname} 다운로드",
                                data=doc_text,
                                file_name=fname,
                                mime="text/markdown",
                                key=f"dl_{fname}"
                            )
                        st.markdown(doc_text)
                    else:
                        st.warning(f"{fname} 문서가 존재하지 않습니다.")
                        
    else:
        # 단일 원본 리포트 열람
        report_files = sorted(glob.glob("output/*.md"), key=os.path.getmtime, reverse=True)
        if not report_files:
            st.info("아직 생성된 리포트가 없습니다. 2번 탭에서 심층 리서치를 실행해보세요.")
        else:
            selected_file = st.selectbox("열람할 리포트 파일 선택", options=report_files, key="sel_single_report")
            if selected_file and os.path.exists(selected_file):
                with open(selected_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                st.download_button(
                    label="📥 마크다운 파일 다운로드",
                    data=content,
                    file_name=os.path.basename(selected_file),
                    mime="text/markdown",
                    key="dl_single_md"
                )
                st.markdown("---")
                st.markdown(content)

# ========================================================
# TAB 4: A/B 엔진 벤치마크
# ========================================================
with tab4:
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
# TAB 5: 스마트 리포트 분석실 (Dashboard & Q&A)
# ========================================================
with tab5:
    st.markdown("### 💎 스마트 리포트 분석실 (Executive Dashboard & AI Q&A)")
    st.markdown("생성된 심층 리포트를 30초 핵심 브리핑, KPI 지표 카드, 구조화된 섹션으로 자동 가공하고, AI와 대화하며 심층 질의응답할 수 있습니다.")

    report_files = sorted(glob.glob("output/*.md"), key=os.path.getmtime, reverse=True)
    if not report_files:
        st.info("아직 생성된 리포트가 없습니다. 2번 탭에서 심층 리서치를 실행해보세요.")
    else:
        col_sel, col_mode = st.columns([3, 2])
        with col_sel:
            selected_report = st.selectbox("분석 대상 리포트 선택", options=report_files, key="tab5_selected_report")
        with col_mode:
            view_subtab = st.radio(
                "분석 모드",
                options=["📋 구조화 대시보드 (Executive View)", "💬 리포트 심층 Q&A (Chat with Report)"],
                horizontal=True
            )

        if selected_report and os.path.exists(selected_report):
            with open(selected_report, "r", encoding="utf-8") as f:
                raw_text = f.read()

            parsed = parse_report_for_dashboard(raw_text)

            # Metadata Hero Banner
            created_str = str(parsed['metadata'].get('created_at', '최근'))[:19].replace('T', ' ')
            model_disp = parsed['metadata'].get('model', model_name)
            sources_disp = parsed['metadata'].get('scraped_sources_count', len(parsed['citations']))

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%); color: white; padding: 18px 24px; border-radius: 10px; margin-bottom: 20px;'>
                <div style='font-size: 1.4rem; font-weight: 700; margin-bottom: 6px;'>📊 {parsed['topic']}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>
                    🕒 작성: {created_str} &nbsp;|&nbsp; 
                    🤖 분석 모델: <code>{model_disp}</code> &nbsp;|&nbsp; 
                    📡 검증 출처: <b>{sources_disp}건</b> 교차 검증
                </div>
            </div>
            """, unsafe_allow_html=True)

            if view_subtab == "📋 구조화 대시보드 (Executive View)":
                # 1. Executive Summary (30-sec briefing)
                st.markdown("#### 💡 Executive Briefing (30초 핵심 브리핑)")
                exec_cards_html = ""
                for point in parsed["executive_summary"]:
                    exec_cards_html += f"<div style='background: #f1f8e9; border-left: 4px solid #43a047; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; font-size: 0.96rem; color: #1b5e20;'>{point}</div>"
                st.markdown(exec_cards_html, unsafe_allow_html=True)

                # 2. Key Metrics (KPIs)
                if parsed["kpi_metrics"]:
                    st.markdown("#### 📊 핵심 정량 지표 (Key Metrics)")
                    cols = st.columns(len(parsed["kpi_metrics"][:4]))
                    for idx, m in enumerate(parsed["kpi_metrics"][:4]):
                        with cols[idx]:
                            st.metric(label=m["label"], value=m["value"], delta=m["delta"])

                st.markdown("---")

                # 3. Structured Sections (Accordions)
                st.markdown("#### 📑 심층 분석 섹션 (클릭하여 접기/펼치기)")

                # Section 1: Facts
                with st.expander(f"🛡️ 1. 확인된 사실 (Verified Facts) — {len(parsed['facts'])}건", expanded=True):
                    if parsed["facts"]:
                        for f_idx, f_item in enumerate(parsed["facts"]):
                            st.markdown(f"**[{f_idx+1}]** {f_item}")
                    else:
                        st.info("추출된 팩트 항목이 없습니다.")

                # Section 2: Analysis
                with st.expander("🔍 2. 에이전트 해석 및 시장 시사점 (Analysis & Implications)", expanded=True):
                    if parsed["analysis_text"]:
                        st.markdown(parsed["analysis_text"])
                    else:
                        st.info("추출된 분석 항목이 없습니다.")

                # Section 3: Risks & Open Questions
                with st.expander("⚠️ 3. 미확인 주장 및 향후 검증 과제 (Open Questions & Risks)", expanded=True):
                    if parsed["risks_text"]:
                        st.markdown(parsed["risks_text"])
                    else:
                        st.info("추출된 미확인 검증 과제가 없습니다.")

                # Custom outline sections if any
                for c_sec in parsed["custom_sections"]:
                    with st.expander(f"📌 {c_sec['title']}", expanded=False):
                        st.markdown(c_sec["body"])

                # Section 4: Citations
                with st.expander(f"📚 4. 검증 뉴스 및 참고 출처 링크 — {len(parsed['citations'])}건", expanded=False):
                    if parsed["citations"]:
                        cit_cols = st.columns(2)
                        for c_idx, cit in enumerate(parsed["citations"]):
                            col_target = cit_cols[c_idx % 2]
                            with col_target:
                                st.markdown(f"**[^{cit['index']}]** [{cit['title']}]({cit['url']}) `({cit['domain']})`")
                    else:
                        st.info("등록된 각주 링크가 없습니다.")

                # Bottom Action Bar
                st.markdown("---")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    summary_text = "\n".join(parsed["executive_summary"])
                    st.download_button(
                        label="📋 3줄 핵심 요약 다운로드",
                        data=summary_text,
                        file_name=f"summary_{os.path.basename(selected_report)}.txt",
                        mime="text/plain",
                        key="tab5_dl_summary"
                    )
                with col_b2:
                    st.download_button(
                        label="📥 원문 마크다운 파일 다운로드",
                        data=raw_text,
                        file_name=os.path.basename(selected_report),
                        mime="text/markdown",
                        key="tab5_dl_raw"
                    )

            else:
                # 💬 Chat with Report
                st.markdown("#### 💬 리포트 심층 질의응답 (Chat with Report)")
                st.markdown("선택된 보고서의 모든 팩트와 분석을 바탕으로 AI와 대화하며 필요한 정보를 즉시 발굴합니다.")

                chat_key = f"chat_history_{selected_report}"
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = [
                        {"role": "assistant", "content": f"안녕하세요! 선택하신 **'{parsed['topic']}'** 리포트에 대해 무엇이든 질문해 주세요. 핵심 수치, 기업별 비교, 리스크 요인 등을 정확히 찾아 답변해 드립니다."}
                    ]

                st.markdown("**⚡ 빠른 추천 질문:**")
                q_cols = st.columns(3)
                quick_query = None
                with q_cols[0]:
                    if st.button("🎯 핵심 결론 3가지 요약", key="qp1", use_container_width=True):
                        quick_query = "이 보고서의 가장 핵심적인 결론 3가지를 명확히 요약해줘."
                with q_cols[1]:
                    if st.button("📊 언급된 모든 수치/점유율 표 정리", key="qp2", use_container_width=True):
                        quick_query = "보고서에 언급된 모든 기업별 점유율, 생산량, 금액 등 정량적 수치를 마크다운 표로 깔끔하게 정리해줘."
                with q_cols[2]:
                    if st.button("⚠️ 리스크 및 미확인 과제 요약", key="qp3", use_container_width=True):
                        quick_query = "보고서에서 지적한 가장 큰 리스크 요인과 향후 추가 검증이 필요한 과제를 상세히 설명해줘."

                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                user_input = st.chat_input("이 보고서에 대해 질문하세요 (예: 삼성전자의 2026년 HBM4 공급 전략은?)...")
                prompt_to_run = quick_query if quick_query else user_input

                if prompt_to_run:
                    st.session_state[chat_key].append({"role": "user", "content": prompt_to_run})
                    with st.chat_message("user"):
                        st.markdown(prompt_to_run)

                    with st.chat_message("assistant"):
                        with st.spinner("보고서 본문을 분석하여 답변 생성 중..."):
                            try:
                                llm = get_chat_model(provider=provider_option, model=model_name)
                                qa_prompt = f"""당신은 전문 수석 산업 분석가입니다.
사용자가 선택한 아래 [심층 리서치 보고서 원문]의 내용만을 엄격히 근거로 삼아 질문에 답변하세요.
보고서에 없는 내용은 지어내지 말고 "보고서에 해당 내용이 언급되어 있지 않습니다"라고 명시하세요.
가능한 경우 보고서의 구체적인 수치와 팩트를 인용하여 친절하고 명확하게 답변하세요.

[심층 리서치 보고서 원문]
제목: {parsed['topic']}
{raw_text[:12000]}

[사용자 질문]
{prompt_to_run}
"""
                                res = llm.invoke(qa_prompt)
                                ans_text = res.content if hasattr(res, "content") else str(res)
                                st.markdown(ans_text)
                                st.session_state[chat_key].append({"role": "assistant", "content": ans_text})
                            except Exception as e:
                                st.error(f"답변 생성 중 오류: {e}")
