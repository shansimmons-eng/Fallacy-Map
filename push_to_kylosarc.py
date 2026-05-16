#!/usr/bin/env python3
"""
Test script to push a marker to KylosArc.com Map ID 2
Loads credentials from .env file (KYLOSARC_WP_EMAIL, KYLOSARC_WP_PW)
or uses WP_APP_PASSWORD environment variable.
"""
import os
import sys
sys.path.insert(0, '.')

from server import MapPressBridge, PublicationMarker, SemanticScrubber, GeoTransformer

WP_SITE = "https://kylosarc.com"

def get_wp_credentials():
    # Try .env file values first
    email = os.environ.get("KYLOSARC_WP_EMAIL", "")
    password = os.environ.get("WP_App_PW_MAPAPP", "") or os.environ.get("KYLOSARC_WP_PW", "")
    
    # Fallback to WP_APP_PASSWORD if only password is needed
    if not password:
        password = os.environ.get("WP_APP_PASSWORD", "")
        if password:
            email = os.environ.get("KYLOSARC_WP_USER", "admin")
    
    if not email or not password:
        print("ERROR: Set KYLOSARC_WP_EMAIL and KYLOSARC_WP_PW in .env")
        print("  (or WP_APP_PASSWORD for just the password)")
        print("  And KYLOSARC_WP_USER for the username")
        sys.exit(1)
    
    # Extract username from email (before @)
    username = email.split('@')[0] if '@' in email else email
    return username, password

def push_test_marker():
    WP_USER, WP_PASS = get_wp_credentials()
    
    test_headline = "You should believe me because I am always right about everything."
    
    scrubber = SemanticScrubber()
    fallacies = scrubber.analyze(test_headline)
    total_cost = sum(f.magnitude * f.persistence for f in fallacies)
    veracity_score = max(0.0, 1.0 - total_cost)
    
    geo = GeoTransformer()
    lat, lon = geo.geocode("Temple, TX")
    print(f"Geocoded Temple, TX: ({lat}, {lon})")
    
    marker = PublicationMarker(
        id="test_kylosarc_001",
        title=test_headline[:100],
        headline=test_headline,
        source_url="https://test.com/climate-hoax",
        source_name="Test Publication",
        lat=lat,
        lon=lon,
        veracity_score=veracity_score,
        fallacy_types=[f.type for f in fallacies],
        published_at=""
    )
    
    print(f"Marker: {marker.headline}")
    print(f"Veracity: {marker.veracity_score:.2f} ({marker.color})")
    print(f"Location: ({marker.lat}, {marker.lon})")
    print(f"Falcies: {marker.fallacy_types}")
    
    bridge = MapPressBridge(WP_SITE, WP_USER, WP_PASS)
    result = bridge.post_marker(marker)
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return False
    else:
        print(f"SUCCESS: Marker posted with ID {result.get('id', result.get('post_id', 'unknown'))}")
        shadow_path = bridge._archive_to_shadow(marker, result.get('id', 'unknown'))
        print(f"Archived to: {shadow_path}")
        return True

if __name__ == "__main__":
    push_test_marker()
