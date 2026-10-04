from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.graphs.states import DLSState
from src.nodes.research_nodes import (
    init_run,
    generate_queries,
    search_web,
    scrape_pages,
    reflect,
    synthesize_section,
    next_section,
    assemble_report,
    route_reflection,
    route_section
)

def create_dls_research_graph():
    """
    DLS 자율 리서치 코어 StateGraph 생성.
    - 쿼리 분해 -> 실시간 웹 검색 -> 본문 스크래핑 -> Self-Reflection 루프
    - 섹션별 3분할 팩트 합성 -> 전체 보고서 완결 조립
    """
    workflow = StateGraph(DLSState)

    # 노드 등록
    workflow.add_node("init_run", init_run)
    workflow.add_node("generate_queries", generate_queries)
    workflow.add_node("search_web", search_web)
    workflow.add_node("scrape_pages", scrape_pages)
    workflow.add_node("reflect", reflect)
    workflow.add_node("synthesize_section", synthesize_section)
    workflow.add_node("next_section", next_section)
    workflow.add_node("assemble_report", assemble_report)

    # 엣지 연결
    workflow.add_edge(START, "init_run")
    workflow.add_edge("init_run", "generate_queries")
    workflow.add_edge("generate_queries", "search_web")
    workflow.add_edge("search_web", "scrape_pages")
    workflow.add_edge("scrape_pages", "reflect")

    # Reflection 조건부 분기 (정보 결손 보완 루프 vs 섹션 합성)
    workflow.add_conditional_edges(
        "reflect",
        route_reflection,
        {
            "generate_queries": "generate_queries", # Sub-query 재탐색
            "synthesize_section": "synthesize_section" # 충분성 확보 시 섹션 합성
        }
    )

    # 섹션 루프 조건부 분기 (다음 섹션 vs 최종 조립)
    workflow.add_conditional_edges(
        "synthesize_section",
        route_section,
        {
            "next_section": "next_section",
            "assemble_report": "assemble_report"
        }
    )

    workflow.add_edge("next_section", "generate_queries")
    workflow.add_edge("assemble_report", END)

    # 체크포인터 장착 (메모리 세이버)
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled app
dls_research_app = create_dls_research_graph()
