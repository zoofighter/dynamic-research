import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from src.graphs.topic_outline_graph import topic_outline_app
from src.graphs.dls_research_graph import dls_research_app
from src.graphs.states import TopicOutlineState, DLSState

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

@pytest.fixture
def mock_llm_response():
    """Returns a deterministic response for pipeline nodes."""
    def _create_mock(content: str):
        mock = MagicMock()
        mock.invoke.return_value = AIMessage(content=content)
        return mock
    return _create_mock

def test_dls_research_graph_end_to_end(tmp_path):
    """
    Graph 2 (DLSResearchGraph) 자율 실행 파이프라인 테스트.
    Web search와 LLM invoke를 모킹하여 쿼리 분해 -> 검색 -> 스크랩 -> 반성 -> 합성 -> 파일 저장 전과정을 검증합니다.
    """
    mock_outline = [
        {
            "section_id": "sec_1",
            "title": "테스트 섹션 1",
            "target_questions": ["질문 1에 대한 사실은?"],
            "expected_takeaway": "테스트 결론"
        }
    ]

    initial_state: DLSState = {
        "topic": "통합 테스트 HBM 시장",
        "outline": mock_outline,
        "config": {"dls": {"max_reflection_loops": 1}},
        "run_id": "test_run_e2e"
    }

    config = {"configurable": {"thread_id": "test_e2e_thread"}}

    # Mock search and scrape providers
    with patch("src.nodes.research_nodes.get_search_provider") as mock_sp_getter, \
         patch("src.nodes.research_nodes.get_scraper_provider") as mock_sc_getter, \
         patch("src.nodes.research_nodes.get_chat_model") as mock_cm_getter:

        # Mock Search Provider
        mock_sp = MagicMock()
        mock_r = MagicMock()
        mock_r.title = "테스트 뉴스 기사"
        mock_r.url = "https://news.example.com/item1"
        mock_r.snippet = "HBM 생산량 2026년 2배 증가 확인"
        mock_sp.search.return_value = [mock_r]
        mock_sp_getter.return_value = mock_sp

        # Mock Scraper Provider
        mock_sc = MagicMock()
        mock_doc = MagicMock()
        mock_doc.success = True
        mock_doc.title = "테스트 뉴스 본문"
        mock_doc.content = "HBM 12단 생산 라인이 가동을 시작했습니다."
        mock_sc.scrape.return_value = mock_doc
        mock_sc_getter.return_value = mock_sc

        # Mock LLM Chat Model
        mock_llm = MagicMock()
        # Returns for: 1) query decomp, 2) reflection (is_sufficient=True), 3) synthesis
        def mock_invoke(prompt, *args, **kwargs):
            p_str = str(prompt)
            if "심층 리서치 에이전트" in p_str:
                return AIMessage(content="HBM 12단 양산 일정\nHBM 공급망 현황")
            elif "팩트 체커이자 리서치 디렉터" in p_str:
                return AIMessage(content=json.dumps({"is_sufficient": True, "gap_description": "", "sub_queries": []}))
            else:
                return AIMessage(content="### 1) 확인된 사실\nHBM 12단 라인이 가동되었습니다. [^1]\n\n### 2) 해석\n시장 영향이 큽니다.\n\n### 3) 과제\n수율 검증 필요.")

        mock_llm.invoke.side_effect = mock_invoke
        mock_cm_getter.return_value = mock_llm

        # Run Graph 2
        events = list(dls_research_app.stream(initial_state, config, stream_mode="values"))
        assert len(events) > 0
        final_state = events[-1]

        # Assertions
        assert "final_report" in final_state
        assert "output_path" in final_state
        assert Path(final_state["output_path"]).exists()
        assert "HBM 12단 라인이 가동되었습니다. [^1]" in final_state["final_report"]
        assert "[^1]: [테스트 뉴스 본문](https://news.example.com/item1)" in final_state["final_report"]
