import os
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
import requests
from duckduckgo_search import DDGS
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

class DuckDuckGoProvider(SearchProvider):
    def __init__(self, region: str = "kr-kr"):
        self.region = region

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            with DDGS() as ddgs:
                ddg_res = list(ddgs.text(query, region=self.region, max_results=max_results))
                for item in ddg_res:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("href", ""),
                        snippet=item.get("body", ""),
                        source="web",
                        engine="duckduckgo"
                    ))
        except Exception as e:
            # Fallback without region if region search fails
            try:
                with DDGS() as ddgs:
                    ddg_res = list(ddgs.text(query, max_results=max_results))
                    for item in ddg_res:
                        results.append(SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                            source="web",
                            engine="duckduckgo"
                        ))
            except Exception as e_fallback:
                print(f"[DuckDuckGoProvider Error] {e_fallback}")
        return results

class SerperProvider(SearchProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            return []
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": max_results, "gl": "kr", "hl": "ko"}
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
