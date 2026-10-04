import os
import re
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
import requests
import trafilatura
from src.utils.config import get_config

class ScrapedDocument(BaseModel):
    url: str
    title: str = ""
    content: str = ""
    method: str = "unknown"
    success: bool = False
    error: Optional[str] = None

def clean_markdown_content(text: str, max_length: int = 5000) -> str:
    """Clean up markdown: remove redundant whitespaces, images, navigation boilerplate."""
    if not text:
        return ""
    # Remove image markdown ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove link formatting but keep anchor text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove repeated blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Trim to max length
    return text.strip()[:max_length]

class ScraperProvider(ABC):
    @abstractmethod
    def scrape(self, url: str) -> ScrapedDocument:
        """Scrape webpage content."""
        pass

class TrafilaturaScraperProvider(ScraperProvider):
    """Local scraper using trafilatura library (100% free, fast, no external network deps)."""
    def __init__(self, timeout: int = 15, max_len: int = 5000):
        self.timeout = timeout
        self.max_len = max_len

    def scrape(self, url: str) -> ScrapedDocument:
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return ScrapedDocument(url=url, success=False, error="Failed to fetch page HTML", method="trafilatura")

            # Extract main content in markdown format
            text = trafilatura.extract(
                downloaded, 
                output_format="markdown", 
                include_links=False, 
                include_images=False,
                favor_precision=True
            )
            if not text or len(text.strip()) < 50:
                return ScrapedDocument(url=url, success=False, error="Extracted content too short or empty", method="trafilatura")

            cleaned = clean_markdown_content(text, max_length=self.max_len)
            metadata = trafilatura.extract_metadata(downloaded)
            title = metadata.title if metadata and metadata.title else ""

            return ScrapedDocument(
                url=url,
                title=title,
                content=cleaned,
                method="trafilatura",
                success=True
            )
        except Exception as e:
            return ScrapedDocument(url=url, success=False, error=str(e), method="trafilatura")

class JinaScraperProvider(ScraperProvider):
    """Scraper using r.jina.ai markdown conversion service."""
    def __init__(self, api_key: Optional[str] = None, timeout: int = 15, max_len: int = 5000):
        self.api_key = api_key or os.getenv("JINA_API_KEY", "")
        self.timeout = timeout
        self.max_len = max_len

    def scrape(self, url: str) -> ScrapedDocument:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "Accept": "text/markdown",
            "User-Agent": "DynamicResearchAgent/1.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.get(jina_url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200 and len(resp.text.strip()) > 50:
                cleaned = clean_markdown_content(resp.text, max_length=self.max_len)
                return ScrapedDocument(
                    url=url,
                    title="",
                    content=cleaned,
                    method="jina",
                    success=True
                )
            return ScrapedDocument(
                url=url,
                success=False,
                error=f"Jina HTTP {resp.status_code}",
                method="jina"
            )
        except Exception as e:
            return ScrapedDocument(url=url, success=False, error=str(e), method="jina")

class MultiTierScraper(ScraperProvider):
    """Multi-tier scraper: Trafilatura -> Jina fallback."""
    def __init__(self, primary: str = "trafilatura", max_len: int = 5000):
        self.trafilatura_scraper = TrafilaturaScraperProvider(max_len=max_len)
        self.jina_scraper = JinaScraperProvider(max_len=max_len)
        self.primary = primary

    def scrape(self, url: str) -> ScrapedDocument:
        first_scraper = self.trafilatura_scraper if self.primary == "trafilatura" else self.jina_scraper
        second_scraper = self.jina_scraper if self.primary == "trafilatura" else self.trafilatura_scraper

        doc = first_scraper.scrape(url)
        if doc.success:
            return doc

        # Fallback to secondary scraper
        fallback_doc = second_scraper.scrape(url)
        if fallback_doc.success:
            return fallback_doc

        return doc

def get_scraper_provider(name: Optional[str] = None) -> ScraperProvider:
    """Factory to get configured scraper provider."""
    cfg = get_config().get("scraper", {})
    provider_name = (name or cfg.get("default_provider", "trafilatura")).lower()
    max_len = cfg.get("max_length_chars", 5000)

    if provider_name == "trafilatura":
        return TrafilaturaScraperProvider(max_len=max_len)
    elif provider_name == "jina":
        return JinaScraperProvider(max_len=max_len)
    else:
        return MultiTierScraper(primary="trafilatura", max_len=max_len)
