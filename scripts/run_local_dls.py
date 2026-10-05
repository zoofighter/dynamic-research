import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.providers.search import get_search_provider
from src.providers.scraper import get_scraper_provider
from src.providers.llm import get_chat_model
from src.utils.dedup import deduplicate_results
from src.utils.config import get_config

def run_dls(
    topic: str = "마이크론 12단 HBM3E 엔비디아 퀄 승인 및 양산 일정",
    max_pages: int = 5,
    provider: str = None,
    model: str = None,
    outline_path: str = None
):
    outline_data = None
    if outline_path and os.path.exists(outline_path):
        try:
            with open(outline_path, "r", encoding="utf-8") as fp:
                outline_data = json.load(fp)
                if outline_data.get("topic"):
                    topic = outline_data["topic"]
                print(f"📑 [아웃라인 연동 완료] 승인된 목차 파일 로드: {outline_path}")
        except Exception as e:
            print(f"⚠️ 아웃라인 로드 실패: {e}")

    cfg = get_config().get("llm", {})
    active_provider = (provider or cfg.get("default_provider", "gemini")).lower()
    
    if active_provider in ["opencode", "opencode_api", "muse"]:
        model_name = model or cfg.get("opencode", {}).get("default_model", "opencode/muse-spark-1.3-contributor-free")
        engine_label = f"OpenCode Muse Spark ({model_name})"
    elif active_provider == "gemini":
        model_name = model or cfg.get("tiers", {}).get("standard", {}).get("model", "gemini-3.5-flash")
        engine_label = f"Google Gemini ({model_name})"
    elif active_provider == "ollama":
        model_name = model or cfg.get("ollama", {}).get("default_model", "qwen3.8:27b")
        engine_label = f"Local Ollama ({model_name})"
    else:
        model_name = model or "default"
        engine_label = f"{active_provider} ({model_name})"

    print("=" * 70)
    print(f"🚀 [DLS 심층 뉴스 리서치 시작] '{topic}'")
    print(f"   • LLM 엔진: {engine_label}")
    print(f"   • 뉴스 검색 엔진: DuckDuckGo News + Web (최대 {max_pages}개 심층 스크랩)")
    print("   • 크롤러: Trafilatura (로컬 본문 마크다운 추출)")
    print("=" * 70)

    start_time = time.perf_counter()
    llm = get_chat_model(tier="standard", provider=active_provider, model=model_name)
    search_provider = get_search_provider("duckduckgo")
    scraper_provider = get_scraper_provider("trafilatura")

    # ----------------------------------------------------
    # Step 1: 뉴스 중심 검색 쿼리 분해 (Query Decomposition)
    # ----------------------------------------------------
    print(f"\n🔍 [Step 1] {engine_label}이 최신 뉴스 검색 쿼리를 분해하는 중...")
    outline_context = ""
    if outline_data and outline_data.get("sections"):
        outline_context = "\n[사전 승인된 목차 및 질문]\n"
        for s in outline_data["sections"]:
            outline_context += f"• {s.get('title')}: {', '.join(s.get('target_questions', []))}\n"

    decomp_prompt = f"""당신은 심층 리서치 에이전트입니다.
다음 주제와 세부 목차에 대해 국내외 최신 언론사 보도, 공시, IR 뉴스를 빠짐없이 수집하기 위한 핵심 검색 키워드 3~4개를 한 줄에 하나씩 출력하세요.
중요: 따옴표("), 괄호(), OR, AND 같은 특수 기호를 절대 쓰지 말고 오직 자연어 키워드만 공백으로 구분하여 출력하세요.

주제: {topic}
{outline_context}
"""
    decomp_res = llm.invoke(decomp_prompt)
    raw_decomp = decomp_res.content if isinstance(decomp_res.content, str) else str(decomp_res.content)
    queries = [q.strip().strip("-").strip("1234567890.").strip() for q in raw_decomp.strip().split("\n") if q.strip()][:3]
    if not queries:
        queries = [topic, f"{topic} 뉴스", f"{topic} 최신 기사"]

    print("   생성된 검색 쿼리:")
    for i, q in enumerate(queries, 1):
        print(f"   [{i}] {q}")

    # ----------------------------------------------------
    # Step 2: 실시간 뉴스 및 웹 검색 (Live News Search)
    # ----------------------------------------------------
    print(f"\n🌐 [Step 2] DuckDuckGo 뉴스 & 웹 검색 수행 중 (쿼리당 8건)...")
    all_search_results = []
    for q in queries:
        res = search_provider.search(q, max_results=8)
        for r in res:
            all_search_results.append({
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "query": q
            })

    # 중복 URL 제거 및 상위 max_pages 개 선별
    deduped_results = deduplicate_results(all_search_results, key="url")[:max_pages]
    print(f"   총 {len(all_search_results)}개 결과 중 고유 1차 출처 {len(deduped_results)}개 선별:")
    for i, r in enumerate(deduped_results, 1):
        print(f"   [{i}] {r['title'][:50]}... ({r['url'][:55]})")

    # ----------------------------------------------------
    # Step 3: 웹 원문 직접 방문 및 텍스트 파싱 (Deep Scraping)
    # ----------------------------------------------------
    print(f"\n📄 [Step 3] {len(deduped_results)}개 뉴스 원문 직접 방문 및 마크다운 본문 추출 중...")
    scraped_documents = []
    for i, item in enumerate(deduped_results, 1):
        print(f"   [{i}/{len(deduped_results)}] 스크랩 중: {item['url'][:60]}...")
        doc = scraper_provider.scrape(item["url"])
        if doc.success and doc.content and len(doc.content.strip()) > 100:
            scraped_documents.append({
                "index": len(scraped_documents) + 1,
                "url": item["url"],
                "title": doc.title or item["title"],
                "content": doc.content[:2500]
            })
            print(f"       ✅ 성공 ({len(doc.content[:2500])}자 본문 확보)")
        else:
            if item.get("snippet"):
                scraped_documents.append({
                    "index": len(scraped_documents) + 1,
                    "url": item["url"],
                    "title": item["title"],
                    "content": item["snippet"]
                })
                print("       ⚠️ 본문 접근 제한 -> 검색 스니펫으로 대체")

    if not scraped_documents:
        print("❌ 유효한 웹 데이터를 확보하지 못했습니다.")
        return

    # ----------------------------------------------------
    # Step 4 & 5: LLM 고밀도 리포트 합성 (Synthesis with Citations)
    # ----------------------------------------------------
    print(f"\n✍️  [Step 4 & 5] {engine_label}이 {len(scraped_documents)}개 출처를 교차 분석하여 심층 리포트 합성 중...")

    context_str = ""
    for doc in scraped_documents:
        context_str += f"\n\n[출처 {doc['index']}: {doc['title']}]\nURL: {doc['url']}\n기사 본문:\n{doc['content']}\n"

    if outline_data and outline_data.get("sections"):
        theme = outline_data.get("theme", "심층 분석")
        sec_directives = []
        for i, s in enumerate(outline_data["sections"], 1):
            q_str = "\n".join([f"       * {q}" for q in s.get("target_questions", [])])
            sec_directives.append(
                f"""   - ## {i}. {s.get('title')}
     - 다루어야 할 핵심 질문:
{q_str}
     - 작성 요령: 위 수집된 원문 데이터에 근거하여 핵심 팩트(수치, 일정, 사양)와 심층 분석을 2~3개 문단 및 불릿으로 밀도 있게 서술하고 모든 문장에 출처 번호 [^번호]를 명시하세요."""
            )
        sections_instruction = "\n".join(sec_directives)
        unverified_sec_num = len(outline_data["sections"]) + 1

        structure_instruction = f"""3. [사전 승인된 아웃라인(테마: {theme}) 기반 섹션 구성 - 반드시 아래 대제목(##) 순서와 제목 그대로 작성할 것]
{sections_instruction}
   - ## {unverified_sec_num}. 미확인 주장 및 향후 검증 과제 (Unverified & Open Questions)
     - 기사 간 상충/과장 내용 및 향후 공식 확인 필요 사항을 마크다운 비교 표로 정리
   - > [!NOTE] 휴먼 피드백 & 직접 집필란
     - 전문가 검토를 위한 빈 Callout 영역"""
    else:
        structure_instruction = """3. 반드시 다음 표준 4개 섹션으로 구성하세요:
   - ## 1. 확인된 사실 (Facts)
     - 4~5개 핵심 팩트 불릿 (각 문장 출처 각주 포함)
   - ## 2. 에이전트 해석 (Analysis)
     - 핵심 영향 및 산업 밸류체인/경쟁 구도 심층 분석 (2~3개 문단)
   - ## 3. 미확인 주장 및 향후 검증 과제 (Unverified & Open Questions)
     - 기사 간 상충/과장 내용 및 향후 공식 IR 확인 필요 사항을 마크다운 표로 정리
   - > [!NOTE] 휴먼 피드백 & 직접 집필란
     - 전문가 검토를 위한 빈 Callout 영역"""

    synthesis_prompt = f"""당신은 '{topic}' 분야 전문 수석 리서치 애널리스트입니다.
아래 수집된 최신 뉴스 및 보도 원문 {len(scraped_documents)}건을 교차 검증하여 전체가 완결된 심층 마크다운 리포트를 작성하세요.

주제: {topic}

수집된 {len(scraped_documents)}개 원문 데이터:
{context_str}

[작성 지침 - 반드시 준수]
1. 완결성 및 분량 균형:
   - 특정 섹션에 과도하게 치중하지 말고, 각 섹션을 핵심 위주로 명료하고 밀도 있게 작성하여 지정된 모든 섹션과 맨 끝 각주 URL 매핑까지 반드시 끝까지 완결하세요.
2. 정량적 수치와 출처 매핑:
   - 기사에 언급된 날짜, 금액, 사양, 성능 수치 등의 숫자를 구체적으로 인용하세요.
   - 모든 문장 끝에 반드시 해당 팩트의 출처 번호 각주 [^1], [^2]를 연결하세요.
{structure_instruction}
4. 맨 아래에 반드시 수집된 출처 URL 매핑을 완결하세요:
   [^1]: URL
   [^2]: URL
"""

    report_response = llm.invoke(synthesis_prompt)
    raw_content = report_response.content if isinstance(report_response.content, str) else str(report_response.content)
    import re
    report_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()

    now_iso = datetime.now().isoformat()
    frontmatter = f"""---
topic: "{topic}"
created_at: "{now_iso}"
generator: "Dynamic Live Search ({engine_label})"
model: "{model_name}"
search_engine: "duckduckgo_news_web"
scraped_sources_count: {len(scraped_documents)}
search_queries:
{json.dumps(queries, ensure_ascii=False, indent=2)}
---

# 📊 {topic} — 심층 리서치 보고서

"""
    final_output = frontmatter + report_content

    output_dir = ROOT_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    if active_provider == "gemini":
        default_filename = "gemini_dls_report.md"
    elif active_provider in ["opencode", "opencode_api", "muse"]:
        default_filename = "opencode_dls_report.md"
    else:
        default_filename = "local_dls_report.md"
    report_path = output_dir / default_filename

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    clean_topic_slug = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_report_path = output_dir / f"report_{clean_topic_slug}_{timestamp}.md"
    with open(timestamped_report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    elapsed = time.perf_counter() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 [성공] DLS 리포트 생성 완료! (소요 시간: {elapsed:.2f}초)")
    print(f"📁 수집 출처 수: {len(scraped_documents)}개")
    print(f"📁 기본 경로: {report_path}")
    print(f"📁 아카이브 경로: {timestamped_report_path}")
    print("=" * 70)

    return str(timestamped_report_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic Live Search Pipeline")
    parser.add_argument("--topic", type=str, default="마이크론 12단 HBM3E 엔비디아 퀄 승인 및 양산 일정")
    parser.add_argument("--provider", type=str, default="opencode", choices=["opencode", "gemini", "ollama", "meta_muse", "meta", "groq", "openai"])
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--max_pages", type=int, default=8)
    parser.add_argument("--outline", type=str, default=None, help="Path to approved outline json")
    args = parser.parse_args()

    default_model = None
    if args.provider == "ollama":
        default_model = "qwen3.8:27b"
    elif args.provider in ["meta_muse", "meta"]:
        default_model = "muse-spark-1.3"
    elif args.provider in ["opencode", "opencode_api", "muse"]:
        default_model = "opencode/muse-spark-1.3-contributor-free"
    elif args.provider == "groq":
        default_model = "llama-3.3-70b-versatile"
    elif args.provider == "gemini":
        default_model = "gemini-3.5-flash"

    chosen_model = args.model or default_model
    run_dls(topic=args.topic, max_pages=args.max_pages, provider=args.provider, model=chosen_model, outline_path=args.outline)
