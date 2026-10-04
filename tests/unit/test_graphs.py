import pytest
from unittest.mock import MagicMock, patch
from src.graphs.states import TopicOutlineState, DLSState
from src.graphs.topic_outline_graph import create_topic_outline_graph
from src.graphs.dls_research_graph import create_dls_research_graph
from src.nodes.research_nodes import init_run, route_reflection, route_section
from src.nodes.topic_nodes import route_human_feedback

def test_graphs_compile_successfully():
    """Graph 1 and Graph 2 should compile without syntax or schema errors."""
    g1 = create_topic_outline_graph()
    g2 = create_dls_research_graph()
    assert g1 is not None
    assert g2 is not None

def test_research_nodes_init_run():
    state: DLSState = {
        "topic": "테스트 토픽",
        "outline": [
            {"section_id": "sec_1", "title": "섹션 1", "target_questions": ["질문 1"]}
        ],
        "config": {"dls": {"max_reflection_loops": 2}}
    }
    result = init_run(state)
    assert result["run_id"].startswith("run_")
    assert result["current_section_idx"] == 0
    assert result["current_section"]["section_id"] == "sec_1"
    assert result["max_reflection_loops"] == 2

def test_route_reflection():
    # When sufficient -> synthesize_section
    state_suff: DLSState = {"is_sufficient": True, "reflection_count": 1, "max_reflection_loops": 3}
    assert route_reflection(state_suff) == "synthesize_section"

    # When insufficient but under max loops -> generate_queries
    state_insuff: DLSState = {"is_sufficient": False, "reflection_count": 1, "max_reflection_loops": 3}
    assert route_reflection(state_insuff) == "generate_queries"

    # When insufficient but reached max loops -> synthesize_section
    state_maxed: DLSState = {"is_sufficient": False, "reflection_count": 3, "max_reflection_loops": 3}
    assert route_reflection(state_maxed) == "synthesize_section"

def test_route_section():
    outline = [{"section_id": "sec_1"}, {"section_id": "sec_2"}]
    
    # Not last section -> next_section
    state_mid: DLSState = {"current_section_idx": 0, "outline": outline}
    assert route_section(state_mid) == "next_section"

    # Last section -> assemble_report
    state_last: DLSState = {"current_section_idx": 1, "outline": outline}
    assert route_section(state_last) == "assemble_report"

def test_route_human_feedback():
    assert route_human_feedback({"human_feedback": "approve"}) == "approve"
    assert route_human_feedback({"human_feedback": "승인"}) == "approve"
    assert route_human_feedback({"human_feedback": "A"}) == "approve"
    assert route_human_feedback({"human_feedback": ""}) == "approve"
    assert route_human_feedback({"human_feedback": "2번 섹션 질문을 더 구체화해주세요"}) == "revise"
