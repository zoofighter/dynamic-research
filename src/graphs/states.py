from typing import TypedDict, Literal, Annotated, List, Dict, Any, Optional
from langgraph.graph import add_messages

# ==============================================================================
# Graph 1 State: Topic & Outline Proposer (HITL)
# ==============================================================================
class TopicOutlineState(TypedDict, total=False):
    # -- Inputs --
    user_input: str                          # 사용자 입력 (키워드, 문장, 관심분야)
    mode: Literal["discover", "direct"]      # "discover"(뉴스 기반 발굴) vs "direct"(직접 입력)
    
    # -- Topic Discovery --
    news_headlines: List[Dict[str, Any]]     # Google News RSS에서 수집된 기사
    past_reports: List[Dict[str, Any]]       # output/ 내 기존 리포트 메타데이터
    suggested_topics: List[Dict[str, Any]]   # LLM이 제안한 추천 주제 리스트
    selected_topic: str                      # 사용자 또는 시스템이 선택한 최종 주제
    
    # -- Outline Generation --
    topic_analysis: Dict[str, Any]           # 주제 의도/타겟/핵심논점 분석
    core_questions: Optional[List[str]]      # 사용자 또는 AI 추천 핵심 질문 (Core Questions)
    outline_proposals: List[Dict[str, Any]]  # 다각도 아웃라인 안 (A/B/C)
    
    # -- Human Review (HITL) --
    human_feedback: Optional[str]            # 사용자 피드백 (수정 요청 등)
    approved_outline: Optional[Dict[str, Any]] # 최종 승인된 아웃라인 구조
    
    # -- Conversational Messages --
    messages: Annotated[list, add_messages]


# ==============================================================================
# Graph 2 State: DLS Autonomous Research Core
# ==============================================================================
class SectionSpec(TypedDict, total=False):
    section_id: str                          # e.g., "sec_1"
    title: str                               # 섹션 제목
    target_questions: List[str]              # 핵심 검증 질문 리스트
    expected_takeaway: str                   # 기대 결론 / 시사점


class DLSState(TypedDict, total=False):
    # -- Inputs (from approved_outline or direct) --
    topic: str                               # 연구 주제
    core_questions: Optional[List[str]]      # 집중 해결 핵심 질문 목록
    outline: List[Dict[str, Any]]            # 섹션 정의 목록
    config: Dict[str, Any]                   # 런타임 설정 (settings.yaml)
    
    # -- Section Loop Control --
    current_section_idx: int                 # 현재 처리 중인 섹션 번호 (0-indexed)
    current_section: Dict[str, Any]          # 현재 섹션 스펙
    
    # -- Step 1: Query Decomposition --
    queries: List[str]                       # 현재 섹션용 검색 쿼리 목록
    
    # -- Step 2: Live Web Search --
    search_results: List[Dict[str, Any]]     # DuckDuckGo/Serper 검색 결과 (제목, URL, 스니펫)
    
    # -- Step 3: Deep Scraping --
    scraped_pages: List[Dict[str, Any]]      # Trafilatura/Jina 추출 본문
    
    # -- Step 4: Self-Reflection Loop --
    reflection_count: int                    # 현재 섹션 내 반성 루프 실행 횟수
    max_reflection_loops: int                # 최대 반성 루프 허용치 (기본 2~3)
    is_sufficient: bool                      # 팩트 충분성 검증 결과 (True/False)
    gap_description: str                     # 결손 팩트 분석 설명
    sub_queries: List[str]                   # 추가 탐색용 세부 쿼리
    
    # -- Step 5: Synthesis & Aggregation --
    section_drafts: Dict[str, str]           # 섹션별 생성된 마크다운 초안 {"sec_1": "..."}
    all_sources: List[Dict[str, Any]]        # 전체 인용 출처 목록 (중복 제거 및 넘버링)
    
    # -- Final Output & Metadata --
    final_report: str                        # 3분할 팩트 + 각주 완결 마크다운 보고서
    run_id: str                              # 실행 세션 ID (run_YYYYMMDD_HHMMSS)
    output_path: str                         # 결과 파일 저장 경로
    bundle_dir: str                          # 4대 보고서 번들 저장 폴더
    bundle_manifest: Dict[str, Any]          # 번들 매니페스트 메타데이터
    bundle_zip: str                          # 번들 ZIP 압축파일 경로
    errors: List[Dict[str, Any]]             # 실행 중 발생한 예외 로그

