import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

OUTLINES_DIR = "output/outlines"
LATEST_APPROVED_PATH = "temp/latest_approved_outline.json"


def sanitize_filename(name: str, max_len: int = 40) -> str:
    """파일명으로 안전한 문자열로 정제합니다."""
    cleaned = re.sub(r'[^\w가-힣0-9\-]+', '_', name).strip('_')
    return cleaned[:max_len] if cleaned else "outline"


def save_outline_history(
    topic: str,
    theme: str,
    sections: List[Dict[str, Any]],
    source: str = "approved",
    memo: str = "",
    save_dir: str = OUTLINES_DIR,
    sync_to_latest: bool = True,
    core_questions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    토픽 및 목차(Outline)를 output/outlines/ 디렉터리에 타임스탬프와 함께 영구 저장하고,
    선택 시 temp/latest_approved_outline.json과 동기화합니다.
    선택된 핵심 질문(core_questions) 목록도 함께 보관합니다.
    """
    os.makedirs(save_dir, exist_ok=True)
    now = datetime.now()
    now_iso = now.isoformat()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    
    slug = sanitize_filename(topic)
    outline_id = f"outline_{timestamp_str}_{slug}"
    file_path = os.path.join(save_dir, f"{outline_id}.json")
    
    cleaned_questions = [q.strip() for q in core_questions if q and q.strip()] if core_questions else []
    
    record = {
        "id": outline_id,
        "saved_at": now_iso,
        "topic": topic.strip(),
        "theme": theme.strip() if theme else "맞춤형 분석 관점",
        "source": source,
        "memo": memo.strip() if memo else "",
        "core_questions": cleaned_questions,
        "sections": sections,
        "section_count": len(sections),
        "file_path": file_path
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        
    if sync_to_latest:
        os.makedirs(os.path.dirname(LATEST_APPROVED_PATH), exist_ok=True)
        with open(LATEST_APPROVED_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "id": record["id"],
                "topic": record["topic"],
                "theme": record["theme"],
                "core_questions": record["core_questions"],
                "sections": record["sections"],
                "saved_at": record["saved_at"]
            }, f, ensure_ascii=False, indent=2)
            
    return record


def list_outline_history(save_dir: str = OUTLINES_DIR) -> List[Dict[str, Any]]:
    """
    저장된 모든 토픽 및 목차 히스토리 목록을 최신순으로 반환합니다.
    """
    if not os.path.exists(save_dir):
        return []
    
    records = []
    for fname in os.listdir(save_dir):
        if fname.endswith(".json") and fname != "index.json":
            fpath = os.path.join(save_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "topic" in data:
                        data["file_path"] = fpath
                        data["id"] = data.get("id") or fname[:-5]
                        data["saved_at"] = data.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                        data["section_count"] = len(data.get("sections", []))
                        data["core_questions"] = data.get("core_questions", [])
                        records.append(data)
            except Exception:
                continue
                
    # 최신 등록순 정렬
    records.sort(key=lambda r: r.get("saved_at", ""), reverse=True)
    return records


def load_outline_history(outline_id: str, save_dir: str = OUTLINES_DIR) -> Optional[Dict[str, Any]]:
    """
    특정 outline_id에 해당하는 목차 데이터를 불러옵니다.
    """
    if not os.path.exists(save_dir):
        return None
        
    fpath = os.path.join(save_dir, f"{outline_id}.json")
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["file_path"] = fpath
                data["core_questions"] = data.get("core_questions", [])
                return data
        except Exception:
            return None
            
    for fname in os.listdir(save_dir):
        if fname.endswith(".json"):
            cur_path = os.path.join(save_dir, fname)
            try:
                with open(cur_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == outline_id:
                        data["file_path"] = cur_path
                        data["core_questions"] = data.get("core_questions", [])
                        return data
            except Exception:
                continue
    return None


def delete_outline_history(outline_id: str, save_dir: str = OUTLINES_DIR) -> bool:
    """
    특정 outline_id의 히스토리 파일을 삭제합니다.
    """
    if not os.path.exists(save_dir):
        return False
        
    target = load_outline_history(outline_id, save_dir)
    if target and target.get("file_path") and os.path.exists(target["file_path"]):
        try:
            os.remove(target["file_path"])
            return True
        except Exception:
            return False
    return False


def set_active_approved_outline(record: Dict[str, Any], target_path: str = LATEST_APPROVED_PATH) -> None:
    """
    선택한 히스토리 레코드를 temp/latest_approved_outline.json 활성 목차로 갱신합니다.
    """
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump({
            "id": record.get("id", ""),
            "topic": record.get("topic", ""),
            "theme": record.get("theme", ""),
            "core_questions": record.get("core_questions", []),
            "sections": record.get("sections", []),
            "saved_at": record.get("saved_at", datetime.now().isoformat())
        }, f, ensure_ascii=False, indent=2)


def sync_existing_latest_to_history(save_dir: str = OUTLINES_DIR) -> None:
    """기존 temp/latest_approved_outline.json이 존재하고 히스토리가 비어있을 경우 초기 마이그레이션 수행"""
    if os.path.exists(LATEST_APPROVED_PATH):
        existing = list_outline_history(save_dir)
        if not existing:
            try:
                with open(LATEST_APPROVED_PATH, "r", encoding="utf-8") as f:
                    curr = json.load(f)
                if curr.get("topic") and curr.get("sections"):
                    save_outline_history(
                        topic=curr["topic"],
                        theme=curr.get("theme", "기존 승인 목차"),
                        sections=curr["sections"],
                        source="migrated",
                        memo="기존 활성 목차 자동 이관",
                        save_dir=save_dir,
                        sync_to_latest=False,
                        core_questions=curr.get("core_questions", [])
                    )
            except Exception:
                pass
