import pytest
from src.utils.markdown_parser import format_citations, assemble_final_report

def test_format_citations():
    sources = [
        {"url": "https://example.com/a", "title": "Article A"},
        {"url": "https://example.com/b", "title": "Article B"},
        {"url": "https://example.com/a", "title": "Duplicate A"},  # Should dedup
        {"url": "", "title": "Empty URL"}
    ]
    url_to_idx, citation_block = format_citations(sources)
    
    assert len(url_to_idx) == 2
    assert url_to_idx["https://example.com/a"] == 1
    assert url_to_idx["https://example.com/b"] == 2
    assert "[^1]: [Article A](https://example.com/a)" in citation_block
    assert "[^2]: [Article B](https://example.com/b)" in citation_block

def test_assemble_final_report():
    topic = "AI 반도체 시장 분석"
    sections = [
        {"section_id": "sec_1", "title": "개요 및 핵심 사실"}
    ]
    section_drafts = {
        "sec_1": "이것은 확인된 사실입니다. [^1]\n\n### 2) 해석\n시장 영향이 큽니다."
    }
    all_sources = [
        {"url": "https://example.com/1", "title": "테스트 출처"}
    ]
    metadata = {
        "queries": ["반도체 HBM"],
        "model": "qwen3.8:27b",
        "search_engine": "duckduckgo"
    }
    
    report = assemble_final_report(topic, sections, section_drafts, all_sources, metadata)
    
    # 5대 저장 규격 검증
    assert "---" in report
    assert 'topic: "AI 반도체 시장 분석"' in report
    assert "rag_metadata:" in report
    assert "# 📊 AI 반도체 시장 분석" in report
    assert "## 📌 개요 및 핵심 사실" in report
    assert "이것은 확인된 사실입니다. [^1]" in report
    assert "## ✍️ 전문가 검토 및 휴먼 피드백" in report
    assert "> [!NOTE] 휴먼 피드백 & 직접 집필란" in report
    assert "## 📚 참고 문헌 및 출처 링크" in report
    assert "[^1]: [테스트 출처](https://example.com/1)" in report
