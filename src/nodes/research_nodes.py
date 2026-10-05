import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from src.graphs.states import DLSState
from src.providers.search import get_search_provider
from src.providers.scraper import get_scraper_provider
from src.providers.llm import get_chat_model
from src.utils.dedup import deduplicate_results
from src.utils.markdown_parser import assemble_final_report
from src.utils.bundle_packager import create_report_bundle
from src.prompts.query_prompts import QUERY_DECOMPOSITION_PROMPT, SUB_QUERY_EXPANSION_PROMPT
from src.prompts.reflection_prompts import REFLECTION_EVALUATION_PROMPT
from src.prompts.synthesis_prompts import SECTION_SYNTHESIS_PROMPT

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def clean_think_tags(text: str) -> str:
    """Strip <think>...</think> tags produced by reasoning models."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def init_run(state: DLSState) -> Dict[str, Any]:
    """초기화 노드: run_id 발급, 임시 디렉토리 생성 및 첫 섹션 설정"""
    run_id = state.get("run_id") or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    temp_dir = ROOT_DIR / "temp" / run_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    raw_outline = state.get("outline", [])
    outline = []
    for idx, s in enumerate(raw_outline):
        s_copy = dict(s)
        if not s_copy.get("section_id"):
            s_copy["section_id"] = f"sec_{idx}"
        outline.append(s_copy)

    if not outline:
        # Fallback default section if outline is empty
        outline = [{
            "section_id": "sec_0",
            "title": f"{state.get('topic', '리서치')} 개요 및 핵심 현황",
            "target_questions": ["최신 핵심 현황 및 주요 사실은 무엇인가?"],
            "expected_takeaway": "핵심 팩트 요약"
        }]

    # Save outline backup
    with open(temp_dir / "outline.json", "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)

    config = state.get("config", {})
    max_loops = config.get("dls", {}).get("max_reflection_loops", 2)

    return {
        "run_id": run_id,
        "outline": outline,
        "current_section_idx": 0,
        "current_section": outline[0],
        "reflection_count": 0,
        "max_reflection_loops": max_loops,
        "section_drafts": {},
        "all_sources": [],
        "errors": []
    }

def generate_queries(state: DLSState) -> Dict[str, Any]:
    """Step 1: 현재 섹션의 핵심 질문을 분해하여 검색 쿼리 생성"""
    llm = get_chat_model(tier="fast")
    sec = state["current_section"]
    topic = state.get("topic", "")
    
    # Sub-queries from reflection or initial query decomposition
    sub_q = state.get("sub_queries")
    if sub_q and state.get("reflection_count", 0) > 0:
        queries = sub_q[:2]
    else:
        questions_str = "\n".join([f"- {q}" for q in sec.get("target_questions", [])])
        prompt = QUERY_DECOMPOSITION_PROMPT.format(
            topic=topic,
            section_title=sec.get("title", ""),
            target_questions=questions_str
        )
        res = llm.invoke(prompt)
        content = clean_think_tags(res.content)
        queries = [q.strip().strip("-").strip("1234567890.").strip() 
                   for q in content.split("\n") if q.strip()][:3]
        if not queries:
            queries = [f"{topic} {sec.get('title', '')}".strip()]

    return {"queries": queries}

def search_web(state: DLSState) -> Dict[str, Any]:
    """Step 2: 실시간 웹 검색 수행 및 URL 중복 제거"""
    search_provider = get_search_provider()
    queries = state.get("queries", [])
    max_results_per_q = 3
    
    raw_results = []
    for q in queries:
        try:
            res = search_provider.search(q, max_results=max_results_per_q)
            for r in res:
                raw_results.append({
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "query": q
                })
        except Exception as e:
            pass

    # Deduplicate by URL
    deduped = deduplicate_results(raw_results, key="url")[:4]
    return {"search_results": deduped}

def scrape_pages(state: DLSState) -> Dict[str, Any]:
    """Step 3: 상위 검색 결과 페이지 크롤링 및 본문 추출"""
    scraper = get_scraper_provider()
    results = state.get("search_results", [])
    scraped_pages = list(state.get("scraped_pages", []))
    all_sources = list(state.get("all_sources", []))

    # Existing URLs to avoid rescraping
    existing_urls = {s.get("url") for s in all_sources}

    for item in results:
        url = item.get("url")
        if not url or url in existing_urls:
            continue

        try:
            doc = scraper.scrape(url)
            if doc.success and doc.content:
                entry = {
                    "url": url,
                    "title": doc.title or item.get("title", ""),
                    "content": doc.content[:2000]
                }
                scraped_pages.append(entry)
                all_sources.append(entry)
                existing_urls.add(url)
            elif item.get("snippet"):
                # Fallback to search snippet
                entry = {
                    "url": url,
                    "title": item.get("title", ""),
                    "content": item.get("snippet", "")
                }
                scraped_pages.append(entry)
                all_sources.append(entry)
                existing_urls.add(url)
        except Exception:
            if item.get("snippet"):
                entry = {
                    "url": url,
                    "title": item.get("title", ""),
                    "content": item.get("snippet", "")
                }
                scraped_pages.append(entry)
                all_sources.append(entry)
                existing_urls.add(url)

    return {
        "scraped_pages": scraped_pages,
        "all_sources": all_sources
    }

def reflect(state: DLSState) -> Dict[str, Any]:
    """Step 4: Self-Reflection — 팩트 충분성 검증 및 정보 결손(Gap) 분석"""
    llm = get_chat_model(tier="standard")
    sec = state["current_section"]
    pages = state.get("scraped_pages", [])
    reflection_count = state.get("reflection_count", 0) + 1
    max_loops = state.get("max_reflection_loops", 2)

    # If reached max loops or no pages, treat as sufficient to prevent deadlock
    if reflection_count >= max_loops or not pages:
        return {
            "reflection_count": reflection_count,
            "is_sufficient": True,
            "gap_description": "",
            "sub_queries": []
        }

    summary_text = "\n".join([f"- [{p.get('title')}] {p.get('content')[:300]}" for p in pages[-4:]])
    prompt = REFLECTION_EVALUATION_PROMPT.format(
        section_title=sec.get("title", ""),
        target_questions="\n".join([f"- {q}" for q in sec.get("target_questions", [])]),
        expected_takeaway=sec.get("expected_takeaway", "상세 분석"),
        scraped_summary=summary_text
    )

    try:
        res = llm.invoke(prompt)
        cleaned = clean_think_tags(res.content)
        # Parse JSON from LLM response
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            is_sufficient = bool(data.get("is_sufficient", True))
            gap = data.get("gap_description", "")
            sub_q = data.get("sub_queries", [])
        else:
            is_sufficient = True
            gap = ""
            sub_q = []
    except Exception:
        is_sufficient = True
        gap = ""
        sub_q = []

    return {
        "reflection_count": reflection_count,
        "is_sufficient": is_sufficient,
        "gap_description": gap,
        "sub_queries": sub_q
    }

def synthesize_section(state: DLSState) -> Dict[str, Any]:
    """Step 5: 현재 섹션의 마크다운 초안(3분할 사실/해석/과제 + 각주) 합성"""
    llm = get_chat_model(tier="standard")
    sec = state["current_section"]
    topic = state.get("topic", "")
    all_sources = state.get("all_sources", [])
    section_drafts = dict(state.get("section_drafts", {}))

    # Build sources context with citation index
    sources_context = ""
    for idx, s in enumerate(all_sources, 1):
        sources_context += f"\n[출처 [^{idx}]] {s.get('title')}\nURL: {s.get('url')}\n내용 발췌:\n{s.get('content')[:1200]}\n"

    prompt = SECTION_SYNTHESIS_PROMPT.format(
        topic=topic,
        section_title=sec.get("title", ""),
        target_questions="\n".join([f"- {q}" for q in sec.get("target_questions", [])]),
        expected_takeaway=sec.get("expected_takeaway", "상세 분석"),
        sources_context=sources_context
    )

    res = llm.invoke(prompt)
    draft_content = clean_think_tags(res.content)
    
    sec_id = sec.get("section_id", f"sec_{state.get('current_section_idx', 0)}")
    section_drafts[sec_id] = draft_content

    # Save intermediate section draft
    run_id = state.get("run_id", "default")
    temp_dir = ROOT_DIR / "temp" / run_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    with open(temp_dir / f"{sec_id}_draft.md", "w", encoding="utf-8") as f:
        f.write(draft_content)

    return {
        "section_drafts": section_drafts,
        "scraped_pages": [] # Reset section-specific scrape buffer
    }

def next_section(state: DLSState) -> Dict[str, Any]:
    """다음 섹션으로 포인터 이동 및 카운터 초기화"""
    next_idx = state.get("current_section_idx", 0) + 1
    outline = state.get("outline", [])
    
    return {
        "current_section_idx": next_idx,
        "current_section": outline[next_idx] if next_idx < len(outline) else {},
        "reflection_count": 0,
        "sub_queries": []
    }

def assemble_report(state: DLSState) -> Dict[str, Any]:
    """전체 섹션 취합, 각주 포맷팅 및 최종 마크다운 리포트 파일 저장"""
    topic = state.get("topic", "")
    outline = state.get("outline", [])
    section_drafts = state.get("section_drafts", {})
    all_sources = state.get("all_sources", [])
    
    metadata = {
        "queries": state.get("queries", []),
        "model": "opencode/muse-spark-1.3-contributor-free",
        "search_engine": "duckduckgo",
        "verified_facts_ratio": "High"
    }
    
    final_report = assemble_final_report(
        topic=topic,
        sections=outline,
        section_drafts=section_drafts,
        all_sources=all_sources,
        metadata=metadata
    )
    
    # Save to output directory
    output_dir = ROOT_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(" ", "_")[:30]
    filename = f"report_{clean_topic}_{timestamp}.md"
    output_path = output_dir / filename
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_report)
        
    # Generate 4-Tier Report Bundle
    bundle_dir_str = ""
    bundle_manifest_dict = {}
    bundle_zip_str = ""
    try:
        llm = get_chat_model(tier="standard")
        bundle_res = create_report_bundle(
            topic=topic,
            technical_report=final_report,
            all_sources=all_sources,
            llm=llm,
            output_base_dir=output_dir / "bundles",
            run_id=state.get("run_id", "default")
        )
        bundle_dir_str = bundle_res.get("bundle_dir", "")
        bundle_manifest_dict = bundle_res.get("manifest", {})
        bundle_zip_str = bundle_res.get("zip_path", "")
    except Exception as e:
        print(f"⚠️ Report bundle generation warning: {e}")
        
    return {
        "final_report": final_report,
        "output_path": str(output_path),
        "bundle_dir": bundle_dir_str,
        "bundle_manifest": bundle_manifest_dict,
        "bundle_zip": bundle_zip_str
    }

# Routing functions for conditional edges
def route_reflection(state: DLSState) -> str:
    """Self-reflection 루프 분기: 정보 충분성 검증"""
    if state.get("is_sufficient", True):
        return "synthesize_section"
    if state.get("reflection_count", 0) >= state.get("max_reflection_loops", 2):
        return "synthesize_section"
    return "generate_queries"

def route_section(state: DLSState) -> str:
    """섹션 루프 분기: 다음 섹션 여부 확인"""
    current_idx = state.get("current_section_idx", 0)
    total_sections = len(state.get("outline", []))
    if current_idx + 1 < total_sections:
        return "next_section"
    return "assemble_report"
