#!/usr/bin/env python3
"""
News API Connectors for live news ingestion.

Supports:
- NewsAPI.org (NEWS_API_KEY)
- NewsData.io (NEWSDATAIO_API_KEY)
- MediaStack (MEDIASTACK_NEWS_API_KEY)

Usage:
    python3 -c "from news_connector import NewsAPIConnector; c = NewsAPIConnector(); articles = c.fetch('climate change')"
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

FEEDPARSER_AVAILABLE = False
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    pass


class NewsAPIConnector:
    """
    NewsAPI.org connector.
    
    Docs: https://newsapi.org/docs
    Free tier: 100 requests/day, 1 req/sec
    
    Set NEWS_API_KEY in .env or environment.
    """
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NEWS_API_KEY", "")
        if not self.api_key:
            print("[NewsAPI] WARNING: No API key set (NEWS_API_KEY)", file=__import__('sys').stderr)
        self._cache: Dict[str, tuple] = {}
        self._last_request = 0.0
        self.MIN_REQUEST_INTERVAL = 1.0  # Rate limit
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()
    
    def fetch(self, query: str, language: str = "en", page_size: int = 20) -> List[Dict]:
        """Fetch news articles matching query."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = urllib.parse.urlencode({
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": self.api_key
        })
        
        url = f"{self.BASE_URL}/everything?{params}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                articles = data.get("articles", [])
                return [
                    {
                        "title": a.get("title", ""),
                        "link": a.get("url", ""),
                        "source": a.get("source", {}).get("name", "Unknown"),
                        "published": a.get("publishedAt", ""),
                        "description": a.get("description", ""),
                        "content": a.get("content", ""),
                    }
                    for a in articles if a.get("title")
                ]
        except Exception as e:
            print(f"[NewsAPI] Fetch error: {e}", file=__import__('sys').stderr)
            return []
    
    def fetch_top_headlines(self, category: str = "general", country: str = "us") -> List[Dict]:
        """Fetch top headlines by category."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = urllib.parse.urlencode({
            "category": category,
            "country": country,
            "pageSize": 20,
            "apiKey": self.api_key
        })
        
        url = f"{self.BASE_URL}/top-headlines?{params}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                articles = data.get("articles", [])
                return [
                    {
                        "title": a.get("title", ""),
                        "link": a.get("url", ""),
                        "source": a.get("source", {}).get("name", "Unknown"),
                        "published": a.get("publishedAt", ""),
                        "description": a.get("description", ""),
                    }
                    for a in articles if a.get("title")
                ]
        except Exception as e:
            print(f"[NewsAPI] Top headlines error: {e}", file=__import__('sys').stderr)
            return []


class NewsDataIOConnector:
    """
    NewsData.io connector.
    
    Docs: https://newsdata.io/documentation
    Free tier: 200 requests/day
    
    Set NEWSDATAIO_API_KEY in .env or environment.
    """
    
    BASE_URL = "https://newsdata.io/api/1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NEWSDATAIO_API_KEY", "")
        if not self.api_key:
            print("[NewsDataIO] WARNING: No API key set (NEWSDATAIO_API_KEY)", file=__import__('sys').stderr)
        self._last_request = 0.0
        self.MIN_REQUEST_INTERVAL = 1.0
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()
    
    def fetch(self, query: str, language: str = "en", size: int = 20) -> List[Dict]:
        """Fetch news articles matching query."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = urllib.parse.urlencode({
            "apikey": self.api_key,
            "q": query,
            "language": language,
            "size": size,
        })
        
        url = f"{self.BASE_URL}/news?{params}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                return [
                    {
                        "title": r.get("title", ""),
                        "link": r.get("link", ""),
                        "source": r.get("source_id", "Unknown"),
                        "published": r.get("pubDate", ""),
                        "description": r.get("description", ""),
                        "content": r.get("content", ""),
                    }
                    for r in results if r.get("title")
                ]
        except Exception as e:
            print(f"[NewsDataIO] Fetch error: {e}", file=__import__('sys').stderr)
            return []
    
    def fetch_latest(self, category: str = "top") -> List[Dict]:
        """Fetch latest news by category."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = urllib.parse.urlencode({
            "apikey": self.api_key,
            "category": category,
            "language": "en",
        })
        
        url = f"{self.BASE_URL}/latest?{params}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                return [
                    {
                        "title": r.get("title", ""),
                        "link": r.get("link", ""),
                        "source": r.get("source_id", "Unknown"),
                        "published": r.get("pubDate", ""),
                        "description": r.get("description", ""),
                    }
                    for r in results if r.get("title")
                ]
        except Exception as e:
            print(f"[NewsDataIO] Latest error: {e}", file=__import__('sys').stderr)
            return []


class MediaStackConnector:
    """
    MediaStack connector.
    
    Docs: https://mediastack.com/documentation
    Free tier: 500 requests/month, 100/day
    
    Set MEDIASTACK_NEWS_API_KEY in .env or environment.
    """
    
    BASE_URL = "http://api.mediastack.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MEDIASTACK_NEWS_API_KEY", "")
        if not self.api_key:
            print("[MediaStack] WARNING: No API key set (MEDIASTACK_NEWS_API_KEY)", file=__import__('sys').stderr)
        self._last_request = 0.0
        self.MIN_REQUEST_INTERVAL = 1.0
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()
    
    def fetch(self, query: str, language: str = "en", sources: str = "", categories: str = "") -> List[Dict]:
        """Fetch news articles matching query."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = {
            "access_key": self.api_key,
            "keywords": query,
            "languages": language,
            "sort": "published_desc",
            "limit": 100,
        }
        if sources:
            params["sources"] = sources
        if categories:
            params["categories"] = categories
        
        url = f"{self.BASE_URL}/news?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                articles = data.get("data", [])
                return [
                    {
                        "title": a.get("title", ""),
                        "link": a.get("url", ""),
                        "source": a.get("source", "Unknown"),
                        "published": a.get("published_at", ""),
                        "description": a.get("description", ""),
                        "image": a.get("image", ""),
                    }
                    for a in articles if a.get("title")
                ]
        except Exception as e:
            print(f"[MediaStack] Fetch error: {e}", file=__import__('sys').stderr)
            return []
    
    def fetch_latest(self, category: str = "general", country: str = "us") -> List[Dict]:
        """Fetch latest news by category."""
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        params = {
            "access_key": self.api_key,
            "languages": "en",
            "sort": "published_desc",
            "limit": 100,
        }
        if category:
            params["categories"] = category
        
        url = f"{self.BASE_URL}/news?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InverionSemanticBridge/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                articles = data.get("data", [])
                return [
                    {
                        "title": a.get("title", ""),
                        "link": a.get("url", ""),
                        "source": a.get("source", "Unknown"),
                        "published": a.get("published_at", ""),
                        "description": a.get("description", ""),
                    }
                    for a in articles if a.get("title")
                ]
        except Exception as e:
            print(f"[MediaStack] Latest error: {e}", file=__import__('sys').stderr)
            return []


