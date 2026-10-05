import os
import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.utils.bundle_packager import (
    clean_think_tags,
    build_bundle_context,
    create_report_bundle,
    get_available_bundles
)


def test_clean_think_tags():
    raw = "<think>내부 추론 과정</think># 최종 리포트 결과"
    assert clean_think_tags(raw) == "# 최종 리포트 결과"


def test_build_bundle_context():
    sample_report = """---
topic: "테스트 토픽"
---
# 보고서 제목
확인된 사실 1
"""
    sources = [{"title": "출처1", "url": "https://example.com"}]
    ctx = build_bundle_context(sample_report, sources)
    assert "확인된 사실 1" in ctx
    assert "[^1]: 출처1" in ctx


def test_create_report_bundle(tmp_path):
    topic = "차세대 HBM4 공급망 경쟁 분석"
    tech_report = """# 📊 차세대 HBM4 공급망 리포트
## 1. 확인된 사실 (Facts)
- 2026년 HBM4 점유율은 SK하이닉스 50%, 삼성전자 33%이다.
## 2. 에이전트 해석 (Analysis)
삼성전자의 반등은 엔비디아 SiP 테스트 결과에 기인한다.
"""
    sources = [
        {"title": "조선비즈 HBM 기사", "url": "https://chosun.com/1"},
        {"title": "디일렉 마이크론 기사", "url": "https://thelec.kr/2"}
    ]
    
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        MagicMock(content="<think>임원 요약</think># 👔 [Executive Strategy Brief] 차세대 HBM4\n## 1. 3대 결론\n- 결론 1"),
        MagicMock(content="# 📊 [Competitive Benchmark Matrix] 차세대 HBM4\n## 1. 비교표"),
        MagicMock(content="# ⚠️ [Risk Due-Diligence Checklist] 차세대 HBM4\n## 1. 신뢰도 평가")
    ]
    
    bundle_res = create_report_bundle(
        topic=topic,
        technical_report=tech_report,
        all_sources=sources,
        llm=mock_llm,
        output_base_dir=tmp_path
    )
    
    bundle_dir = Path(bundle_res["bundle_dir"])
    assert bundle_dir.exists()
    
    # 4 files check
    f_exec = bundle_dir / "01_executive_brief.md"
    f_tech = bundle_dir / "02_technical_deepdive.md"
    f_bench = bundle_dir / "03_competitive_benchmark.md"
    f_risk = bundle_dir / "04_risk_due_diligence.md"
    f_manifest = bundle_dir / "00_bundle_manifest.json"
    f_zip = bundle_dir / "full_bundle.zip"
    
    assert f_exec.exists()
    assert f_tech.exists()
    assert f_bench.exists()
    assert f_risk.exists()
    assert f_manifest.exists()
    assert f_zip.exists()
    
    # Verify manifest JSON
    with open(f_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["topic"] == topic
    assert manifest_data["reports_count"] == 4
    assert len(manifest_data["reports"]) == 4
    
    # Verify ZIP file contents
    with zipfile.ZipFile(f_zip, "r") as z:
        names = z.namelist()
        assert "00_bundle_manifest.json" in names
        assert "01_executive_brief.md" in names
        assert "02_technical_deepdive.md" in names
        assert "03_competitive_benchmark.md" in names
        assert "04_risk_due_diligence.md" in names
        
    # Verify get_available_bundles
    bundles = get_available_bundles(tmp_path)
    assert len(bundles) == 1
    assert bundles[0]["topic"] == topic
