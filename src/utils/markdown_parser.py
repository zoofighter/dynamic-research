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
    for idx, sec in enumerate(sections):
        sec_id = sec.get("section_id") or f"sec_{idx}"
        sec_title = sec.get("title", "")
        draft = section_drafts.get(sec_id, "").strip()
        if not draft:
            draft = section_drafts.get(f"sec_{idx}", "").strip()
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


def parse_report_for_dashboard(markdown_text: str) -> Dict[str, Any]:
    """
    마크다운 리포트를 분석하여 프론트매터 메타데이터, 핵심 지표(KPI),
    3줄 요약(Executive Summary), 구조화된 섹션(팩트/해석/리스크), 각주 출처를 추출합니다.
    """
    import urllib.parse
    
    metadata: Dict[str, Any] = {}
    content = markdown_text

    # 1. Frontmatter parsing
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", markdown_text, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        content = markdown_text[fm_match.end():]
        for line in fm_text.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("-") and not line.startswith("["):
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'")

    # 2. Citations extraction (e.g. [^1]: [Title](URL) or [^1]: URL)
    citations = []
    citation_pattern = re.compile(r"^\[\^(\d+)\]:\s*(?:\[(.*?)\]\((.*?)\)|(\S+))", re.MULTILINE)
    for match in citation_pattern.finditer(markdown_text):
        idx = match.group(1)
        title = match.group(2) or ""
        url = match.group(3) or match.group(4) or ""
        domain = ""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.replace("www.", "")
        except Exception:
            domain = url[:25]
        citations.append({
            "index": idx,
            "title": title if title else domain,
            "url": url,
            "domain": domain
        })

    # 3. Sections parsing
    raw_sections = re.split(r"\n(?=##\s+)", content)
    
    facts_list = []
    analysis_text = ""
    risks_text = ""
    custom_sections = []

    for sec in raw_sections:
        sec = sec.strip()
        if not sec:
            continue
        first_line = sec.splitlines()[0]
        
        if re.search(r"확인된\s*사실|Facts", first_line, re.I):
            for l in sec.splitlines()[1:]:
                l_strip = l.strip()
                if l_strip.startswith(("- ", "* ")):
                    facts_list.append(re.sub(r"^[-*]\s+", "", l_strip))
                elif re.match(r"^\d+[\.\)]\s+", l_strip):
                    facts_list.append(re.sub(r"^\d+[\.\)]\s+", "", l_strip))
        elif re.search(r"에이전트\s*해석|Analysis|시사점|전략적", first_line, re.I):
            analysis_text = "\n".join(sec.splitlines()[1:]).strip()
        elif re.search(r"미확인|검증\s*과제|Unverified|Open\s*Questions|리스크", first_line, re.I):
            risks_text = "\n".join(sec.splitlines()[1:]).strip()
        elif re.search(r"참고\s*문헌|출처|전문가\s*검토", first_line, re.I):
            continue
        else:
            sec_title = re.sub(r"^##\s*", "", first_line).strip()
            sec_body = "\n".join(sec.splitlines()[1:]).strip()
            if sec_body:
                custom_sections.append({
                    "title": sec_title,
                    "body": sec_body
                })

    # 4. Extract KPI Metrics
    kpi_metrics = []
    seen_labels = set()
    
    share_matches = re.findall(
        r"([가-힣A-Za-z0-9\s·]+?(?:점유율|비중|성장률|수율|대역폭|효율))\s*(?:은|는|이|가|:)?\s*([+\-]?\d+(?:\.\d+)?(?:%|배|TB/s|GB/s))",
        markdown_text
    )
    for label, val in share_matches:
        lbl = label.strip()[-15:]
        if lbl not in seen_labels and len(lbl) > 1:
            seen_labels.add(lbl)
            kpi_metrics.append({"label": lbl, "value": val.strip(), "delta": "주요 지표"})
        if len(kpi_metrics) >= 2:
            break

    scale_matches = re.findall(
        r"([가-힣A-Za-z0-9\s·]+?(?:규모|캐파|생산능력|매출|투자액|커밋먼트))\s*(?:은|는|이|가|:)?\s*([약최대대략]*\s*[\d,]+(?:\.\d+)?\s*(?:조\s*원|억\s*원|억\s*달러|조\s*달러|만\s*장|단))",
        markdown_text
    )
    for label, val in scale_matches:
        lbl = label.strip()[-15:]
        if lbl not in seen_labels and len(lbl) > 1:
            seen_labels.add(lbl)
            kpi_metrics.append({"label": lbl, "value": val.strip(), "delta": "규모/일정"})
        if len(kpi_metrics) >= 4:
            break

    if len(kpi_metrics) < 2 and facts_list:
        for f in facts_list[:5]:
            m = re.search(r"(\d+(?:\.\d+)?(?:%|조원|억원|만장|억달러))", f)
            if m:
                val = m.group(1)
                kpi_metrics.append({"label": "핵심 팩트 수치", "value": val, "delta": "보도 인용"})
            if len(kpi_metrics) >= 3:
                break

    # 5. Executive Summary (TL;DR 3줄 요약)
    exec_summary = []
    if facts_list:
        clean_fact1 = re.sub(r"\[\^\d+\]", "", facts_list[0]).strip()
        exec_summary.append(f"📌 **핵심 팩트**: {clean_fact1[:140]}")
    if analysis_text:
        first_para_candidates = [p.strip() for p in analysis_text.splitlines() if p.strip() and not p.strip().startswith("#")]
        if first_para_candidates:
            clean_analysis = re.sub(r"\[\^\d+\]", "", first_para_candidates[0]).strip()
            clean_analysis = re.sub(r"^\*\*[^*]+\*\*[:\s]*", "", clean_analysis)
            exec_summary.append(f"💡 **시장 시사점**: {clean_analysis[:140]}")
    elif len(facts_list) > 1:
        clean_fact2 = re.sub(r"\[\^\d+\]", "", facts_list[1]).strip()
        exec_summary.append(f"💡 **추가 팩트**: {clean_fact2[:140]}")

    if risks_text:
        risk_lines = [l.strip() for l in risks_text.splitlines() if l.strip().startswith("|") and not l.strip().startswith("|---")]
        if len(risk_lines) > 1:
            cols = [c.strip() for c in risk_lines[1].split("|") if c.strip()]
            if len(cols) >= 2:
                exec_summary.append(f"⚠️ **검증 과제**: [{cols[0]}] {re.sub(r'\[\^\d+\]', '', cols[1])[:100]}")
            else:
                exec_summary.append(f"⚠️ **검증 과제**: {re.sub(r'\[\^\d+\]', '', cols[0])[:120]}")
        else:
            risk_candidates = [l.strip() for l in risks_text.splitlines() if l.strip() and not l.strip().startswith("#")]
            if risk_candidates:
                exec_summary.append(f"⚠️ **리스크 요인**: {re.sub(r'\[\^\d+\]', '', risk_candidates[0])[:130]}")
    elif len(facts_list) > 2:
        clean_fact3 = re.sub(r"\[\^\d+\]", "", facts_list[2]).strip()
        exec_summary.append(f"⚠️ **주목 지표**: {clean_fact3[:140]}")

    return {
        "metadata": metadata,
        "topic": metadata.get("topic") or "심층 리서치 보고서",
        "kpi_metrics": kpi_metrics,
        "executive_summary": exec_summary,
        "facts": facts_list,
        "analysis_text": analysis_text,
        "risks_text": risks_text,
        "custom_sections": custom_sections,
        "citations": citations,
        "raw_content": markdown_text
    }


