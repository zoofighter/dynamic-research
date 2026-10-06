import os
import shutil
import pytest
from src.utils.outline_history import (
    save_outline_history,
    list_outline_history,
    load_outline_history,
    delete_outline_history,
    set_active_approved_outline,
    sync_existing_latest_to_history
)

TEST_DIR = "temp/test_outlines_history"

@pytest.fixture(autouse=True)
def cleanup():
    os.makedirs(TEST_DIR, exist_ok=True)
    yield
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

def test_save_and_list_history():
    topic = "차세대 HBF 반도체 시장"
    theme = "산업 및 비즈니스 전략"
    sections = [
        {"title": "섹션 1", "target_questions": ["질문 1", "질문 2"]},
        {"title": "섹션 2", "target_questions": ["질문 3"]}
    ]
    
    # Save record
    record = save_outline_history(
        topic=topic,
        theme=theme,
        sections=sections,
        source="approved",
        memo="테스트 메모",
        save_dir=TEST_DIR,
        sync_to_latest=False
    )
    
    assert record["id"].startswith("outline_")
    assert record["topic"] == topic
    assert record["section_count"] == 2
    assert os.path.exists(record["file_path"])
    
    # List history
    history = list_outline_history(save_dir=TEST_DIR)
    assert len(history) == 1
    assert history[0]["id"] == record["id"]
    assert history[0]["topic"] == topic

def test_load_and_delete_history():
    record = save_outline_history(
        topic="테스트 주제 B",
        theme="기술 사양 관점",
        sections=[{"title": "기술 분석", "target_questions": ["수율"]}],
        save_dir=TEST_DIR,
        sync_to_latest=False
    )
    
    loaded = load_outline_history(record["id"], save_dir=TEST_DIR)
    assert loaded is not None
    assert loaded["topic"] == "테스트 주제 B"
    assert len(loaded["sections"]) == 1
    
    deleted = delete_outline_history(record["id"], save_dir=TEST_DIR)
    assert deleted is True
    
    after_list = list_outline_history(save_dir=TEST_DIR)
    assert len(after_list) == 0

def test_set_active_approved_outline():
    record = {
        "id": "test_id",
        "topic": "활성 목차 테스트",
        "theme": "전략 관점",
        "sections": [{"title": "섹션 A", "target_questions": ["Q1"]}],
        "saved_at": "2026-10-06T15:00:00"
    }
    target_file = os.path.join(TEST_DIR, "test_latest.json")
    set_active_approved_outline(record, target_path=target_file)
    
    assert os.path.exists(target_file)
    import json
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["topic"] == "활성 목차 테스트"
    assert data["sections"][0]["title"] == "섹션 A"

def test_core_questions_persistence():
    topic = "차세대 HBM4 패키징 및 수율"
    theme = "기술 아키텍처 관점"
    sections = [
        {"title": "HBM4 16단 하이브리드 본딩", "target_questions": ["TSV 피치 및 접합 공정 수율"]}
    ]
    core_questions = [
        "1. TSV 및 하이브리드 본딩 공정 수율은 상용화 수준(80% 이상)에 도달했는가?",
        "2. 주요 메모리 3사의 16단 양산 샘플 출하 일정은 언제인가?",
        "3. 베이스 다이 파운드리 제조 파트너십(TSMC vs 자체 파운드리) 구도는 어떠한가?"
    ]
    
    # 저장 및 동기화 검증
    target_latest = os.path.join(TEST_DIR, "test_core_latest.json")
    record = save_outline_history(
        topic=topic,
        theme=theme,
        sections=sections,
        source="ai_outline_B",
        memo="핵심질문 연동 테스트",
        save_dir=TEST_DIR,
        sync_to_latest=False,
        core_questions=core_questions
    )
    
    assert record["core_questions"] == core_questions
    
    # 목록 조회 시 core_questions 포함 여부
    hist = list_outline_history(save_dir=TEST_DIR)
    assert len(hist) == 1
    assert hist[0]["core_questions"] == core_questions
    
    # 개별 조회 시 core_questions 포함 여부
    loaded = load_outline_history(record["id"], save_dir=TEST_DIR)
    assert loaded is not None
    assert loaded["core_questions"] == core_questions
    
    # 활성 목차 파일 갱신 시 core_questions 포함 여부
    set_active_approved_outline(loaded, target_path=target_latest)
    assert os.path.exists(target_latest)
    import json
    with open(target_latest, "r", encoding="utf-8") as f:
        latest_data = json.load(f)
    assert latest_data["core_questions"] == core_questions

