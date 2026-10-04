from typing import List, Optional
from pydantic import BaseModel
import feedparser
from src.utils.config import get_config

class NewsArticle(BaseModel):
    title: str
    link: str
    summary: str = ""
    published: str = ""
    source: str = "Google News"

class NewsRSSProvider:
    """
    Fetches real-time headlines from Google News RSS.
    (Note: Hankyung direct feed is reserved as a TODO for later.)
    """
    GOOGLE_NEWS_KR = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"

    def __init__(self, default_limit: int = 30):
        self.default_limit = default_limit

    def fetch_headlines(self, query: Optional[str] = None, limit: Optional[int] = None) -> List[NewsArticle]:
        """Fetch real-time news headlines from Google News RSS."""
        target_limit = limit or self.default_limit

        if query:
            url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        else:
            url = self.GOOGLE_NEWS_KR

        articles: List[NewsArticle] = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:target_limit]:
                # Extract clean source name if present (e.g., '기사제목 - 언론사')
                raw_title = entry.get("title", "").strip()
                source_name = "Google News"
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()
                else:
                    title = raw_title

                articles.append(NewsArticle(
                    title=title,
                    link=entry.get("link", "").strip(),
                    summary=entry.get("summary", "").strip(),
                    published=entry.get("published", "").strip(),
                    source=source_name
                ))
        except Exception as e:
            print(f"[NewsRSSProvider Error] Failed to fetch Google News RSS: {e}")

        return articles