def sections_to_markdown_outline(theme: str, sections: List[Dict[str, Any]]) -> str:
    """
    목차 구조체를 마크다운 텍스트 형식으로 변환합니다.
    """
    lines = [f"# 테마: {theme}", ""]
    for idx, s in enumerate(sections, 1):
        title = s.get("title", f"섹션 {idx}")
        # 번호 중복 방지
        clean_title = re.sub(r"^\d+[\.\)]\s*", "", title)
        lines.append(f"## {idx}. {clean_title}")
        for q in s.get("target_questions", []):
            lines.append(f"- {q}")
        lines.append("")
    return "\n".join(lines).strip()


def markdown_outline_to_sections(md_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    사용자가 직접 작성/수정한 마크다운 목차 텍스트를 파싱하여 theme과 sections 구조체로 변환합니다.
    """
    theme = "사용자 정의 맞춤형 목차"
    sections: List[Dict[str, Any]] = []
    
    current_sec_title = ""
    current_questions: List[str] = []
    
    for raw_line in md_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        # 1. Theme line (# 테마: ...)
        if line.startswith("# ") and not line.startswith("## "):
            theme_cand = re.sub(r"^#\s*(?:테마|Theme|관점)?[:：]?\s*", "", line).strip()
            if theme_cand:
                theme = theme_cand
            continue
            
        # 2. Section header (## ...)
        if line.startswith("## ") or (line.startswith("### ") and not current_sec_title):
            if current_sec_title:
                sec_id = f"sec_{len(sections)}"
                sections.append({
                    "section_id": sec_id,
                    "title": current_sec_title,
                    "target_questions": current_questions if current_questions else [current_sec_title]
                })
                current_questions = []
            sec_title_cand = re.sub(r"^##+\s*", "", line).strip()
            sec_title_clean = re.sub(r"^\d+[\.\)]\s*", "", sec_title_cand)
            current_sec_title = sec_title_clean if sec_title_clean else sec_title_cand
            continue
            
        # 3. Bullet questions (- ... or * ...)
        if line.startswith(("- ", "* ")):
            q = re.sub(r"^[-*]\s*", "", line).strip()
            if q:
                current_questions.append(q)
        elif re.match(r"^\d+[\.\)]\s+", line) and current_sec_title:
            q = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if q:
                current_questions.append(q)
        elif current_sec_title and not line.startswith("#"):
            current_questions.append(line)
            
    # Add last section
    if current_sec_title:
        sec_id = f"sec_{len(sections)}"
        sections.append({
            "section_id": sec_id,
            "title": current_sec_title,
            "target_questions": current_questions if current_questions else [current_sec_title]
        })
        
    return theme, sections


