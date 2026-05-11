"""
GDELT Scraper - Real-time headline ingestion for the Sovereignty Engine

Ingests from GDELT (Global Database of Events, Language, and Tone) stream.
Transmits to the Geographic Transformer for coordinate mapping.

Usage:
    python3 -m engine.gdelt_scraper --test
    python3 -m engine.gdelt_scraper --stream
"""

import json
import time
import hashlib
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from typing import List, Optional, Iterator
from datetime import datetime
import threading


GDELT_13_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_RAW_FEED = "https://www.gdeltproject.org/data/sources/LAST14DAYS"


@dataclass
class GDLTEvent:
    """Represents a GDELT event with veracity metadata."""
    id: str
    headline: str
    source_url: str
    source_country: str
    location_raw: str
    location_clean: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: float = 0.0
    veracity_score: float = 1.0
    tone: float = 0.0
    themes: List[str] = None
    
    def __post_init__(self):
        if self.themes is None:
            self.themes = []
        if self.timestamp == 0:
            self.timestamp = time.time()
        if not self.id:
            self.id = hashlib.md5(f"{self.headline}:{self.timestamp}".encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def has_coordinates(self) -> bool:
        return self.lat is not None and self.lon is not None
    
    def sunrise_color(self) -> str:
        """Return sunrise color based on veracity score."""
        if self.veracity_score > 0.8:
            return "#FFFFFF"  # Ignition - High Veracity
        elif self.veracity_score > 0.5:
            return "#FFD54F"  # Stable - Morning Amber
        elif self.veracity_score > 0.2:
            return "#FF8F00"  # Distorted - Deep Amber
        else:
            return "#880E4F"  # Eclipse - Crimson


class GDLTScraper:
    """
    GDELT stream scraper for real-time headline ingestion.
    
    Mode 1: API query mode (structured JSON)
    Mode 2: Raw feed mode (unstructured, needs parsing)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._running = False
        self._last_fetch = 0
        self._lockout_until: Optional[float] = None
        
    def fetch_via_api(
        self, 
        query: str, 
        mode: str = "artimeline",
        format: str = "json",
        max_records: int = 50
    ) -> List[GDLTEvent]:
        """
        Fetch events via GDELT v2 API.
        
        Args:
            query: Search query (e.g., "climate", "election")
            mode: Output mode (artimeline, timelinemini, geo, artype)
            format: Output format (json, html)
            max_records: Maximum number of records to return
            
        Returns:
            List of GDLTEvent objects
        """
        params = {
            "query": query,
            "mode": mode,
            "format": format,
            "maxrecords": max_records
        }
        
        if self.api_key:
            params["key"] = self.api_key
        
        url = f"{GDELT_13_API}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Inverion-Sovereignty-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                return self._parse_api_response(data)
        except Exception as e:
            print(f"GDELT API error: {e}", file=__import__('sys').stderr)
            return []
    
    def _parse_api_response(self, data: dict) -> List[GDLTEvent]:
        """Parse GDELT API response into GDLTEvent objects."""
        events = []
        
        try:
            articles = data.get("articles", [])
            for article in articles:
                loc_raw = article.get("domain", "")
                
                event = GDLTEvent(
                    id="",
                    headline=article.get("title", ""),
                    source_url=article.get("url", ""),
                    source_country=article.get("domain", "").split(".")[-1] if "." in article.get("domain", "") else "",
                    location_raw=loc_raw,
                    location_clean=self._extract_location_from_domain(loc_raw),
                    timestamp=article.get("seendate", 0),
                    veracity_score=1.0,  # Default - will be analyzed by VeracityAuditor
                    tone=article.get("tone", {}).get("tone", 0) if isinstance(article.get("tone"), dict) else 0,
                    themes=[]
                )
                events.append(event)
        except Exception as e:
            print(f"Parse error: {e}", file=__import__('sys').stderr)
            
        return events
    
    def _extract_location_from_domain(self, domain: str) -> str:
        """Extract location hint from source domain."""
        location_hints = {
            "us": "United States",
            "uk": "United Kingdom",
            "fr": "France",
            "de": "Germany",
            "au": "Australia",
            "ca": "Canada",
            "in": "India",
            "br": "Brazil",
            "mx": "Mexico",
            "jp": "Japan",
            "cn": "China",
            "ru": "Russia",
        }
        
        domain_lower = domain.lower()
        for code, country in location_hints.items():
            if code in domain_lower:
                return country
                
        return "Global"
    
    def stream(self, query: str, interval: int = 900) -> Iterator[GDLTEvent]:
        """
        Stream GDELT events continuously.
        
        Args:
            query: Search query
            interval: Fetch interval in seconds (default 15 min)
            
        Yields:
            GDLTEvent objects as they arrive
        """
        self._running = True
        
        while self._running:
            try:
                events = self.fetch_via_api(query)
                for event in events:
                    yield event
                    
                self._last_fetch = time.time()
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self._running = False
                break
            except Exception as e:
                print(f"Stream error: {e}", file=__import__('sys').stderr)
                time.sleep(60)  # Retry after 1 minute
    
    def stop(self):
        """Stop the streaming loop."""
        self._running = False


class GDELTAnalyzer:
    """
    Analyzes GDELT events for veracity scoring.
    
    Wraps the SemanticScrubber from server.py for pattern-based
    fallacy detection in headlines.
    """
    
    def __init__(self):
        self._temporal_index = 0
        
    def analyze_event(self, event: GDLTEvent) -> GDLTEvent:
        """
        Analyze a GDELT event for logical fallacies.
        
        Updates the veracity_score based on detected patterns.
        """
        from server import SemanticScrubber
        
        scrubber = SemanticScrubber()
        fallacies = scrubber.analyze(event.headline)
        
        if fallacies:
            # Calculate veracity decay
            total_cost = sum(f.magnitude * f.persistence for f in fallacies)
            event.veracity_score = max(0.0, event.veracity_score - total_cost)
            
        # Update location string for geocoding
        event.location_clean = self._geocode_hint(event)
        
        return event
    
    def _geocode_hint(self, event: GDLTEvent) -> str:
        """Generate geocoding hint from event metadata."""
        # Use source country as fallback
        if event.location_raw:
            return event.location_raw.split(".")[0].title()
        elif event.source_country:
            return event.source_country.upper()
        return "Global"


def main():
    """Test the GDELT scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GDELT Sovereignty Scraper")
    parser.add_argument("--query", "-q", default="climate change", help="Search query")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--stream", action="store_true", help="Stream mode")
    args = parser.parse_args()
    
    scraper = GDLTScraper()
    analyzer = GDELTAnalyzer()
    
    if args.test or not args.stream:
        # Single fetch test
        print(f"Fetching GDELT events for: {args.query}")
        events = scraper.fetch_via_api(args.query)
        
        print(f"\nReceived {len(events)} events:\n")
        for event in events[:5]:
            analyzed = analyzer.analyze_event(event)
            print(f"Headline: {analyzed.headline[:80]}...")
            print(f"  Location: {analyzed.location_clean}")
            print(f"  Veracity: {analyzed.veracity_score:.2f} ({analyzed.sunrise_color()})")
            print()
    else:
        # Stream mode
        print(f"Streaming GDELT events for: {args.query}")
        print("Press Ctrl+C to exit\n")
        
        for event in scraper.stream(args.query):
            analyzed = analyzer.analyze_event(event)
            print(f"[{datetime.now().isoformat()}] {analyzed.headline[:60]}...")
            print(f"  → Veracity: {analyzed.veracity_score:.2f} | Color: {analyzed.sunrise_color()}")


if __name__ == "__main__":
    main()