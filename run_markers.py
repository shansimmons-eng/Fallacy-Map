#!/usr/bin/env python3
"""
Run mock ledger pipeline - pushes markers to WordPress Map ID 2
Usage: python3 run_markers.py [--loop]
"""
import sys
import os
from pathlib import Path

# Load .env if present
def load_env(path=".env"):
    p = Path(path)
    if not p.exists(): return
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            line = line.lstrip('export ').strip()
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

load_env()

WP_SITE = os.environ.get("KYLOSARC_WP_SITE", "https://kylosarc.com")
WP_USER = os.environ.get("KYLOSARC_WP_EMAIL", "")
WP_PASS = os.environ.get("WP_App_PW_MAPAPP", "") or os.environ.get("KYLOSARC_WP_PW", "")

import json
import time
import base64
import urllib.request

# Load mock ledger
with open("mock_ledger.json") as f:
    ledger = json.load(f)
events = ledger.get("events", [])
print(f"[Ledger] Loaded {len(events)} events from mock_ledger.json")

# Location patterns for geocoding
LOCATIONS = {
    "Washington DC": (38.9072, -77.0369),
    "California": (36.7783, -119.4179),
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Chicago": (41.8781, -87.6298),
    "Berlin": (52.5200, 13.4050),
    "Texas": (31.9686, -99.9018),
    "San Francisco": (37.7749, -122.4194),
    "Los Angeles": (34.0522, -118.2437),
    "Singapore": (1.3521, 103.8198),
}

def geocode(raw_loc):
    for name, coords in LOCATIONS.items():
        if name.lower() in raw_loc.lower():
            return coords
    return (None, None)

def veracity_to_color(score):
    if score >= 0.8: return "#FFFFFF"
    elif score >= 0.5: return "#FFB300"
    elif score >= 0.3: return "#FF8F00"
    else: return "#B71C1C"

def push_marker(event):
    lat, lon = geocode(event.get("raw_location", ""))
    color = veracity_to_color(event.get("veracity_score", 1.0))
    
    payload = {
        "title": event.get("title", "")[:100],
        "content": f"Source: {event.get('source_name', '')}\nURL: {event.get('source_url', '')}",
        "map_id": 2,
        "marker_lat": lat or 0,
        "marker_lng": lon or 0,
        "veracity_score": event.get("veracity_score", 1.0),
        "fallacy_types": event.get("fallacy_types", []),
        "marker_icon": "circle",
        "marker_color": color,
        "published_at": event.get("published_at", ""),
    }
    
    url = f"{WP_SITE}/wp-json/wp/v2/posts"
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("id", 0)
    except Exception as e:
        print(f"[Push Error] {e}", file=sys.stderr)
        return 0

if __name__ == "__main__":
    loop = "--loop" in sys.argv
    interval = 30
    
    print(f"[MapPress] Pushing to {WP_SITE} as {WP_USER}")
    
    if loop:
        idx = 0
        print(f"[Loop] Starting {interval}s interval. Ctrl+C to stop.")
        try:
            while True:
                event = events[idx % len(events)]
                event["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                pid = push_marker(event)
                if pid:
                    print(f"[Pushed] {event['title'][:50]}... -> post {pid}")
                idx += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Stopped]")
    else:
        count = 0
        for event in events:
            event["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            pid = push_marker(event)
            if pid:
                count += 1
                print(f"[{count}] {event['title'][:60]}...")
        print(f"\n[Done] Pushed {count} markers to WordPress Map ID 2")