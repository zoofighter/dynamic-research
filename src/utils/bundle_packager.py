"""
다각화 보고서 패키지 (Multi-Tier Report Bundle) 자동 생성 및 패키징 모듈
- 1회 심층 리서치 결과로부터 4대 전문 보고서 생성:
  1. 01_executive_brief.md (경영진 1-Pager 브리프)
  2. 02_technical_deepdive.md (심층 기술·산업 상세 보고서)
  3. 03_competitive_benchmark.md (경쟁사 벤치마크 매트릭스)
  4. 04_risk_due_diligence.md (리스크 진단 & Due-Diligence 체크리스트)
- 00_bundle_manifest.json 메타데이터 매니페스트 저장
- full_bundle.zip 원클릭 다운로드용 압축 파일 생성
"""

import os
import re
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.prompts.bundle_prompts import (
    EXECUTIVE_BRIEF_PROMPT,
    COMPETITIVE_BENCHMARK_PROMPT,
    RISK_DUE_DILIGENCE_PROMPT
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def clean_think_tags(text: str) -> str:
    """LLM의 추론 태그 제거"""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def build_bundle_context(technical_report: str, all_sources: Optional[List[Dict[str, Any]]] = None) -> str:
    """원천 기술 보고서 및 출처로부터 핵심 컨텍스트 블록 추출"""
    context_parts = []
    
    # 원문 보고서의 주요 팩트와 분석 추출 (최대 10,000자)
    clean_report = re.sub(r"^---.*?---\s*", "", technical_report, flags=re.DOTALL).strip()
    context_parts.append("=== [원천 심층 리서치 본문 발췌] ===")
    context_parts.append(clean_report[:10000])
    
    if all_sources:
        context_parts.append("\n=== [주요 인용 출처 목록] ===")
        for idx, s in enumerate(all_sources[:15], 1):
            title = s.get("title", "출처")
            url = s.get("url", "")
            context_parts.append(f"[^{idx}]: {title} ({url})")
            
    return "\n".join(context_parts)


def generate_executive_brief(topic: str, context_data: str, llm) -> str:
    """경영진 전략 1-Pager 브리프 생성"""
    prompt = EXECUTIVE_BRIEF_PROMPT.format(topic=topic, context_data=context_data)
    res = llm.invoke(prompt)
    content = res.content if hasattr(res, "content") else str(res)
    return clean_think_tags(content)


def generate_competitive_benchmark(topic: str, context_data: str, llm) -> str:
    """경쟁사 벤치마크 매트릭스 생성"""
    prompt = COMPETITIVE_BENCHMARK_PROMPT.format(topic=topic, context_data=context_data)
    res = llm.invoke(prompt)
    content = res.content if hasattr(res, "content") else str(res)
    return clean_think_tags(content)


def generate_risk_checklist(topic: str, context_data: str, llm) -> str:
    """리스크 진단 & Due-Diligence 체크리스트 생성"""
    prompt = RISK_DUE_DILIGENCE_PROMPT.format(topic=topic, context_data=context_data)
    res = llm.invoke(prompt)
    content = res.content if hasattr(res, "content") else str(res)
    return clean_think_tags(content)


def create_report_bundle(
    topic: str,
    technical_report: str,
    all_sources: Optional[List[Dict[str, Any]]] = None,
    llm: Any = None,
    output_base_dir: Optional[Path] = None,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    4대 전문 보고서를 생성하고, manifest.json 및 zip 파일로 일괄 패키징합니다.
    """
    base_dir = output_base_dir or (ROOT_DIR / "output" / "bundles")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(" ", "_")[:30]
    bundle_name = f"bundle_{clean_topic}_{timestamp}"
    bundle_dir = base_dir / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 원천 데이터 컨텍스트 빌드
    context_data = build_bundle_context(technical_report, all_sources)
    
    # 2. 4대 보고서 생성
    # 보고서 2: 심층 기술·산업 상세 보고서 (원문 리포트)
    tech_content = technical_report
    
    # LLM이 전달되지 않은 경우 기본 요약 생성기 대체 또는 안내
    if llm:
        exec_content = generate_executive_brief(topic, context_data, llm)
        benchmark_content = generate_competitive_benchmark(topic, context_data, llm)
        risk_content = generate_risk_checklist(topic, context_data, llm)
    else:
        exec_content = f"# 👔 [Executive Brief] {topic}\n\nLLM 인스턴스가 주입되지 않아 기본 템플릿으로 출력되었습니다.\n\n{context_data[:1500]}"
        benchmark_content = f"# 📊 [Competitive Benchmark] {topic}\n\nLLM 인스턴스가 주입되지 않아 기본 템플릿으로 출력되었습니다.\n\n{context_data[:1500]}"
        risk_content = f"# ⚠️ [Risk Due-Diligence] {topic}\n\nLLM 인스턴스가 주입되지 않아 기본 템플릿으로 출력되었습니다.\n\n{context_data[:1500]}"

    # 파일 저장 목록
    report_specs = [
        ("01_executive_brief.md", "경영진 전략 1-Pager 브리프", exec_content, "👔"),
        ("02_technical_deepdive.md", "심층 기술·산업 상세 보고서", tech_content, "🔬"),
        ("03_competitive_benchmark.md", "경쟁사 벤치마크 매트릭스", benchmark_content, "📊"),
        ("04_risk_due_diligence.md", "리스크 진단 & Due-Diligence", risk_content, "⚠️")
    ]
    
    saved_reports = {}
    manifest_reports_list = []
    
    for filename, title, content, icon in report_specs:
        file_path = bundle_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        word_count = len(content.split())
        saved_reports[filename] = {
            "title": title,
            "filename": filename,
            "path": str(file_path),
            "content": content,
            "word_count": word_count,
            "icon": icon
        }
        manifest_reports_list.append({
            "id": filename.split("_")[0],
            "filename": filename,
            "title": title,
            "icon": icon,
            "word_count": word_count,
            "path": str(file_path)
        })
        
    # 3. 00_bundle_manifest.json 생성
    manifest_data = {
        "bundle_id": bundle_name,
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "run_id": run_id or "default",
        "total_sources_count": len(all_sources) if all_sources else 0,
        "reports_count": len(report_specs),
        "reports": manifest_reports_list
    }
    
    manifest_path = bundle_dir / "00_bundle_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        
    # 4. full_bundle.zip 생성
    zip_path = bundle_dir / "full_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
        zip_f.write(manifest_path, arcname="00_bundle_manifest.json")
        for filename, _, _, _ in report_specs:
            file_path = bundle_dir / filename
            zip_f.write(file_path, arcname=filename)
            
    return {
        "bundle_id": bundle_name,
        "bundle_dir": str(bundle_dir),
        "manifest_path": str(manifest_path),
        "zip_path": str(zip_path),
        "manifest": manifest_data,
        "reports": saved_reports
    }


def get_available_bundles(output_base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """생성된 보고서 번들 목록 조회"""
    base_dir = output_base_dir or (ROOT_DIR / "output" / "bundles")
    if not base_dir.exists():
        return []
        
    bundles = []
    for b_dir in sorted(base_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not b_dir.is_dir():
            continue
        manifest_file = b_dir / "00_bundle_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    manifest["dir_path"] = str(b_dir)
                    manifest["zip_path"] = str(b_dir / "full_bundle.zip")
                    bundles.append(manifest)
            except Exception:
                continue
                
    return bundles
