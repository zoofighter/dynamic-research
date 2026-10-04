import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.providers.search import get_search_provider
from src.providers.scraper import get_scraper_provider
from src.providers.llm import get_chat_model
from src.utils.dedup import deduplicate_results
from src.utils.config import get_config
from scripts.run_local_dls import run_dls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DailyScheduler")

def fetch_trending_keywords(keywords="반도체 OR AI OR HBM"):
    """Google News RSS에서 최신 헤드라인 상위 목록 추출"""
    try:
        from src.providers.rss import NewsRSSProvider
        rss_provider = NewsRSSProvider()
        articles = rss_provider.fetch_headlines(keywords, limit=15)
        return [f"[{a.source}] {a.title}" for a in articles]
    except Exception as e:
        logger.error(f"RSS 스캔 실패: {e}")
        return []

def select_daily_hot_topic(headlines, provider="opencode", model=None):
    """LLM을 통해 수집된 헤드라인 중 오늘 가장 중요한 심층 리서치 토픽 1건 선정"""
    if not headlines:
        return "엔비디아 차세대 AI 가속기 및 HBM 공급망 최신 동향"

    llm = get_chat_model(provider=provider, model=model)
    headlines_text = "\n".join(f"- {h}" for h in headlines[:10])

    prompt = f"""당신은 산업 분석 에디터입니다.
아래 오늘자 최신 뉴스 헤드라인 목록을 분석하여, 가장 산업적 파급력이 크고 심층 리서치가 시급한 '핵심 리서치 주제 1개'를 명확한 단일 문장으로 요약하여 출력하세요.
주의: 설명이나 서론 없이 오직 최종 주제 문장만 한 줄로 출력하세요.

[오늘의 헤드라인]
{headlines_text}
"""
    res = llm.invoke(prompt)
    raw = res.content if isinstance(res.content, str) else str(res.content)
    import re
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    topic_candidate = cleaned.split("\n")[0].strip().strip('"').strip("'")
    return topic_candidate or headlines[0]

def execute_daily_cycle(provider="opencode", model=None, max_pages=3, output_dir="output/daily_reports"):
    """1회 데일리 브리핑 리서치 사이클 실행"""
    logger.info("=" * 65)
    logger.info("⏰ [데일리 자동 리서치 스케줄러 사이클 시작]")
    logger.info(f"   • 기본 LLM: {provider} ({model or 'default'}) [비용: 0원]")
    logger.info("=" * 65)

    os.makedirs(output_dir, exist_ok=True)

    # 1. 트렌드 감지
    logger.info("1️⃣ 최신 뉴스 RSS 스캔 중...")
    headlines = fetch_trending_keywords()
    logger.info(f"   헤드라인 {len(headlines)}건 감지 완료")

    # 2. 핵심 토픽 자동 선정
    logger.info("2️⃣ AI 에디터가 오늘자 최우선 리서치 토픽 선정 중...")
    chosen_topic = select_daily_hot_topic(headlines, provider=provider, model=model)
    logger.info(f"   🎯 오늘의 브리핑 토픽: '{chosen_topic}'")

    # 3. DLS 심층 리서치 파이프라인 가동
    logger.info("3️⃣ DLS 자율 심층 리서치 가동 (이중 뉴스 수집 + 본문 추출 + 인용 리포트 합성)...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = "".join(c for c in chosen_topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")[:35]
    report_filename = f"daily_report_{clean_title}_{timestamp}.md"
    target_report_path = os.path.join(output_dir, report_filename)

    run_dls(
        topic=chosen_topic,
        max_pages=max_pages,
        provider=provider,
        model=model
    )

    # 가장 최근에 output/ 에 생성된 리포트를 output/daily_reports/ 로 복사/연동
    generated_reports = sorted(Path("output").glob("report_*.md"), key=os.path.getmtime, reverse=True)
    if generated_reports:
        latest = generated_reports[0]
        content = latest.read_text(encoding="utf-8")
        with open(target_report_path, "w", encoding="utf-8") as f:
            f.write(f"# 📅 [데일리 자동 브리핑] {chosen_topic}\n\n" + content)
        logger.info(f"✅ 데일리 리포트 아카이빙 완료: {target_report_path}")

    # 히스토리 기록
    history_file = os.path.join(output_dir, "scheduler_history.json")
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": chosen_topic,
        "report_file": target_report_path,
        "headlines_scanned": len(headlines)
    })

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    logger.info("🎉 오늘의 데일리 리서치 사이클 성공 완료!")

def start_scheduler_daemon(interval_hours=24, provider="opencode", model=None, max_pages=3):
    """지정된 주기(기본 24시간)마다 무한 반복 실행하는 데몬"""
    logger.info(f"🔄 데일리 리서치 데몬 시작 (실행 주기: {interval_hours}시간)")
    while True:
        try:
            execute_daily_cycle(provider=provider, model=model, max_pages=max_pages)
        except Exception as e:
            logger.error(f"사이클 실행 중 에러 발생: {e}", exc_info=True)

        logger.info(f"💤 다음 사이클까지 대기 중... ({interval_hours}시간 후 재실행)")
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Automated Research Scheduler")
    parser.add_argument("--run-once", action="store_true", help="단 1회만 즉시 실행하고 종료")
    parser.add_argument("--interval-hours", type=float, default=24.0, help="데몬 실행 주기(시간 단위, 기본 24.0)")
    parser.add_argument("--provider", type=str, default="opencode")
    parser.add_argument("--model", type=str, default="opencode/muse-spark-1.3-contributor-free")
    parser.add_argument("--max_pages", type=int, default=3)
    args = parser.parse_args()

    if args.run_once:
        execute_daily_cycle(provider=args.provider, model=args.model, max_pages=args.max_pages)
    else:
        start_scheduler_daemon(
            interval_hours=args.interval_hours,
            provider=args.provider,
            model=args.model,
            max_pages=args.max_pages
        )
