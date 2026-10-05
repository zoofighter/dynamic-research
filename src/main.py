import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.graphs.topic_outline_graph import topic_outline_app
from src.graphs.dls_research_graph import dls_research_app
from src.utils.config import get_config

def run_pipeline(mode: str = "direct", topic_hint: str = "", auto_approve: bool = False, outline_path: str = None):
    print("=" * 75)
    print("🤖 [Dynamic Research] 자율 리서치 에이전트 시스템 가동")
    print(f"   • 모드: {'주제 자동 발굴 (Google News RSS)' if mode == 'discover' else '직접 주제 입력'}")
    print(f"   • 입력 주제/힌트: {topic_hint or '최신 반도체 AI 기술 동향'}")
    print("=" * 75)

    config = get_config()
    approved_outline = None

    if outline_path and os.path.exists(outline_path):
        try:
            with open(outline_path, "r", encoding="utf-8") as fp:
                approved_outline = json.load(fp)
            print(f"\n📑 [사전 승인된 아웃라인 직접 로드] {outline_path}")
            print(f"   • 주제: {approved_outline.get('topic')}")
            print(f"   • 테마: {approved_outline.get('theme')}")
            print(f"   • 섹션 수: {len(approved_outline.get('sections', []))}개")
            print("   👉 Stage 1 건너뛰고 Stage 2 (DLS 자율 심층 리서치 Graph 2)로 즉시 진입합니다.")
        except Exception as e:
            print(f"⚠️ 아웃라인 파일 로드 실패: {e}")

    if not approved_outline:
        thread_id_g1 = f"thread_g1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        g1_config = {"configurable": {"thread_id": thread_id_g1}}

        # ---------------------------------------------------------
        # Stage 1: TopicOutlineGraph (Graph 1)
        # ---------------------------------------------------------
        print("\n📋 [Stage 1] 아웃라인 설계 및 주제 탐색 시작 (Graph 1)...")
    initial_state = {
        "user_input": topic_hint or "최신 AI 반도체 동향",
        "mode": mode
    }

    # Step-by-step or streaming execution to handle interrupts
    approved_outline = None
    events = topic_outline_app.stream(initial_state, g1_config, stream_mode="values")
    
    current_state = None
    for event in events:
        current_state = event

    # Check for interrupts
    snapshot = topic_outline_app.get_state(g1_config)
    while snapshot.next:
        next_node = snapshot.next[0]
        tasks = snapshot.tasks
        interrupt_val = tasks[0].interrupts[0].value if tasks and tasks[0].interrupts else {}
        
        int_type = interrupt_val.get("type")
        msg = interrupt_val.get("message", "사용자 입력을 대기합니다.")
        print(f"\n🔔 [휴먼 인터럽트 (HITL)] {msg}")

        if int_type == "topic_selection":
            options = interrupt_val.get("options", [])
            for opt in options:
                print(f"   {opt}")
            if auto_approve:
                chosen = interrupt_val.get("raw_topics", [{}])[0].get("title", topic_hint)
                print(f"   👉 [Auto-Approve] 자동 선택: {chosen}")
            else:
                user_choice = input("\n선택할 번호 또는 새 주제 입력 [엔터=1번]: ").strip()
                if not user_choice:
                    chosen = interrupt_val.get("raw_topics", [{}])[0].get("title", topic_hint)
                else:
                    chosen = user_choice
            # Resume
            topic_outline_app.update_state(g1_config, {"selected_topic": chosen}, as_node=next_node)
            for event in topic_outline_app.stream(None, g1_config, stream_mode="values"):
                current_state = event
            snapshot = topic_outline_app.get_state(g1_config)

        elif int_type == "outline_review":
            proposals = interrupt_val.get("proposals", [])
            for p in proposals:
                print(f"\n   [{p.get('proposal_id')}] 테마: {p.get('theme')}")
                for s in p.get("sections", []):
                    print(f"       - {s.get('title')}: {s.get('target_questions')}")
            
            if auto_approve:
                feedback = "approve"
                print("   👉 [Auto-Approve] 아웃라인 즉시 승인")
            else:
                feedback = input("\n승인하시겠습니까? (엔터/approve=승인, 수정요청 내용 입력): ").strip()
                if not feedback:
                    feedback = "approve"
            # Resume
            topic_outline_app.update_state(g1_config, {"human_feedback": feedback}, as_node=next_node)
            for event in topic_outline_app.stream(None, g1_config, stream_mode="values"):
                current_state = event
            snapshot = topic_outline_app.get_state(g1_config)

    approved_outline = current_state.get("approved_outline") if current_state else None
    if not approved_outline:
        print("❌ 승인된 아웃라인이 없습니다.")
        return

    print(f"\n✅ [Stage 1 완료] 아웃라인 최종 승인: '{approved_outline.get('topic')}'")
    print(f"   섹션 수: {len(approved_outline.get('sections', []))}개")

    # ---------------------------------------------------------
    # Stage 2: DLSResearchGraph (Graph 2)
    # ---------------------------------------------------------
    print("\n🚀 [Stage 2] DLS 자율 심층 리서치 시작 (Graph 2)...")
    thread_id_g2 = f"thread_g2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    g2_config = {"configurable": {"thread_id": thread_id_g2}}

    g2_initial_state = {
        "topic": approved_outline.get("topic"),
        "outline": approved_outline.get("sections", []),
        "config": config,
        "run_id": current_state.get("run_id") or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }

    final_g2_state = None
    for event in dls_research_app.stream(g2_initial_state, g2_config, stream_mode="values"):
        final_g2_state = event
        curr_sec = event.get("current_section", {})
        if curr_sec:
            print(f"   진행 중 섹션: {curr_sec.get('title', '')} (Reflect 루프: {event.get('reflection_count', 0)})")

    out_path = final_g2_state.get("output_path") if final_g2_state else None
    print("\n" + "=" * 75)
    print("🎉 [최종 완료] Dynamic Research 파이프라인 완결!")
    print(f"📄 최종 마크다운 리포트 경로: {out_path}")
    print("=" * 75)
    return out_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic Research Autonomous Agent Pipeline")
    parser.add_argument("--mode", choices=["discover", "direct"], default="direct", help="Research mode")
    parser.add_argument("--topic", type=str, default="마이크론 12단 HBM3E 엔비디아 퀄 승인 및 양산 일정", help="Research topic or hint")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve HITL prompts for testing")
    parser.add_argument("--outline", type=str, default=None, help="Path to pre-approved outline JSON")
    args = parser.parse_args()

    run_pipeline(mode=args.mode, topic_hint=args.topic, auto_approve=args.auto_approve, outline_path=args.outline)
