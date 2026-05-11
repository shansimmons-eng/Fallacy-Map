"""
Geographic Transformer - Converts location strings to lat/long coordinates

Uses GeoPy for geocoding and the Sunrise color spectrum for visualization.
Transmits to WordPress/MapPress via WPGetAPI.

Usage:
    python3 -m engine.geo_transformer --test "Paris, FR"
    python3 -m engine.geo_transformer --batch locations.json
"""

import json
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from enum import Enum


class SunriseColor(Enum):
    """Sunrise spectrum colors for map markers."""
    IGNITION = "#FFFFFF"      # High Veracity / Objective Reporting
    STABLE = "#FFD54F"       # Morning Amber
    DISTORTED = "#FF8F00"     # Deep Amber / Fallacy Detected
    ECLIPSE = "#880E4F"       # Structural Collapse / Disinformation


@dataclass
class GeoPoint:
    """Represents a geocoded point with veracity metadata."""
    id: str
    location_raw: str
    location_clean: str
    lat: Optional[float]
    lon: Optional[float]
    veracity_score: float
    timestamp: float
    source: str
    color: str = "#FFFFFF"
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(self.location_raw.encode()).hexdigest()[:12]
        self.color = self._calculate_color()
    
    def _calculate_color(self) -> str:
        """Calculate sunrise color based on veracity score."""
        if self.veracity_score > 0.8:
            return SunriseColor.IGNITION.value
        elif self.veracity_score > 0.5:
            return SunriseColor.STABLE.value
        elif self.veracity_score > 0.2:
            return SunriseColor.DISTORTED.value
        else:
            return SunriseColor.ECLIPSE.value
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_mappress_marker(self) -> dict:
        """Convert to MapPress marker format."""
        return {
            "id": self.id,
            "lat": self.lat,
            "lng": self.lon,
            "title": self.location_clean,
            "description": f"V: {self.veracity_score:.2f}",
            "color": self.color,
            "veracity": self.veracity_score
        }
    
    def has_valid_coordinates(self) -> bool:
        return self.lat is not None and self.lon is not None


class GeoTransformer:
    """
    Geographic Transformer for converting location strings to coordinates.
    
    Uses GeoPy for geocoding. Falls back to caching and pattern matching
    when geocoding services are unavailable.
    """
    
    # Location pattern mappings for common locations
    LOCATION_PATTERNS = {
        "united states": (37.0902, -95.7129),
        "usa": (37.0902, -95.7129),
        "uk": (55.3781, -3.4360),
        "united kingdom": (55.3781, -3.4360),
        "france": (46.2276, 2.2137),
        "germany": (51.1657, 10.4515),
        "australia": (-25.2744, 133.7751),
        "canada": (56.1304, -106.3468),
        "india": (20.5937, 78.9629),
        "brazil": (-14.2350, -51.9253),
        "china": (35.8617, 104.1954),
        "russia": (61.5240, 105.3188),
        "japan": (36.2048, 138.2529),
        "germany": (51.1657, 10.4515),
        "italy": (41.8719, 12.5674),
        "spain": (40.4637, -3.7492),
        "mexico": (23.6345, -102.5528),
        "global": (0.0, 0.0),
    }
    
    # US State abbreviations
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
    
    def __init__(self, geopy_enabled: bool = False):
        """
        Initialize the Geographic Transformer.
        
        Args:
            geopy_enabled: If True, attempt to use GeoPy for geocoding.
                          If False, use pattern matching only.
        """
        self.geopy_enabled = geopy_enabled
        self._geocoder = None
        self._cache: Dict[str, Tuple[float, float]] = {}
        
        if geopy_enabled:
            self._init_geopy()
    
    def _init_geopy(self) -> bool:
        """Initialize GeoPy geocoder."""
        try:
            from geopy.geocoders import Nominatim
            self._geocoder = Nominatim(user_agent="Inverion-Sovereignty-Engine/1.0")
            return True
        except ImportError:
            print("GeoPy not installed. Using pattern matching fallback.", file=__import__('sys').stderr)
            return False
        except Exception as e:
            print(f"GeoPy init error: {e}", file=__import__('sys').stderr)
            return False
    
    def geocode(self, location_str: str, veracity_score: float = 1.0) -> GeoPoint:
        """
        Geocode a location string to lat/long coordinates.
        
        Args:
            location_str: Raw location string (e.g., "Temple, TX" or "Paris, FR")
            veracity_score: Veracity score for color coding
            
        Returns:
            GeoPoint with coordinates
        """
        location_clean = self._clean_location(location_str)
        
        # Check cache first
        if location_clean in self._cache:
            lat, lon = self._cache[location_clean]
            return GeoPoint(
                id="",
                location_raw=location_str,
                location_clean=location_clean,
                lat=lat,
                lon=lon,
                veracity_score=veracity_score,
                timestamp=time.time(),
                source="cache"
            )
        
        # Try GeoPy if enabled
        if self.geopy_enabled and self._geocoder:
            try:
                location = self._geocoder.geocode(location_clean, timeout=5)
                if location:
                    coords = (location.latitude, location.longitude)
                    self._cache[location_clean] = coords
                    return GeoPoint(
                        id="",
                        location_raw=location_str,
                        location_clean=location_clean,
                        lat=coords[0],
                        lon=coords[1],
                        veracity_score=veracity_score,
                        timestamp=time.time(),
                        source="geopy"
                    )
            except Exception as e:
                print(f"Geocoding error for '{location_clean}': {e}", file=__import__('sys').stderr)
        
        # Fall back to pattern matching
        lat, lon = self._pattern_match(location_clean)
        
        return GeoPoint(
            id="",
            location_raw=location_str,
            location_clean=location_clean,
            lat=lat,
            lon=lon,
            veracity_score=veracity_score,
            timestamp=time.time(),
            source="pattern"
        )
    
    def _clean_location(self, location_str: str) -> str:
        """Clean and normalize location string."""
        # Remove common suffixes
        cleaned = location_str.strip()
        
        # Handle "City, ST" format (US)
        if "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2:
                city = parts[0].strip()
                state = parts[1].strip().upper()
                if len(state) == 2 and state.isalpha():
                    return f"{city}, {state}"
        
        return cleaned
    
    def _pattern_match(self, location_clean: str) -> Tuple[float, float]:
        """
        Match location using pattern database.
        
        Returns (0.0, 0.0) for unmapped locations (Global).
        """
        loc_lower = location_clean.lower()
        
        # Check for US state
        for abbrev, coords in self.US_STATES.items():
            if abbrev in loc_lower or abbrev.lower() in loc_lower:
                return coords
        
        # Check for country
        for country, coords in self.LOCATION_PATTERNS.items():
            if country in loc_lower:
                return coords
        
        # Return global center as fallback
        return (0.0, 0.0)
    
    def batch_geocode(self, locations: List[dict]) -> List[GeoPoint]:
        """
        Geocode a batch of locations.
        
        Args:
            locations: List of dicts with 'location' and optional 'veracity' keys
            
        Returns:
            List of GeoPoints
        """
        points = []
        
        for loc_data in locations:
            location_str = loc_data.get("location", "")
            veracity = loc_data.get("veracity", 1.0)
            
            if location_str:
                point = self.geocode(location_str, veracity)
                points.append(point)
                
                # Rate limit for API calls
                if self.geopy_enabled:
                    time.sleep(1.0)
        
        return points


