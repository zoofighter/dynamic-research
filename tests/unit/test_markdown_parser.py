from src.utils.markdown_parser import (
    format_citations,
    assemble_final_report,
    parse_report_for_dashboard,
    sections_to_markdown_outline,
    markdown_outline_to_sections
)

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


def test_parse_report_for_dashboard():
    sample_md = """---
topic: "HBM4 경쟁 전략"
model: "opencode/muse-spark-1.3"
---

# 📊 HBM4 경쟁 전략 리포트

## 1. 확인된 사실 (Facts)
- 2026년 SK하이닉스 점유율은 50%, 삼성전자 점유율은 33%이다 [^1].
- 마이크론 연말 생산능력은 월 10만장 규모이다 [^2].

## 2. 에이전트 해석 (Analysis)
삼성전자의 점유율 반등은 HBM3E 정상화에 기인한다.

## 3. 미확인 주장 및 향후 검증 과제 (Unverified)
| 구분 | 상충 소지 | 검증 과제 |
|---|---|---|
| 양산 시점 | 일정 불명확 | 퀄테스트 확인 필요 |

[^1]: https://news.google.com/sample1
[^2]: [마이크론 공식](https://micron.com/news)
"""
    data = parse_report_for_dashboard(sample_md)
    assert data["topic"] == "HBM4 경쟁 전략"
    assert len(data["facts"]) == 2
    assert len(data["citations"]) == 2
    assert data["citations"][0]["index"] == "1"
    assert data["citations"][0]["domain"] == "news.google.com"
    assert len(data["kpi_metrics"]) >= 2
    assert len(data["executive_summary"]) == 3


def test_outline_conversions():
    theme = "HBM4 기술 및 공급망 분석"
    sections = [
        {
            "section_id": "sec_0",
            "title": "엔비디아 루빈 공급 일정",
            "target_questions": ["초도 양산 시점", "SiP 테스트 통과 여부"]
        },
        {
            "section_id": "sec_1",
            "title": "파운드리 베이스다이 공정",
            "target_questions": ["TSMC 협력 관계", "패키징 수율"]
        }
    ]
    
    # 1. Structure -> Markdown
    md_text = sections_to_markdown_outline(theme, sections)
    assert "# 테마: HBM4 기술 및 공급망 분석" in md_text
    assert "## 1. 엔비디아 루빈 공급 일정" in md_text
    assert "- 초도 양산 시점" in md_text
    assert "## 2. 파운드리 베이스다이 공정" in md_text
    
    # 2. Markdown -> Structure
    parsed_theme, parsed_sections = markdown_outline_to_sections(md_text)
    assert parsed_theme == "HBM4 기술 및 공급망 분석"
    assert len(parsed_sections) == 2
    assert parsed_sections[0]["title"] == "엔비디아 루빈 공급 일정"
    assert len(parsed_sections[0]["target_questions"]) == 2
    assert parsed_sections[0]["target_questions"][0] == "초도 양산 시점"
    assert parsed_sections[1]["title"] == "파운드리 베이스다이 공정"
    assert parsed_sections[1]["target_questions"][1] == "패키징 수율"


