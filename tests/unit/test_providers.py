import pytest
from src.providers.search import get_search_provider, SearchResult
from src.providers.scraper import get_scraper_provider, ScrapedDocument
from src.providers.rss import NewsRSSProvider, NewsArticle
from src.providers.llm import get_chat_model

def test_search_provider():
    """Verify DuckDuckGo search provider works without API key."""
    provider = get_search_provider("duckduckgo")
    results = provider.search("NVIDIA HBM3E", max_results=3)
    assert isinstance(results, list)
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert len(results[0].url) > 0
    assert len(results[0].title) > 0

def test_scraper_provider():
    """Verify local Trafilatura scraper can extract content."""
    scraper = get_scraper_provider("trafilatura")
    doc = scraper.scrape("https://example.com")
    assert isinstance(doc, ScrapedDocument)
    assert doc.success is True
    assert "Example Domain" in doc.title or "permission" in doc.content

def test_google_news_rss():
    """Verify Google News RSS fetches headlines."""
    rss = NewsRSSProvider(default_limit=5)
    articles = rss.fetch_headlines(limit=5)
    assert isinstance(articles, list)
    assert len(articles) > 0
    assert isinstance(articles[0], NewsArticle)
    assert len(articles[0].title) > 0
    assert len(articles[0].link) > 0

def test_local_ollama_llm():
    """Verify local Ollama chat model generates response."""
    llm = get_chat_model(tier="fast")
    res = llm.invoke("1+1의 결과를 숫자 하나만 말해줘")
    assert res is not None
    assert len(res.content.strip()) > 0