class MapPressBridge:
    """
    Bridge to WordPress/MapPress for injecting map markers.
    
    Uses WPGetAPI to communicate with WordPress REST API.
    """
    
    def __init__(self, site_url: str, api_key: Optional[str] = None):
        self.site_url = site_url.rstrip("/")
        self.api_key = api_key
        self._markers: List[dict] = []
        
    def add_marker(self, point: GeoPoint) -> bool:
        """
        Add a marker to the internal queue.
        
        Returns True if successful.
        """
        if point.has_valid_coordinates():
            self._markers.append(point.to_mappress_marker())
            return True
        return False
    
    def add_markers(self, points: List[GeoPoint]) -> int:
        """Add multiple markers. Returns count of successful adds."""
        count = 0
        for point in points:
            if self.add_marker(point):
                count += 1
        return count
    
    def export_json(self, filepath: str) -> str:
        """Export markers to JSON file for MapPress import."""
        data = {
            "markers": self._markers,
            "export_timestamp": time.time(),
            "count": len(self._markers)
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        return filepath
    
    def get_marker_count(self) -> int:
        """Get current marker count."""
        return len(self._markers)
    
    def clear_markers(self) -> None:
        """Clear all markers."""
        self._markers.clear()
    
    def get_markdown_report(self) -> str:
        """Generate markdown report of markers."""
        lines = [
            "# MapPress Marker Report",
            f"",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Markers:** {len(self._markers)}",
            f"",
            "## Markers by Sunrise Color",
            f"",
        ]
        
        color_counts = {}
        for marker in self._markers:
            color = marker.get("color", "#FFFFFF")
            color_counts[color] = color_counts.get(color, 0) + 1
        
        for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {color}: {count} markers")
        
        lines.extend([
            f"",
            "## Full Marker List",
            f"",
            "| Location | Lat | Lon | Veracity | Color |",
            "|---------|-----|-----|----------|-------|",
        ])
        
        for marker in self._markers:
            lines.append(
                f"| {marker['title']} | {marker['lat']} | {marker['lng']} | "
                f"{marker['veracity']:.2f} | {marker['color']} |"
            )
        
        return "\n".join(lines)


def main():
    """Test the Geographic Transformer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Geographic Transformer")
    parser.add_argument("--location", "-l", help="Single location to geocode")
    parser.add_argument("--batch", "-b", help="JSON file with batch locations")
    parser.add_argument("--test", action="store_true", help="Run test mode")
    args = parser.parse_args()
    
    transformer = GeoTransformer(geopy_enabled=False)
    bridge = MapPressBridge("https://kylosarc.com")
    
    if args.test or not args.location:
        # Test with sample locations
        test_locations = [
            "Temple, TX",
            "Paris, FR", 
            "London, UK",
            "Climate Summit",
            "Berlin, DE",
        ]
        
        print("Testing Geographic Transformer:\n")
        for loc in test_locations:
            point = transformer.geocode(loc, veracity_score=0.85)
            print(f"  {loc}")
            print(f"    → {point.location_clean}")
            print(f"    → ({point.lat}, {point.lon})")
            print(f"    → Color: {point.color}")
            print()
            bridge.add_marker(point)
    
    elif args.location:
        # Single location
        point = transformer.geocode(args.location)
        print(f"Location: {point.location_clean}")
        print(f"Coordinates: ({point.lat}, {point.lon})")
        print(f"Color: {point.color}")
        
    if bridge.get_marker_count() > 0:
        print(f"\n{bridge.get_marker_count()} markers ready for MapPress")
        
        # Export report
        report = bridge.get_markdown_report()
        print("\n" + report)


if __name__ == "__main__":
    main()