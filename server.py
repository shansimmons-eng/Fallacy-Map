#!/usr/bin/env python3
"""
Inverion Semantic Bridge — The Sovereign Scrubber

Local-to-Arc Pipeline:
1. Ingests GDELT/RSS publication streams
2. Geocodes location strings via GeoPy
3. Calculates Veracity Scores via SemanticScrubber
4. Pushes Sunrise-encoded markers to WordPress/MapPress

Usage:
    python3 server.py --stream --wp-site https://kylosarc.com --wp-user admin
    python3 server.py --gdelt "climate change"
    python3 server.py --rss https://example.com/feed.xml

The server outputs JSON telemetry to stdout for stitching with the frontend.
"""

import sys
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

FEEDPARSER_AVAILABLE = False

def load_env_file(env_path: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    path = Path(env_path)
    if not path.exists():
        return
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            line = line.lstrip('export ').strip()
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value

# Logic Constants: The Inverion Thresholds
VERACITY_CONSTANT = 1.0
BYPASS_THRESHOLD = 0.5
LOCKOUT_THRESHOLD = 0.1
SHUTDOWN_THRESHOLD = 0.0


class SunriseColor(Enum):
    """Sunrise spectrum colors for map markers."""
    IGNITION = "#FFFFFF"       # Veracity > 0.8 - High Veracity / Objective
    MORNING = "#FFB300"       # Veracity 0.5-0.8 - Morning Amber
    SUNSET = "#FF8F00"         # Veracity 0.3-0.5 - Distorted
    CRIMSON = "#B71C1C"       # Veracity < 0.3 - Structural Collapse


@dataclass
class FallacyTelemetry:
    """Represents a detected fallacy as telemetry for the manifold."""
    type: str
    magnitude: float
    persistence: float
    coord: List[float]  # [x, y, z] spatial position
    depth: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass  
class VeracityState:
    """Current veracity state of the analysis."""
    V_active: float
    V_initial: float
    ticks: int
    bypass_count: int
    inverion_triggered: bool
    root_fallacy_id: Optional[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PublicationMarker:
    """
    A Sunrise-encoded publication marker for MapPress.
    
    Contains all data needed for WordPress/MapPress injection.
    """
    id: str
    title: str
    headline: str
    source_url: str
    source_name: str
    lat: Optional[float]
    lon: Optional[float]
    veracity_score: float
    fallacy_types: List[str]
    published_at: str
    color: str = "#FFFFFF"
    
    def __post_init__(self):
        self.id = hashlib.md5(self.headline.encode()).hexdigest()[:12]
        self.color = self._calculate_color()
    
    def _calculate_color(self) -> str:
        """Calculate Sunrise color based on veracity score."""
        if self.veracity_score > 0.8:
            return SunriseColor.IGNITION.value
        elif self.veracity_score > 0.5:
            return SunriseColor.MORNING.value
        elif self.veracity_score > 0.3:
            return SunriseColor.SUNSET.value
        else:
            return SunriseColor.CRIMSON.value
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_wp_rest_payload(self) -> dict:
        """Convert to WordPress REST API payload for MapPress."""
        return {
            "title": self.headline[:200],
            "content": f"Veracity: {self.veracity_score:.2f}\nFallacies: {', '.join(self.fallacy_types)}\nSource: {self.source_url}",
            "status": "publish",
            "meta": {
                "mappress_veracity_score": self.veracity_score,
                "mappress_color": self.color,
                "mappress_lat": self.lat or 0.0,
                "mappress_lng": self.lon or 0.0,
                "mappress_fallacy_types": ",".join(self.fallacy_types),
                "mappress_source": self.source_name,
            }
        }
    
    def to_manifold_jump(self) -> dict:
        """Data for syncing to 3D manifold when marker is clicked."""
        return {
            "id": self.id,
            "headline": self.headline,
            "veracity_score": self.veracity_score,
            "fallacy_types": self.fallacy_types,
            "position": [self.lon or 0, 0, self.lat or 0] if self.lat else [0, 0, 0],
            "color": self.color
        }


class SemanticScrubber:
    """
    Simulated LLM-Bridge / Regex Scrubber.
    
    In production, this wraps the local analyzer (engine/auditor/semantic_bridge/).
    For now, it provides pattern-based detection for testing.
    """
    
    FALLACY_PATTERNS = [
        {"pattern": r"\b(you|your)\s+(should|must|have to)\b.*\b(believe me|I am right|trust me)\b", 
         "type": "appeal_to_authority", "magnitude": 0.6, "persistence": 0.6},
        {"pattern": r"\b(either|only|just)\s+(we|you|i|they)\s+(do|have|are)\b.*\bor\b", 
         "type": "false_dilemma", "magnitude": 0.8, "persistence": 0.7},
        {"pattern": r"\bif\s+.*\bthen\s+.*\bwill\s+(also|too|as well)\b", 
         "type": "slippery_slope", "magnitude": 0.7, "persistence": 0.6},
        {"pattern": r"\b(obviously|certainly|clearly|everyone knows)\b.*\b(so|therefore|thus)\b", 
         "type": "begging_the_question", "magnitude": 0.7, "persistence": 0.6},
        {"pattern": r"\bdoesn't\s+(actually|really|truly)\b", 
         "type": "strawman", "magnitude": 0.6, "persistence": 0.5},
    ]
    
    def __init__(self):
        self._temporal_index = 0
        
    def analyze(self, raw_input: str) -> List[FallacyTelemetry]:
        """Analyze raw text and return fallacy telemetry."""
        import re
        
        fallacies = []
        input_lower = raw_input.lower()
        
        for fp in self.FALLACY_PATTERNS:
            if re.search(fp["pattern"], input_lower, re.IGNORECASE):
                # Calculate spatial position based on temporal index
                x = self._temporal_index * 2.0  # X = temporal flow
                y = fp["magnitude"] * 2.0       # Y = relationship density  
                z = -fp["magnitude"] * 3.0       # Z = gravity depth (negative = well)
                
                fallacies.append(FallacyTelemetry(
                    type=fp["type"],
                    magnitude=fp["magnitude"],
                    persistence=fp["persistence"],
                    coord=[x, y, z],
                    depth=0
                ))
                
                self._temporal_index += 1
                
        return fallacies
    
    def analyze_headline(self, headline: str) -> tuple[List[FallacyTelemetry], float]:
        """
        Analyze a headline and return fallacies plus veracity score.
        
        Returns (fallacies, veracity_score) where veracity_score is 1.0 minus decay.
        """
        fallacies = self.analyze(headline)
        
        # Calculate veracity decay
        total_cost = sum(f.magnitude * f.persistence for f in fallacies)
        veracity_score = max(0.0, VERACITY_CONSTANT - total_cost)
        
        return fallacies, veracity_score


class GeoTransformer:
    """
    Geographic Transformer for resolving location strings to coordinates.
    
    Uses GeoPy for geocoding with pattern-matching fallback.
    """
    
    US_STATES = {
        "AL": (32.3182, -86.9023), "AK": (61.2181, -149.9003), "AZ": (34.0489, -111.0937),
        "AR": (35.2010, -91.8318), "CA": (36.7783, -119.4179), "CO": (39.5501, -105.7821),
        "CT": (41.6032, -73.0877), "DE": (38.9108, -75.5277), "FL": (27.6648, -81.5158),
        "GA": (32.1574, -81.4250), "HI": (19.8968, -155.5828), "ID": (43.6151, -116.2023),
        "IL": (40.6331, -89.3985), "IN": (40.2672, -86.1349), "IA": (41.8780, -93.0977),
        "KS": (39.0119, -98.4842), "KY": (37.8392, -84.2700), "LA": (30.9843, -91.9623),
        "ME": (44.6938, -69.3819), "MD": (39.0458, -76.6413), "MA": (42.4072, -71.3824),
        "MI": (44.3148, -85.6024), "MN": (46.7296, -94.6859), "MS": (32.3546, -89.3985),
        "MO": (37.9642, -91.8318), "MT": (46.8797, -110.3626), "NE": (41.4925, -99.9018),
        "NV": (38.8026, -116.4194), "NH": (43.1939, -71.5724), "NJ": (40.0583, -74.4057),
        "NM": (34.8403, -106.2485), "NY": (43.2994, -74.2179), "NC": (35.7596, -79.0193),
        "ND": (47.5515, -101.0020), "OH": (40.4173, -82.9071), "OK": (35.0078, -97.0929),
        "OR": (43.8041, -120.5542), "PA": (41.2033, -77.1945), "RI": (41.5801, -71.4774),
        "SC": (33.8361, -81.1637), "SD": (43.9695, -99.9018), "TN": (35.5175, -86.5804),
        "TX": (31.9686, -99.9018), "UT": (39.3200, -111.0937), "VT": (44.5588, -72.5778),
        "VA": (37.4316, -78.6569), "WA": (47.7511, -120.7401), "WV": (38.5972, -80.4549),
        "WI": (43.7844, -88.7879), "WY": (43.0760, -107.2903),
    }
    
    def __init__(self, geopy_enabled: bool = True):
        self.geopy_enabled = geopy_enabled
        self._geocoder = None
        self._init_geopy()
        self._cache: Dict[str, Tuple[float, float]] = {}
    
    def _init_geopy(self) -> bool:
        """Initialize GeoPy geocoder."""
        self.geopy_enabled = False
        return False
    
    def geocode(self, location_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Geocode a location string to (lat, lon).
        
        Returns (None, None) if geocoding fails.
        """
        if not location_str:
            return None, None
        
        location_clean = location_str.strip()
        
        # Check cache first
        if location_clean in self._cache:
            return self._cache[location_clean]
        
        # Try GeoPy if enabled
        if self.geopy_enabled and self._geocoder:
            try:
                location = self._geocoder.geocode(location_clean, timeout=5)
                if location:
                    coords = (location.latitude, location.longitude)
                    self._cache[location_clean] = coords
                    return coords
            except Exception as e:
                print(f"Geocoding error for '{location_clean}': {e}", file=sys.stderr)
        
        # Fall back to pattern matching
        lat, lon = self._pattern_match(location_clean)
        if lat is not None and lon is not None:
            self._cache[location_clean] = (lat, lon)
        
        return lat, lon
    
    def _pattern_match(self, location_str: str) -> tuple[Optional[float], Optional[float]]:
        """Match location using pattern database."""
        loc_lower = location_str.lower()
        
        # Check for US state
        for abbrev, coords in self.US_STATES.items():
            if abbrev.lower() in loc_lower or f" {abbrev.lower()}" in loc_lower:
                return coords
        
        # Check for country names
        countries = {
            "france": (46.2276, 2.2137), "germany": (51.1657, 10.4515),
            "uk": (55.3781, -3.4360), "united kingdom": (55.3781, -3.4360),
            "canada": (56.1304, -106.3468), "australia": (-25.2744, 133.7751),
            "india": (20.5937, 78.9629), "brazil": (-14.2350, -51.9253),
            "china": (35.8617, 104.1954), "japan": (36.2048, 138.2529),
        }
        
        for country, coords in countries.items():
            if country in loc_lower:
                return coords
        
        return None, None


class GDELTConnector:
    """
    GDELT stream connector for real-time headline ingestion.
    """
    
    GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def fetch(self, query: str, max_records: int = 50) -> List[Dict]:
        """Fetch headlines from GDELT."""
        params = {
            "query": query,
            "mode": "artimeline",
            "format": "json",
            "maxrecords": max_records
        }
        
        if self.api_key:
            params["key"] = self.api_key
        
        url = f"{self.GDELT_API}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Inverion-Sovereignty-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                return data.get("articles", [])
        except Exception as e:
            print(f"GDELT fetch error: {e}", file=sys.stderr)
            return []
    
    def fetch_with_geocode(self, query: str, geo_transformer: GeoTransformer) -> List[PublicationMarker]:
        """Fetch GDELT headlines and geocode them."""
        articles = self.fetch(query)
        markers = []
        
        for article in articles:
            headline = article.get("title", "")
            source_url = article.get("url", "")
            source_name = article.get("domain", "")
            location_raw = source_name.split(".")[-1] if "." in source_name else ""
            
            # Analyze veracity
            scrubber = SemanticScrubber()
            fallacies, veracity_score = scrubber.analyze_headline(headline)
            fallacy_types = [f.type for f in fallacies]
            
            # Geocode location
            lat, lon = geo_transformer.geocode(location_raw)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=source_url,
                source_name=source_name,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=article.get("seendate", "")
            )
            markers.append(marker)
        
        return markers


class RSSConnector:
    """
    RSS feed connector for headline ingestion.
    """
    
    def fetch(self, feed_url: str) -> List[Dict]:
        """Fetch headlines from RSS feed using urllib."""
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Inverion-Sovereignty-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8', errors='ignore')
            
            entries = []
            import re
            item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL | re.IGNORECASE)
            title_pattern = re.compile(r'<title>(.*?)</title>', re.DOTALL | re.IGNORECASE)
            link_pattern = re.compile(r'<link>(.*?)</link>', re.DOTALL | re.IGNORECASE)
            
            for item in item_pattern.findall(content):
                title = title_pattern.search(item)
                link = link_pattern.search(item)
                
                entries.append({
                    "title": title.group(1) if title else "",
                    "link": link.group(1) if link else "",
                    "published": "",
                    "source": feed_url
                })
            
            return entries[:50]
        except Exception as e:
            print(f"RSS fetch error: {e}", file=sys.stderr)
            return []
    
    def fetch_with_geocode(self, feed_url: str, geo_transformer: GeoTransformer) -> List[PublicationMarker]:
        """Fetch RSS headlines and geocode them."""
        articles = self.fetch(feed_url)
        markers = []
        
        for article in articles:
            headline = article.get("title", "")
            source_url = article.get("link", "")
            source_name = article.get("source", "")
            
            # Analyze veracity
            scrubber = SemanticScrubber()
            fallacies, veracity_score = scrubber.analyze_headline(headline)
            fallacy_types = [f.type for f in fallacies]
            
            # Extract location from source or title
            location_hint = self._extract_location(article, headline)
            lat, lon = geo_transformer.geocode(location_hint) if location_hint else (None, None)
            
            marker = PublicationMarker(
                id="",
                title=headline[:100],
                headline=headline,
                source_url=source_url,
                source_name=source_name,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                fallacy_types=fallacy_types,
                published_at=article.get("published", "")
            )
            markers.append(marker)
        
        return markers
    
    def _extract_location(self, article: Dict, headline: str) -> str:
        """Extract location hint from article or headline."""
        # Try to find location patterns in title
        import re
        loc_pattern = r'\b([A-Z]{2})\b'
        matches = re.findall(loc_pattern, headline)
        if matches:
            return matches[0]
        return ""


class MapPressBridge:
    """
    MapPress REST API bridge for injecting markers into Map ID 2.
    
    Hardcoded for KylosArc.com Geographic Handshake.
    """
    
    MAP_ID = 2  # Hardcoded target map
    
    SUNRSE_ICON_MAP = {
        "#FFFFFF": 1,  # White-Hot (Ignition) - Veracity > 0.8
        "#FFB300": 2,  # Morning Amber - Veracity 0.4-0.7
        "#880E4F": 3,  # Shadow Crimson - Veracity < 0.3
        "#FF8F00": 4,  # Sunset Orange - Veracity 0.3-0.5
    }
    
    def __init__(self, site_url: str, username: str, password: str = ""):
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.password = password
        self._markers_cache: List[PublicationMarker] = []
        self._archive_dir = "data/archive/shadow"
    
    def _get_auth_header(self) -> str:
        """Get base64 auth header for WordPress."""
        import base64
        auth = f"{self.username}:{self.password}"
        return base64.b64encode(auth.encode()).decode()
    
    def _get_icon_id(self, veracity_score: float) -> int:
        """Map veracity score to Sunrise icon ID."""
        if veracity_score > 0.8:
            return self.SUNRSE_ICON_MAP["#FFFFFF"]
        elif veracity_score > 0.5:
            return self.SUNRSE_ICON_MAP["#FFB300"]
        elif veracity_score > 0.3:
            return self.SUNRSE_ICON_MAP["#FF8F00"]
        else:
            return self.SUNRSE_ICON_MAP["#880E4F"]
    
    def post_marker(self, marker: PublicationMarker) -> Dict:
        """
        Post a single marker to MapPress Map ID 2.
        
        MapPress uses a custom post type 'mappress_marker'.
        """
        url = f"{self.site_url}/wp-json/wp/v2/mappress_marker"
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "mapid": self.MAP_ID,
                    "title": marker.headline[:200],
                    "lat": marker.lat or 0.0,
                    "lng": marker.lon or 0.0,
                    "content": f"Veracity Score: {marker.veracity_score:.2f} | Source: {marker.source_name}",
                    "iconid": self._get_icon_id(marker.veracity_score),
                    "linked_post": 0,
                    "tags": ",".join(marker.fallacy_types) if marker.fallacy_types else ""
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._get_auth_header()}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                print(f"[MapPress] Marker posted: {result.get('id', 'unknown')}", file=sys.stderr)
                return result
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            print(f"MapPress HTTP error {e.code}: {error_body[:200]}", file=sys.stderr)
            
            # Fallback: Try generic WordPress post with custom fields
            return self._post_as_wp_post(marker)
            
        except Exception as e:
            print(f"MapPress POST error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def _post_as_wp_post(self, marker: PublicationMarker) -> Dict:
        """
        Fallback: Post as WordPress post with MapPress metadata.
        
        Used when MapPress REST API is not available.
        """
        url = f"{self.site_url}/wp-json/wp/v2/posts"
        
        custom_meta = {
            "_mappress_veracity_score": str(marker.veracity_score),
            "_mappress_color": marker.color,
            "_mappress_lat": str(marker.lat or 0),
            "_mappress_lng": str(marker.lon or 0),
            "_mappress_fallacy_types": ",".join(marker.fallacy_types),
            "_mappress_source": marker.source_name,
            "_mappress_gdel_hash": marker.id,
        }
        
        payload = {
            "title": marker.headline[:200],
            "content": f"<!-- MapPress --><!-- MapID: {self.MAP_ID} -->\nVeracity: {marker.veracity_score:.2f} | Source: {marker.source_name}",
            "status": "publish",
            "categories": [self.MAP_ID],
            "meta": custom_meta
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._get_auth_header()}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                print(f"[MapPress-Fallback] Post created: {result.get('id', 'unknown')}", file=sys.stderr)
                return result
                
        except Exception as e:
            print(f"MapPress fallback error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def sync_markers(self, markers: List[PublicationMarker]) -> int:
        """Sync multiple markers to MapPress Map ID 2."""
        self._markers_cache = markers
        count = 0
        
        for marker in markers:
            result = self.post_marker(marker)
            if "id" in result or "post_id" in result:
                # Archive to Shadow Ledger
                self._archive_to_shadow(marker, result.get("id", result.get("post_id", "unknown")))
                count += 1
            time.sleep(0.5)  # Rate limit
        
        return count
    
    def _archive_to_shadow(self, marker: PublicationMarker, wp_id: Any) -> str:
        """Archive marker to Shadow Ledger for forensic record."""
        import os
        os.makedirs(self._archive_dir, exist_ok=True)
        
        archive_entry = {
            "gdelt_hash": marker.id,
            "wp_id": wp_id,
            "headline": marker.headline,
            "source_url": marker.source_url,
            "source_name": marker.source_name,
            "lat": marker.lat,
            "lon": marker.lon,
            "veracity_score": marker.veracity_score,
            "fallacy_types": marker.fallacy_types,
            "color": marker.color,
            "icon_id": self._get_icon_id(marker.veracity_score),
            "map_id": self.MAP_ID,
            "archived_at": datetime.now().isoformat()
        }
        
        filename = f"{self._archive_dir}/{marker.id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(archive_entry, f, indent=2)
        
        print(f"[Shadow Archive] {filename}", file=sys.stderr)
        return filename
    
    def export_manifest(self, filepath: str = "data/manifest.json") -> str:
        """Export markers as JSON manifest for frontend MapPress sync."""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "map_id": self.MAP_ID,
            "count": len(self._markers_cache),
            "markers": [m.to_dict() for m in self._markers_cache],
            "manifold_jumps": [m.to_manifold_jump() for m in self._markers_cache]
        }
        
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath


class WordPressBridge:
    """
    WordPress REST API bridge for MapPress marker injection.
    """
    
    def __init__(self, site_url: str, username: str, password: str = ""):
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.password = password
        self._markers_cache: List[PublicationMarker] = []
    
    def post_marker(self, marker: PublicationMarker) -> Dict:
        """Post a single marker to WordPress via REST API."""
        payload = marker.to_wp_rest_payload()
        
        # WordPress REST API endpoint for posts
        url = f"{self.site_url}/wp-json/wp/v2/posts"
        
        auth = f"{self.username}:{self.password}"
        import base64
        auth_header = base64.b64encode(auth.encode()).decode()
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth_header}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"WordPress POST error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def sync_markers(self, markers: List[PublicationMarker]) -> int:
        """Sync multiple markers to WordPress."""
        self._markers_cache = markers
        count = 0
        
        for marker in markers:
            result = self.post_marker(marker)
            if "id" in result:
                count += 1
        
        return count
    
    def export_manifest(self, filepath: str = "data/manifest.json") -> str:
        """Export markers as JSON manifest for frontend MapPress sync."""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "count": len(self._markers_cache),
            "markers": [m.to_dict() for m in self._markers_cache],
            "manifold_jumps": [m.to_manifold_jump() for m in self._markers_cache]
        }
        
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return filepath


class VeracityAuditor:
    """
    The Veracity Gate — tracks V_active and triggers lockouts.
    
    In production, this wraps engine/auditor/veracity_auditor.py.
    """
    
    def __init__(self):
        self.V_active = VERACITY_CONSTANT
        self.V_initial = VERACITY_CONSTANT
        self.ticks = 0
        self.bypass_count = 0
        self.inverion_triggered = False
        self.root_fallacy_id: Optional[str] = None
        self._lockout_until: Optional[float] = None
        
    def process_fallacies(self, fallacies: List[FallacyTelemetry]) -> Dict:
        """Process detected fallacies and update veracity state."""
        self.ticks += 1
        
        # Check for lockout
        if self._lockout_until and time.time() < self._lockout_until:
            return {
                "accepted": False,
                "reason": "lockout",
                "V_active": self.V_active,
                "bypass_triggered": True
            }
        
        # Calculate veracity decay
        total_cost = sum(f.magnitude * f.persistence for f in fallacies)
        
        previous_V = self.V_active
        self.V_active -= total_cost
        
        # Bypass detection: sudden spike
        bypass_triggered = (previous_V - self.V_active) > BYPASS_THRESHOLD
        if bypass_triggered:
            self.bypass_count += 1
            self._lockout_until = time.time() + 3.0
            
        # Inverion Divide: total collapse
        if self.V_active <= SHUTDOWN_THRESHOLD:
            self.V_active = SHUTDOWN_THRESHOLD
            self.inverion_triggered = True
            if not self.root_fallacy_id and fallacies:
                self.root_fallacy_id = hashlib.md5(
                    f"{fallacies[0].type}:{fallacies[0].coord}".encode()
                ).hexdigest()[:12]
        
        return {
            "accepted": True,
            "V_cost": total_cost,
            "V_before": previous_V,
            "V_after": self.V_active,
            "bypass_triggered": bypass_triggered,
            "inverion_triggered": self.inverion_triggered
        }
    
    def get_state(self) -> VeracityState:
        """Get current veracity state."""
        return VeracityState(
            V_active=self.V_active,
            V_initial=self.V_initial,
            ticks=self.ticks,
            bypass_count=self.bypass_count,
            inverion_triggered=self.inverion_triggered,
            root_fallacy_id=self.root_fallacy_id
        )


class InverionBridge:
    """
    The Sovereign Scrubber — main server loop.
    
    Ingests from sources, audits through Veracity Gate, 
    and serves Sunrise telemetry to frontend.
    """
    
    def __init__(self):
        self.scrubber = SemanticScrubber()
        self.auditor = VeracityAuditor()
        self._running = False
        
    def process_input(self, raw_input: str) -> Dict:
        """Process input through the full Inverion pipeline."""
        # 1. Semantic analysis
        fallacies = self.scrubber.analyze(raw_input)
        
        # 2. Veracity audit
        audit_result = self.auditor.process_fallacies(fallacies)
        
        # 3. Build output
        output = {
            "timestamp": time.time(),
            "input_hash": hashlib.sha256(raw_input.encode()).hexdigest()[:16],
            "input_preview": raw_input[:100] + "..." if len(raw_input) > 100 else raw_input,
            "fallacies": [f.to_dict() for f in fallacies],
            "veracity": self.auditor.get_state().to_dict(),
            "audit": audit_result
        }
        
        return output
    
    def run(self, source_file: Optional[str] = None):
        """Run the bridge loop."""
        self._running = True
        
        print(f"--- [INVERION BRIDGE ACTIVE] ---", file=sys.stderr)
        print(f"Veracity Constant: {VERACITY_CONSTANT}", file=sys.stderr)
        print(f"Bypass Threshold: {BYPASS_THRESHOLD}", file=sys.stderr)
        print(f"Lockout Threshold: {LOCKOUT_THRESHOLD}", file=sys.stderr)
        
        try:
            while self._running:
                # 1. Ingest from source
                if source_file and Path(source_file).exists():
                    with open(source_file, 'r', encoding='utf-8') as f:
                        raw_input = f.read()
                else:
                    # Read from stdin (pipe mode)
                    raw_input = input().strip()
                    if not raw_input:
                        break
                        
                # 2. Process through pipeline
                result = self.process_input(raw_input)
                
                # 3. Check for Inverion Divide
                if result["veracity"]["inverion_triggered"]:
                    print("[!] INVERION DIVIDE CROSSED: LOCKOUT INITIATED", file=sys.stderr)
                    
                # 4. Output JSON for frontend stitching
                print(json.dumps(result), flush=True)
                
                # 5. Check for lockout
                if result["audit"].get("bypass_triggered"):
                    print("[!] BYPASS DETECTED: Lockout for 3 seconds", file=sys.stderr)
                    time.sleep(3.0)
                    
        except KeyboardInterrupt:
            print("--- [BRIDGE SHUTDOWN] ---", file=sys.stderr)
            
    def stop(self):
        """Stop the bridge loop."""
        self._running = False


def main():
    """Main entry point."""
    load_env_file()  # Load .env if present
    import argparse
    
    parser = argparse.ArgumentParser(description="Inverion Semantic Bridge")
    parser.add_argument("--source", "-s", help="Source file to analyze")
    parser.add_argument("--test", "-t", action="store_true", help="Run test mode")
    args = parser.parse_args()
    
    bridge = InverionBridge()
    
    if args.test:
        # Test with sample input
        test_inputs = [
            "You should believe me because I am always right.",
            "Either we cut spending or we go bankrupt.",
            "If we allow this, then bad things will happen too.",
            "Everyone knows that this is obviously the best approach, therefore we must proceed.",
        ]
        
        for inp in test_inputs:
            result = bridge.process_input(inp)
            print(f"\nInput: {inp}")
            print(json.dumps(result, indent=2))
            
    elif args.source:
        bridge.run(source_file=args.source)
        
    else:
        # Interactive mode
        print("Enter text to analyze (Ctrl+C to exit):", file=sys.stderr)
        bridge.run()


if __name__ == "__main__":
    main()