class RSSConnector:
    """RSS/Atom feed connector."""
    
    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_time: Dict[str, float] = {}
        self.CACHE_TTL = 300  # 5 minutes
    
    def fetch(self, feed_url: str, max_items: int = 20) -> List[Dict]:
        """Fetch items from RSS/Atom feed."""
        now = time.time()
        
        if feed_url in self._cache:
            if now - self._cache_time.get(feed_url, 0) < self.CACHE_TTL:
                return self._cache[feed_url]
        
        if not FEEDPARSER_AVAILABLE:
            print("[RSS] WARNING: feedparser not available", file=__import__('sys').stderr)
            return []
        
        try:
            feed = feedparser.parse(feed_url)
            entries = [
                {
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "source": feed.feed.get("title", feed_url),
                    "published": e.get("published", ""),
                    "description": e.get("summary", ""),
                }
                for e in feed.entries[:max_items]
                if e.get("title")
            ]
            self._cache[feed_url] = entries
            self._cache_time[feed_url] = now
            return entries
        except Exception as e:
            print(f"[RSS] Fetch error for {feed_url}: {e}", file=__import__('sys').stderr)
            return []


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("NEWS API CONNECTOR TEST")
    print("=" * 60)
    
    newsapi = NewsAPIConnector()
    newsdata = NewsDataIOConnector()
    mediastack = MediaStackConnector()
    
    print(f"\nNewsAPI key set: {bool(newsapi.api_key)}")
    print(f"NewsDataIO key set: {bool(newsdata.api_key)}")
    print(f"MediaStack key set: {bool(mediastack.api_key)}")
    
    if newsapi.api_key:
        print("\nTesting NewsAPI fetch...")
        articles = newsapi.fetch_top_headlines(category="technology")
        print(f"  Got {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0]['title'][:60]}...")
    
    if newsdata.api_key:
        print("\nTesting NewsDataIO fetch...")
        articles = newsdata.fetch_latest(category="technology")
        print(f"  Got {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0]['title'][:60]}...")
    
    if mediastack.api_key:
        print("\nTesting MediaStack fetch...")
        articles = mediastack.fetch_latest(category="technology")
        print(f"  Got {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0]['title'][:60]}...")