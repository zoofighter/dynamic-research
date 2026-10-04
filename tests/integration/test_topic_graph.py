import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

from src.graphs.topic_outline_graph import topic_outline_app
from src.graphs.states import TopicOutlineState
from src.providers.rss import NewsArticle

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def test_topic_outline_graph_discover_mode():
    """
    Graph 1 (TopicOutlineGraph) 주제 자동 발굴 및 HITL 승인 파이프라인 검증.
    Google News RSS 수집 -> 주제 추천 -> 선택(HITL) -> 분석 -> 아웃라인 생성 -> 승인(HITL) -> approved_outline.json
    """
    initial_state: TopicOutlineState = {
        "user_input": "반도체 HBM",
        "mode": "discover"
    }
    thread_id = "test_g1_thread"
    config = {"configurable": {"thread_id": thread_id}}

    with patch("src.nodes.topic_nodes.NewsRSSProvider") as mock_rss_cls, \
         patch("src.nodes.topic_nodes.get_chat_model") as mock_cm_getter:

        # Mock RSS Provider
        mock_rss = MagicMock()
        mock_rss.fetch_feed.return_value = [
            NewsArticle(title="마이크론 HBM3E 양산 박차", link="https://news.example.com/1", published="2026-10-04", source="뉴스")
        ]
        mock_rss_cls.return_value = mock_rss

        # Mock LLM Chat Model
        mock_llm = MagicMock()
        def mock_invoke(prompt, *args, **kwargs):
            p = str(prompt)
            if "트렌드와 기술 혁신을 포착하는 리서치 디렉터" in p:
                return AIMessage(content=json.dumps([
                    {"topic_id": "T1", "title": "마이크론 12단 HBM3E 양산 현황", "rationale": "시장의 높은 관심"}
                ]))
            elif "리서치 기획 전문가" in p:
                return AIMessage(content=json.dumps({
                    "topic": "마이크론 12단 HBM3E 양산 현황",
                    "target_audience": "반도체 투자자",
                    "research_depth": "deep",
                    "key_controversies": ["엔비디아 퀄 승인 여부"],
                    "core_hypothesis": "양산 가시성 확인"
                }))
            else: # Outline generation
                return AIMessage(content=json.dumps([
                    {
                        "proposal_id": "A",
                        "theme": "공급망 및 수율 중심",
                        "sections": [
                            {"section_id": "sec_1", "title": "공급망 현황", "target_questions": ["납품 일정은?"], "expected_takeaway": "공급 시점"}
                        ]
                    }
                ]))
        mock_llm.invoke.side_effect = mock_invoke
        mock_cm_getter.return_value = mock_llm

        # Run until first interrupt (select_topic)
        events = list(topic_outline_app.stream(initial_state, config, stream_mode="values"))
        snapshot = topic_outline_app.get_state(config)
        assert snapshot.next == ("select_topic",)

        # Resume select_topic
        topic_outline_app.update_state(config, {"selected_topic": "마이크론 12단 HBM3E 양산 현황"}, as_node="select_topic")
        events = list(topic_outline_app.stream(None, config, stream_mode="values"))
        
        # Check next interrupt (human_review)
        snapshot = topic_outline_app.get_state(config)
        assert snapshot.next == ("human_review",)

        # Resume human_review with approval
        topic_outline_app.update_state(config, {"human_feedback": "approve"}, as_node="human_review")
        final_events = list(topic_outline_app.stream(None, config, stream_mode="values"))
        final_state = final_events[-1]

        # Verify finalized outline
        assert "approved_outline" in final_state
        assert final_state["approved_outline"]["topic"] == "마이크론 12단 HBM3E 양산 현황"
        assert len(final_state["approved_outline"]["sections"]) == 1
        assert (ROOT_DIR / "temp" / "latest_approved_outline.json").exists()
