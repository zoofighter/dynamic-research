import pytest
from src.engines.base import BaseDataEngine, EngineResult
from src.engines.baseline_engine import BaselineDataEngine
from src.engines.llamaindex_engine import LlamaIndexDataEngine

def test_engine_result_model():
    res = EngineResult(
        answer="테스트 답변 [^1]",
        citations=[{"index": 1, "url": "https://example.com"}],
        latency_sec=1.23,
        token_usage={"total_tokens": 150},
        engine_name="TestEngine"
    )
    assert res.latency_sec == 1.23
    assert len(res.citations) == 1
    assert res.engine_name == "TestEngine"

def test_llamaindex_chunking_and_ranking():
    engine = LlamaIndexDataEngine(chunk_size=200)
    sample_docs = [
        {
            "title": "HBM 양산 뉴스",
            "url": "https://news.test/hbm",
            "content": "마이크론이 12단 HBM3E 엔비디아 공급을 승인받았습니다. 양산 일정은 2026년 하반기입니다."
        },
        {
            "title": "기타 자동차 뉴스",
            "url": "https://news.test/car",
            "content": "전기차 배터리 신기술이 발표되었습니다."
        }
    ]
    engine.index_documents(sample_docs)
    assert len(engine.nodes) >= 2
    
    ranked = engine._rank_nodes("마이크론 HBM3E 양산 일정", top_k=1)
    assert len(ranked) == 1
    assert "HBM3E" in ranked[0].text
