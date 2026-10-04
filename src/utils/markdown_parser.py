import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

def format_citations(sources: List[Dict[str, Any]]) -> Tuple[Dict[str, int], str]:
    """
    고유 URL별로 [^1], [^2] 각주 인덱스를 부여하고, 
    마크다운 하단에 붙일 각주 텍스트를 생성합니다.
    """
    url_to_index: Dict[str, int] = {}
    citation_lines: List[str] = []
    
    idx = 1
    for s in sources:
        url = s.get("url", "").strip()
        title = s.get("title", "").strip()
        if not url:
            continue
        if url not in url_to_index:
            url_to_index[url] = idx
            display_title = title if title else url
            citation_lines.append(f"[^{idx}]: [{display_title}]({url})")
            idx += 1
            
    citation_block = "\n".join(citation_lines)
    return url_to_index, citation_block

def assemble_final_report(
    topic: str,
    sections: List[Dict[str, Any]],
    section_drafts: Dict[str, str],
    all_sources: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> str:
    """
    전체 섹션 초안과 출처 각주, YAML Frontmatter, 5대 마크다운 저장 규격을
    통합하여 최종 리포트를 조립합니다.
    """
    now_iso = datetime.now().isoformat()
    source_count = len(all_sources)
    queries = metadata.get("queries", [])
    model_name = metadata.get("model", "qwen3.8:27b")
    
    # 1. Frontmatter
    queries_str = "\n".join([f'  - "{q}"' for q in queries])
    frontmatter = f"""---
topic: "{topic}"
created_at: "{now_iso}"
generator: "Dynamic Live Search (LangGraph Core)"
model: "{model_name}"
search_engine: "{metadata.get('search_engine', 'duckduckgo')}"
scraped_sources_count: {source_count}
search_queries:
{queries_str}
rag_metadata:
  verified_facts_ratio: "{metadata.get('verified_facts_ratio', 'High')}"
  hitl_reviewed: false
---

# 📊 {topic} — 심층 리서치 보고서

> **리서치 일자**: {now_iso[:10]} | **생성 에이전트**: DLS Multi-Tier Engine | **분석 모델**: {model_name}

---
"""
    # 2. Body sections
    body_blocks = []
    for sec in sections:
        sec_id = sec.get("section_id", "")
        sec_title = sec.get("title", "")
        draft = section_drafts.get(sec_id, "").strip()
        if not draft:
            continue
            
        block = f"## 📌 {sec_title}\n\n{draft}\n"
        body_blocks.append(block)
        
    full_body = "\n\n---\n\n".join(body_blocks)
    
    # 3. Human Feedback Slot
    human_slot = """
---

## ✍️ 전문가 검토 및 휴먼 피드백

> [!NOTE] 휴먼 피드백 & 직접 집필란
> 이 섹션은 도메인 전문가의 검토 및 인사이트 추가를 위한 전용 영역입니다.
> - [ ] 사실 관계 교차 검증 완료
> - [ ] 추가 의견 기술: 
"""

    # 4. Citations block
    _, citations = format_citations(all_sources)
    citations_section = f"\n\n---\n\n## 📚 참고 문헌 및 출처 링크\n\n{citations}\n" if citations else ""
    
    return frontmatter + full_body + human_slot + citations_section
