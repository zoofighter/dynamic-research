import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.providers.search import get_search_provider
from src.providers.scraper import get_scraper_provider
from src.providers.llm import get_chat_model
from src.utils.dedup import deduplicate_results

def run_local_dls(topic: str = "마이크론 12단 HBM3E 엔비디아 퀄 승인 및 양산 현황", max_pages: int = 3):
    print("=" * 70)
    print(f"🚀 [Local DLS] 자율 리서치 시작: '{topic}'")
    print("   • LLM 엔진: Local Ollama (qwen3.8:27b)")
    print("   • 검색 엔진: DuckDuckGo (무료 실시간 웹 검색)")
    print("   • 크롤러: Trafilatura (로컬 마크다운 추출)")
    print("=" * 70)

    start_time = time.perf_counter()
    llm = get_chat_model(tier="standard")
    search_provider = get_search_provider("duckduckgo")
    scraper_provider = get_scraper_provider("trafilatura")

    # ----------------------------------------------------
    # Step 1: 쿼리 분해 (Query Decomposition)
    # ----------------------------------------------------
    print("\n🔍 [Step 1] 로컬 LLM이 검색 쿼리를 분해하는 중...")
    decomp_prompt = f"""당신은 심층 리서치 에이전트입니다. 다음 리서치 주제에 대해 최신 팩트를 다각도로 수집하기 위한 최적의 검색 쿼리 2~3개를 한 줄에 하나씩 출력하세요.
(설명이나 번호 없이 오직 검색 키워드만 한 줄에 하나씩 출력)

주제: {topic}
"""
    decomp_res = llm.invoke(decomp_prompt)
    queries = [q.strip().strip("-").strip("1234567890.").strip() for q in decomp_res.content.strip().split("\n") if q.strip()][:3]
    if not queries:
        queries = [topic, f"{topic} 최신 뉴스"]

    print("   생성된 검색 쿼리:")
    for i, q in enumerate(queries, 1):
        print(f"   [{i}] {q}")

    # ----------------------------------------------------
    # Step 2: 실시간 웹 검색 (Live Web Search)
    # ----------------------------------------------------
    print("\n🌐 [Step 2] DuckDuckGo 실시간 웹 검색 수행 중...")
    all_search_results = []
    for q in queries:
        res = search_provider.search(q, max_results=3)
        for r in res:
            all_search_results.append({
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "query": q
            })

    # 중복 URL 제거
    deduped_results = deduplicate_results(all_search_results, key="url")[:max_pages]
    print(f"   총 {len(all_search_results)}개 중 고유 1차 출처 {len(deduped_results)}개 선별:")
    for i, r in enumerate(deduped_results, 1):
        print(f"   [{i}] {r['title'][:45]}... ({r['url'][:55]})")

    # ----------------------------------------------------
    # Step 3: 웹 원문 직접 방문 및 텍스트 파싱 (Deep Scraping)
    # ----------------------------------------------------
    print("\n📄 [Step 3] 웹페이지 원문 직접 방문 및 로컬 마크다운 추출 중...")
    scraped_documents = []
    for i, item in enumerate(deduped_results, 1):
        print(f"   [{i}/{len(deduped_results)}] 스크랩 중: {item['url'][:60]}...")
        doc = scraper_provider.scrape(item["url"])
        if doc.success and doc.content:
            scraped_documents.append({
                "index": len(scraped_documents) + 1,
                "url": item["url"],
                "title": doc.title or item["title"],
                "content": doc.content[:1500]  # 핵심 본문 발췌
            })
            print(f"       ✅ 성공 ({len(doc.content[:1500])}자 발췌)")
        else:
            # Fallback to search snippet
            if item.get("snippet"):
                scraped_documents.append({
                    "index": len(scraped_documents) + 1,
                    "url": item["url"],
                    "title": item["title"],
                    "content": item["snippet"]
                })
                print("       ⚠️ 본문 실패 -> 검색 스니펫으로 대체")

    if not scraped_documents:
        print("❌ 유효한 웹 데이터를 확보하지 못했습니다.")
        return

    # ----------------------------------------------------
    # Step 4 & 5: 로컬 LLM 리포트 합성 (Synthesis with Citations)
    # ----------------------------------------------------
    print("\n✍️  [Step 4 & 5] 로컬 LLM(qwen3.8:27b)이 팩트/해석 3분할 각주 리포트 합성 중...")

    context_str = ""
    for doc in scraped_documents:
        context_str += f"\n\n[출처 {doc['index']}] {doc['title']}\nURL: {doc['url']}\n본문 내용:\n{doc['content']}\n"

    synthesis_prompt = f"""당신은 자율 리서치 전문 에이전트입니다.
아래 수집된 최신 웹 데이터만을 바탕으로 주제에 대해 정밀한 마크다운 리포트를 작성하세요.

주제: {topic}

참고 데이터:
{context_str}

[작성 지침]
1. 반드시 다음 4개 섹션으로 구성하세요:
   - ## 1. 확인된 사실 (Facts)
     - 검색 결과에 명시적으로 확인된 팩트만 서술하고, 각 문장 끝에 출처 각주 [^1], [^2]를 반드시 매핑하세요.
   - ## 2. 에이전트 해석 (Analysis)
     - 수집된 팩트를 바탕으로 한 시장/기술적 영향과 의미를 분석하세요.
   - ## 3. 미확인 주장 및 향후 검증 과제 (Unverified & Open Questions)
     - 아직 교차 검증되지 않았거나 추가 확인이 필요한 사항을 정리하세요.
   - > [!NOTE] 휴먼 피드백 & 직접 집필란
     - 전문가 검토를 위한 빈 Callout 영역을 남겨두세요.

2. 마크다운 맨 아래에 각주 URL 매핑을 작성하세요:
   [^1]: URL
   [^2]: URL
"""

    report_response = llm.invoke(synthesis_prompt)
    raw_content = report_response.content
    import re
    # Strip <think>...</think> tags if present from reasoning models
    report_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()

    # Frontmatter 조립
    now_iso = datetime.now().isoformat()
    frontmatter = f"""---
topic: "{topic}"
created_at: "{now_iso}"
generator: "Dynamic Live Search (Local Ollama Engine)"
model: "qwen3.8:27b"
search_engine: "duckduckgo"
scraped_sources_count: {len(scraped_documents)}
search_queries:
{json.dumps(queries, ensure_ascii=False, indent=2)}
---

# 📊 {topic} — 심층 리서치 보고서

"""
    final_output = frontmatter + report_content

    # 저장
    output_dir = ROOT_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "local_dls_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    elapsed = time.perf_counter() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 [성공] 로컬 DLS 리포트 생성 완료! (소요 시간: {elapsed:.2f}초)")
    print(f"📁 저장 경로: {report_path}")
    print("=" * 70)

    return report_path

if __name__ == "__main__":
    test_topic = "마이크론 12단 HBM3E 엔비디아 퀄 승인 및 양산 일정"
    run_local_dls(topic=test_topic)
