from typing import List, Dict, Any
from urllib.parse import urlparse

def normalize_url(url: str) -> str:
    """Normalize URL by stripping trailing slashes, fragments, and tracking query params."""
    if not url:
        return ""
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"

def deduplicate_results(results: List[Dict[str, Any]], key: str = "url") -> List[Dict[str, Any]]:
    """Deduplicate list of dictionaries based on normalized URL or key."""
    seen = set()
    deduped = []
    for item in results:
        val = item.get(key, "")
        if key == "url":
            val = normalize_url(val)
        if val and val not in seen:
            seen.add(val)
            deduped.append(item)
    return deduped
