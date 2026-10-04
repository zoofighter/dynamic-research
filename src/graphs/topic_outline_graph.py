from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.graphs.states import TopicOutlineState
from src.nodes.topic_nodes import (
    discover_topics,
    select_topic,
    expand_topic,
    generate_outlines,
    human_review,
    revise_outline,
    finalize_outline,
    route_human_feedback
)

def create_topic_outline_graph():
    """
    주제 발굴 및 아웃라인 제안 (Graph 1) 생성.
    - Google News RSS 수집 및 클러스터링
    - HITL interrupt() 기반 주제 선택 및 아웃라인 승인/수정 루프
    """
    workflow = StateGraph(TopicOutlineState)

    # 노드 등록
    workflow.add_node("discover_topics", discover_topics)
    workflow.add_node("select_topic", select_topic)
    workflow.add_node("expand_topic", expand_topic)
    workflow.add_node("generate_outlines", generate_outlines)
    workflow.add_node("human_review", human_review)
    workflow.add_node("revise_outline", revise_outline)
    workflow.add_node("finalize_outline", finalize_outline)

    # 시작 분기 (mode: "discover" vs "direct")
    workflow.add_conditional_edges(
        START,
        lambda s: s.get("mode", "direct"),
        {
            "discover": "discover_topics",
            "direct": "expand_topic"
        }
    )

    workflow.add_edge("discover_topics", "select_topic")
    workflow.add_edge("select_topic", "expand_topic")
    workflow.add_edge("expand_topic", "generate_outlines")
    workflow.add_edge("generate_outlines", "human_review")

    # HITL Review 분기 (수정 루프 vs 승인)
    workflow.add_conditional_edges(
        "human_review",
        route_human_feedback,
        {
            "revise": "revise_outline",
            "approve": "finalize_outline"
        }
    )

    workflow.add_edge("revise_outline", "human_review")
    workflow.add_edge("finalize_outline", END)

    # 체크포인터 연결 (인터럽트 복원용)
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled app
topic_outline_app = create_topic_outline_graph()
