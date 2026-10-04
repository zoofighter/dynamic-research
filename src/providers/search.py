import os
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
import requests
from ddgs import DDGS
from src.utils.config import get_config

class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = "web"
    engine: str = "duckduckgo"

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform search and return list of SearchResult."""
        pass

def sanitize_query(query: str) -> str:
    """Strip complex boolean syntax, quotes, and parenthetical groups for search engine stability."""
    q = re.sub(r'[\(\)\[\]\"\'\{\}]', ' ', query)
    q = re.sub(r'\b(OR|AND|NOT)\b', ' ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q

from concurrent.futures import ThreadPoolExecutor
import feedparser
import urllib.parse

class DuckDuckGoProvider(SearchProvider):
    """
    뉴스 전용 듀얼 수집기:
    덕덕고 뉴스(ddgs.news)와 구글 뉴스 RSS(Google News RSS)를 동시(병렬) 조회하여
    최신 언론사 1차 보도 기사를 극대화 수집하고, 부족 시 일반 웹 검색(ddgs.text)으로 보완합니다.
    """
    def __init__(self, region: str = "kr-kr"):
        self.region = region

    def _fetch_ddg_news(self, clean_q: str, max_results: int) -> List[SearchResult]:
        items: List[SearchResult] = []
        try:
            with DDGS() as ddgs:
                ddg_news = list(ddgs.news(clean_q, region=self.region, max_results=max_results))
                for item in ddg_news:
                    url = item.get("url", "")
                    if url:
                        source_label = item.get("source", "뉴스")
                        date_str = item.get("date", "")[:10]
                        items.append(SearchResult(
                            title=f"[{source_label}] {item.get('title', '')}",
                            url=url,
                            snippet=f"발행일: {date_str} | {item.get('body', '')}",
                            source="news",
                            engine="duckduckgo_news"
                        ))
        except Exception:
            pass
        return items

    def _fetch_google_rss(self, clean_q: str, max_results: int) -> List[SearchResult]:
        items: List[SearchResult] = []
        try:
            encoded_query = urllib.parse.quote_plus(clean_q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:max_results]:
                raw_title = entry.get("title", "").strip()
                source_name = "Google News"
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()
                else:
                    title = raw_title

                items.append(SearchResult(
                    title=f"[{source_name}] {title}",
                    url=entry.get("link", "").strip(),
                    snippet=f"언론사: {source_name} | {entry.get('summary', '')}",
                    source="news",
                    engine="google_news_rss"
                ))
        except Exception:
            pass
        return items

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        seen_urls = set()
        clean_q = sanitize_query(query)

        # 1. 듀얼 뉴스 병렬 수집: 덕덕고 뉴스 + 구글 뉴스 RSS 동시 조회
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_ddg = executor.submit(self._fetch_ddg_news, clean_q, max_results)
            fut_google = executor.submit(self._fetch_google_rss, clean_q, max_results)
            ddg_news_list = fut_ddg.result()
            google_news_list = fut_google.result()

        # 번갈아가며(Interleaved) 우선 병합하여 출처 다양성 확보
        combined_news = []
        for i in range(max(len(ddg_news_list), len(google_news_list))):
            if i < len(ddg_news_list):
                combined_news.append(ddg_news_list[i])
            if i < len(google_news_list):
                combined_news.append(google_news_list[i])

        for item in combined_news:
            if item.url and item.url not in seen_urls:
                seen_urls.add(item.url)
                results.append(item)

        # 2. 뉴스 결과 부족 시 일반 웹 텍스트 검색(ddgs.text) 보완
        if len(results) < max_results:
            needed = max_results - len(results)
            try:
                with DDGS() as ddgs:
                    ddg_res = list(ddgs.text(clean_q, max_results=needed + 5))
                    for item in ddg_res:
                        url = item.get("href", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append(SearchResult(
                                title=item.get("title", ""),
                                url=url,
                                snippet=item.get("body", ""),
                                source="web",
                                engine="duckduckgo_web"
                            ))
            except Exception as e:
                print(f"[DuckDuckGoProvider Error] {e}")

        return results[:max_results]

class SerperProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        if not self.api_key:
            return []
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"q": sanitize_query(query), "num": max_results, "gl": "kr", "hl": "ko"}
        results: List[SearchResult] = []
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("organic", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="web",
                        engine="serper"
                    ))
        except Exception as e:
            print(f"[SerperProvider Error] {e}")
        return results

def get_search_provider(name: Optional[str] = None) -> SearchProvider:
    """Factory to get the appropriate search provider."""
    cfg = get_config().get("search", {})
    provider_name = (name or cfg.get("default_provider", "duckduckgo")).lower()

    if provider_name == "serper":
        serper_key = os.getenv("SERPER_API_KEY")
        if serper_key:
            return SerperProvider(api_key=serper_key)
        print("[get_search_provider] SERPER_API_KEY not found. Falling back to DuckDuckGo.")

    return DuckDuckGoProvider(region=cfg.get("region", "kr-kr"))
