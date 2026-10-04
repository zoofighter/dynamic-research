import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from langgraph.types import interrupt

from src.graphs.states import TopicOutlineState
from src.providers.rss import NewsRSSProvider
from src.providers.llm import get_chat_model
from src.prompts.topic_prompts import TOPIC_DISCOVERY_PROMPT, TOPIC_EXPANSION_PROMPT
from src.prompts.outline_prompts import OUTLINE_GENERATION_PROMPT, OUTLINE_REVISION_PROMPT

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def clean_think_tags(text: str) -> str:
    """Strip <think>...</think> tags produced by reasoning models."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def scan_past_reports(output_dir: Path) -> List[Dict[str, Any]]:
    """Scan previous research reports in output/ to prevent repetitive topics."""
    past = []
    if not output_dir.exists():
        return past
    for f in output_dir.glob("*.md"):
        try:
            # Read first 10 lines for title/topic
            with open(f, "r", encoding="utf-8") as fp:
                lines = [fp.readline() for _ in range(10)]
            first_line = lines[0] if lines else f.stem
            past.append({"filename": f.name, "topic": first_line.strip("# -*\n")})
        except Exception:
            pass
    return past[:5]

def discover_topics(state: TopicOutlineState) -> Dict[str, Any]:
    """
    뉴스 RSS(Google News RSS 전용)를 수집하고 LLM으로 클러스터링하여 추천 주제 목록을 생성합니다.
    (한경 직접 연동은 추후 TODO로 보류)
    """
    user_input = state.get("user_input", "반도체 AI 인프라")
    rss_provider = NewsRSSProvider()
    
    # 1. Google News RSS Fetch
    articles = rss_provider.fetch_feed(query=user_input, max_items=12)
    headlines = [{"title": a.title, "url": getattr(a, "link", getattr(a, "url", "")), "published": a.published} for a in articles]
    
    # 2. Past Reports Scan
    output_dir = ROOT_DIR / "output"
    past = scan_past_reports(output_dir)
    
    # 3. LLM Topic Clustering
    llm = get_chat_model(tier="fast")
    headlines_text = "\n".join([f"- {h['title']}" for h in headlines])
    past_text = "\n".join([f"- {p['topic']}" for p in past]) if past else "없음"
    
    prompt = TOPIC_DISCOVERY_PROMPT.format(
        user_hint=user_input,
        news_headlines=headlines_text or "최신 기술 동향",
        past_reports=past_text
    )
    
    try:
        res = llm.invoke(prompt)
        cleaned = clean_think_tags(res.content)
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            suggested = json.loads(match.group(0))
        else:
            suggested = [
                {"topic_id": "T1", "title": f"{user_input} 최신 기술 및 시장 동향", "rationale": "핵심 키워드 기반 기본 제안"}
            ]
    except Exception:
        suggested = [
            {"topic_id": "T1", "title": f"{user_input} 최신 기술 및 시장 동향", "rationale": "기본 제안"}
        ]
        
    return {
        "news_headlines": headlines,
        "past_reports": past,
        "suggested_topics": suggested
    }

def select_topic(state: TopicOutlineState) -> Dict[str, Any]:
    """
    HITL Interrupt: 사용자에게 추천 주제 목록을 제시하고 선택 또는 직접 입력을 대기합니다.
    """
    suggested = state.get("suggested_topics", [])
    options_summary = [f"[{t.get('topic_id', i+1)}] {t.get('title')}: {t.get('rationale', '')}" 
                       for i, t in enumerate(suggested)]
    
    selection = interrupt({
        "type": "topic_selection",
        "message": "리서치를 진행할 주제를 선택하거나 직접 새로운 주제를 입력해주세요.",
        "options": options_summary,
        "raw_topics": suggested
    })
    
    selected_text = selection.get("selected_topic") if isinstance(selection, dict) else str(selection)
    if not selected_text and suggested:
        selected_text = suggested[0].get("title", state.get("user_input", ""))
        
    return {"selected_topic": selected_text}

def expand_topic(state: TopicOutlineState) -> Dict[str, Any]:
    """선택된 주제의 타겟 독자, 리서치 깊이, 핵심 논쟁점을 분석합니다."""
    topic = state.get("selected_topic") or state.get("user_input", "")
    llm = get_chat_model(tier="standard")
    
    prompt = TOPIC_EXPANSION_PROMPT.format(
        topic=topic,
        user_input=state.get("user_input", "")
    )
    
    try:
        res = llm.invoke(prompt)
        cleaned = clean_think_tags(res.content)
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            analysis = json.loads(match.group(0))
        else:
            analysis = {
                "topic": topic,
                "target_audience": "도메인 실무자 및 투자자",
                "research_depth": "deep",
                "key_controversies": ["기술 경쟁력 및 양산 일정", "시장 점유율 파급력"],
                "core_hypothesis": f"{topic}의 실현 가능성과 시장 영향 검증"
            }
    except Exception:
        analysis = {
            "topic": topic,
            "target_audience": "도메인 실무자 및 투자자",
            "research_depth": "deep",
            "key_controversies": ["핵심 검증 요소"],
            "core_hypothesis": "최신 팩트 기반 검증"
        }
        
    return {"topic_analysis": analysis}

def generate_outlines(state: TopicOutlineState) -> Dict[str, Any]:
    """주제 분석 결과를 바탕으로 복수(A/B) 아웃라인 안을 생성합니다."""
    topic = state.get("selected_topic") or state.get("user_input", "")
    analysis = state.get("topic_analysis", {})
    llm = get_chat_model(tier="standard")
    
    prompt = OUTLINE_GENERATION_PROMPT.format(
        topic=topic,
        analysis=json.dumps(analysis, ensure_ascii=False, indent=2)
    )
    
    try:
        res = llm.invoke(prompt)
        cleaned = clean_think_tags(res.content)
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            proposals = json.loads(match.group(0))
        else:
            proposals = [{
                "proposal_id": "A",
                "theme": "표준 종합 분석",
                "sections": [
                    {"section_id": "sec_1", "title": "핵심 팩트 및 공급망 현황", "target_questions": ["최신 양산 및 공급 일정은?"], "expected_takeaway": "공급망 사실 확인"},
                    {"section_id": "sec_2", "title": "기술적 우위 및 병목 이슈", "target_questions": ["수율 및 기술적 과제는?"], "expected_takeaway": "기술 타당성 검증"},
                    {"section_id": "sec_3", "title": "시장 파급력 및 경쟁 구도", "target_questions": ["경쟁사 대비 영향은?"], "expected_takeaway": "시장 전망 수립"}
                ]
            }]
    except Exception:
        proposals = [{
            "proposal_id": "A",
            "theme": "표준 종합 분석",
            "sections": [
                {"section_id": "sec_1", "title": "핵심 팩트 및 일정", "target_questions": ["최신 현황은?"], "expected_takeaway": "일정 확인"}
            ]
        }]
        
    return {"outline_proposals": proposals}

def human_review(state: TopicOutlineState) -> Dict[str, Any]:
    """
    HITL Interrupt: 생성된 복수 아웃라인을 사용자에게 제시하고 수정 피드백 또는 승인을 대기합니다.
    """
    proposals = state.get("outline_proposals", [])
    
    feedback = interrupt({
        "type": "outline_review",
        "message": "아웃라인 제안을 확인하세요. 수정 사항이 있으면 입력하거나, 승인 시 'approve' 또는 선택한 안(A/B)을 전달해주세요.",
        "proposals": proposals
    })
    
    feedback_str = feedback.get("feedback") if isinstance(feedback, dict) else str(feedback)
    return {"human_feedback": feedback_str}

def route_human_feedback(state: TopicOutlineState) -> str:
    """사용자 피드백에 따라 아웃라인 수정(revise) 또는 승인 완료(approve)로 분기"""
    feedback = (state.get("human_feedback") or "").strip().lower()
    if "approve" in feedback or "승인" in feedback or feedback in ["a", "b", "ok", "yes", ""]:
        return "approve"
    return "revise"

def revise_outline(state: TopicOutlineState) -> Dict[str, Any]:
    """사용자 피드백을 반영하여 아웃라인을 재생성합니다."""
    llm = get_chat_model(tier="standard")
    proposals = state.get("outline_proposals", [])
    feedback = state.get("human_feedback", "")
    
    prompt = OUTLINE_REVISION_PROMPT.format(
        original_outline=json.dumps(proposals, ensure_ascii=False, indent=2),
        human_feedback=feedback
    )
    
    try:
        res = llm.invoke(prompt)
        cleaned = clean_think_tags(res.content)
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            revised_data = json.loads(match.group(0))
            sections = revised_data.get("sections", [])
            revised_proposals = [{
                "proposal_id": "Revised",
                "theme": "사용자 피드백 반영 아웃라인",
                "sections": sections
            }]
        else:
            revised_proposals = proposals
    except Exception:
        revised_proposals = proposals
        
    return {"outline_proposals": revised_proposals}

def finalize_outline(state: TopicOutlineState) -> Dict[str, Any]:
    """승인된 아웃라인을 approved_outline.json 규격으로 파일 및 State에 저장합니다."""
    topic = state.get("selected_topic") or state.get("user_input", "")
    proposals = state.get("outline_proposals", [])
    feedback = (state.get("human_feedback") or "").strip().upper()
    
    # Select chosen proposal (Default to first if not specified)
    chosen_proposal = proposals[0] if proposals else {}
    for p in proposals:
        if p.get("proposal_id", "").upper() == feedback:
            chosen_proposal = p
            break
            
    sections = chosen_proposal.get("sections", [])
    approved = {
        "topic": topic,
        "theme": chosen_proposal.get("theme", "종합 분석"),
        "approved_at": datetime.now().isoformat(),
        "sections": sections,
        "analysis": state.get("topic_analysis", {})
    }
    
    # Save to temp directory
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    temp_dir = ROOT_DIR / "temp" / run_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    outline_path = temp_dir / "approved_outline.json"
    
    with open(outline_path, "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    # Also save as latest_approved_outline.json
    with open(ROOT_DIR / "temp" / "latest_approved_outline.json", "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)
        
    return {
        "approved_outline": approved,
        "run_id": run_id
    }
