#!/usr/bin/env python3
"""
Dry-run test for local ledger processing.
Tests detection and shows what WOULD be pushed without actually pushing.
"""
import sys
import json
import os
from pathlib import Path

sys.path.insert(0, '.')
from server import SemanticScrubber, GeoTransformer, LocalLedgerConnector, PublicationMarker, VERACITY_CONSTANT

def main():
    ledger_path = "mock_ledger.json"
    if not Path(ledger_path).exists():
        print(f"Error: {ledger_path} not found")
        sys.exit(1)
    
    print("=" * 70)
    print("DRY-RUN TEST: Local Ledger Processing")
    print("=" * 70)
    
    scrubber = SemanticScrubber()
    geo = GeoTransformer()
    connector = LocalLedgerConnector(ledger_path=ledger_path)
    
    markers = connector.fetch_with_geocode(geo)
    print(f"\nLoaded {len(markers)} markers from ledger\n")
    
    for i, marker in enumerate(markers[:10], 1):
        print(f"{i}. {marker.headline[:60]}...")
        print(f"   Location: ({marker.lat}, {marker.lon})")
        print(f"   Veracity: {marker.veracity_score:.2f} ({marker.color})")
        print(f"   Fallacies: {marker.fallacy_types}")
        
        fallacies = scrubber.analyze(marker.headline)
        detected = [f.type for f in fallacies]
        print(f"   Detected ({len(fallacies)}): {detected}")
        
        total_cost = sum(f.magnitude * f.persistence for f in fallacies)
        final_veracity = max(0.0, VERACITY_CONSTANT - total_cost)
        print(f"   Final Veracity: {final_veracity:.2f} (decay: {total_cost:.2f})")
        print()
    
    if len(markers) > 10:
        print(f"... and {len(markers) - 10} more markers")
    
    print("=" * 70)
    print("CREDENTIALS CHECK")
    print("=" * 70)
    wp_email = os.environ.get("KYLOSARC_WP_EMAIL", "")
    wp_pw = os.environ.get("WP_App_PW_MAPAPP", "") or os.environ.get("KYLOSARC_WP_PW", "")
    jwt_key = os.environ.get("JWT_WP_API_KEY", "")
    jwt_user = os.environ.get("JWT_WP_USER", "")
    
    print(f"KYLOSARC_WP_EMAIL: {'✓ set' if wp_email else '✗ missing'}")
    print(f"KYLOSARC_WP_PW: {'✓ set' if wp_pw else '✗ missing'}")
    print(f"JWT_WP_API_KEY: {'✓ set' if jwt_key else '✗ missing'}")
    print(f"JWT_WP_USER: {'✓ set' if jwt_user else '✗ missing'}")
    
    if wp_email and wp_pw:
        username = wp_email.split('@')[0]
        print(f"\nWould authenticate as: {username}")
    
    print("\n" + "=" * 70)
    print("TO PUSH TO WORDPRESS, RUN:")
    print("=" * 70)
    print("  python3 server.py --local-ledger mock_ledger.json --push-markers \\")
    print("    --wp-site https://kylosarc.com --wp-user admin")
    print()
    print("OR with loop mode:")
    print("  python3 server.py --local-ledger mock_ledger.json --loop --interval 30 \\")
    print("    --push-markers --wp-site https://kylosarc.com --wp-user admin")

if __name__ == "__main__":
    main()