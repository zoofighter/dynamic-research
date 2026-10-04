import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.graphs.topic_outline_graph import topic_outline_app
from src.utils.config import get_config

def run_topic_outline(mode: str = "discover", topic_hint: str = "", auto_approve: bool = False):
    print("=" * 75)
    print("💡 [Topic & Outline Proposer] AI 실시간 주제 발굴 및 목차 제안 에이전트")
    print(f"   • 모드: {'🔥 실시간 뉴스 기반 주제 자동 발굴 (Discover)' if mode == 'discover' else '✍️  직접 주제 입력 (Direct)'}")
    print(f"   • 입력 키워드/힌트: {topic_hint or '반도체 AI 인프라'}")
    print("=" * 75)

    thread_id = f"thread_to_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_input": topic_hint or "반도체 AI 인프라",
        "mode": mode
    }

    current_state = None
    events = topic_outline_app.stream(initial_state, config, stream_mode="values")
    for event in events:
        current_state = event

    snapshot = topic_outline_app.get_state(config)
    while snapshot.next:
        next_node = snapshot.next[0]
        tasks = snapshot.tasks
        interrupt_val = tasks[0].interrupts[0].value if tasks and tasks[0].interrupts else {}

        int_type = interrupt_val.get("type")
        msg = interrupt_val.get("message", "사용자 입력을 대기합니다.")

        if int_type == "topic_selection":
            print(f"\n📢 [Step 1: 주제 선택] {msg}")
            raw_topics = interrupt_val.get("raw_topics", [])
            for i, t in enumerate(raw_topics, 1):
                print(f"\n   [{i}] {t.get('title')}")
                print(f"       ↳ 근거: {t.get('rationale')}")
                print(f"       ↳ 추천 각도: {t.get('angle')}")

            if auto_approve:
                chosen = raw_topics[0].get("title", topic_hint) if raw_topics else topic_hint
                print(f"\n   👉 [Auto-Approve] 1번 주제 자동 선택: {chosen}")
            else:
                user_choice = input("\n👉 원하는 번호를 선택하거나 새 주제를 직접 입력하세요 [엔터=1번]: ").strip()
                if not user_choice:
                    chosen = raw_topics[0].get("title", topic_hint) if raw_topics else topic_hint
                elif user_choice.isdigit() and 1 <= int(user_choice) <= len(raw_topics):
                    chosen = raw_topics[int(user_choice)-1].get("title")
                else:
                    chosen = user_choice

            topic_outline_app.update_state(config, {"selected_topic": chosen}, as_node=next_node)
            for event in topic_outline_app.stream(None, config, stream_mode="values"):
                current_state = event
            snapshot = topic_outline_app.get_state(config)

        elif int_type == "outline_review":
            print(f"\n📑 [Step 2: 아웃라인 검토] {msg}")
            proposals = interrupt_val.get("proposals", [])
            for p in proposals:
                print(f"\n" + "-" * 65)
                print(f"📂 [제안 {p.get('proposal_id')}] 테마: {p.get('theme')}")
                print("-" * 65)
                for s in p.get("sections", []):
                    print(f"   • {s.get('title')}")
                    for q in s.get("target_questions", []):
                        print(f"       - Q: {q}")
                    if s.get("expected_takeaway"):
                        print(f"       - 기대 도출점: {s.get('expected_takeaway')}")

            if auto_approve:
                feedback = "A"
                print("\n   👉 [Auto-Approve] A안 즉시 승인")
            else:
                feedback = input("\n👉 승인할 안을 선택하거나 수정 요청을 입력하세요 [엔터/A/B/수정피드백]: ").strip()
                if not feedback:
                    feedback = "A"

            topic_outline_app.update_state(config, {"human_feedback": feedback}, as_node=next_node)
            for event in topic_outline_app.stream(None, config, stream_mode="values"):
                current_state = event
            snapshot = topic_outline_app.get_state(config)

    approved = current_state.get("approved_outline")
    if approved:
        print("\n" + "=" * 75)
        print("🎉 [최종 확정] 승인된 리서치 아웃라인:")
        print(f"📌 주제: {approved.get('topic')}")
        print(f"🏷️  테마: {approved.get('theme')}")
        print(f"📑 섹션 수: {len(approved.get('sections', []))}개")
        for i, s in enumerate(approved.get('sections', []), 1):
            print(f"   [{i}] {s.get('title')}")
        print(f"\n💾 저장 경로: temp/latest_approved_outline.json")
        print("=" * 75)
        return approved
    else:
        print("❌ 아웃라인 확정에 실패했습니다.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Topic & Outline Proposer Agent")
    parser.add_argument("--mode", choices=["discover", "direct"], default="discover", help="discover: 실시간 뉴스 기반 추천 / direct: 직접 입력")
    parser.add_argument("--topic", type=str, default="반도체 HBM 차세대 패키징", help="주제 힌트 또는 직접 입력 주제")
    parser.add_argument("--auto-approve", action="store_true", help="테스트용 자동 승인")
    args = parser.parse_args()

    run_topic_outline(mode=args.mode, topic_hint=args.topic, auto_approve=args.auto_approve)
