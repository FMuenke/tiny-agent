"""Web search tool for clawlite."""

import re
import time
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup


def web_search_tool(
    query: str,
    num_results: int = 5,
    recency_days: int = 30,
    extract: str = "snippets",
    max_chars_per_result: int = 3000,
) -> dict[str, Any]:
    """Search the web using DuckDuckGo.
    
    Args:
        query: Search query
        num_results: Number of results to return
        recency_days: Recency filter (not implemented in HTML scraping)
        extract: Extraction mode (snippets|readable_text)
        max_chars_per_result: Maximum characters per result
        
    Returns:
        Search results with snippets
    """
    # Rate limiting - ensure at least 3 seconds between searches
    time.sleep(3)
    
    try:
        results = _duckduckgo_search(query, num_results)
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {e}",
            "results": [],
        }
    
    # Process results
    processed = []
    for result in results[:num_results]:
        processed_result = {
            "title": result.get("title", "No title"),
            "url": result.get("url", ""),
            "snippet": result.get("snippet", ""),
        }
        
        if extract == "readable_text" and result.get("url"):
            try:
                text = _fetch_readable_text(result["url"], max_chars_per_result)
                processed_result["extracted_text"] = text
            except Exception as e:
                processed_result["extracted_text"] = f"[Extraction failed: {e}]"
                processed_result["limitations"] = "Content extraction failed"
        
        processed.append(processed_result)
    
    return {
        "success": True,
        "query": query,
        "num_results": len(processed),
        "results": processed,
    }


def _duckduckgo_search(query: str, num_results: int) -> list[dict]:
    """Search DuckDuckGo HTML."""
    encoded_query = quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # DuckDuckGo HTML results
        for result in soup.find_all("div", class_="result")[:num_results]:
            title_elem = result.find("a", class_="result__a")
            snippet_elem = result.find("a", class_="result__snippet")
            url_elem = result.find("a", class_="result__url")
            
            if title_elem and snippet_elem:
                result_url = url_elem.get_text(strip=True) if url_elem else ""
                if not result_url and title_elem.get("href"):
                    # Extract URL from href
                    href = title_elem.get("href", "")
                    # DuckDuckGo redirects: /l/?...uddg=
                    if "uddg=" in href:
                        import urllib.parse
                        result_url = urllib.parse.unquote(
                            href.split("uddg=")[-1]
                        )
                    else:
                        result_url = href
                
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "snippet": snippet_elem.get_text(strip=True),
                    "url": result_url,
                })
        
        return results


def _fetch_readable_text(url: str, max_chars: int) -> str:
    """Fetch and extract readable text from URL."""
    try:
        from readability import Document
    except ImportError:
        raise ImportError("readability-lxml required. Install with: pip install readability-lxml")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        
        # Use readability-lxml
        doc = Document(response.text)
        summary = doc.summary()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        return text[:max_chars]
