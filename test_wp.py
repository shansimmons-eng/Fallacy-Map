#!/usr/bin/env python3
"""Test WordPress connectivity and create a test post"""
import sys
import os
import json
import base64
import urllib.request
import urllib.error

SITE = "https://kylosarc.com"

# Load from environment variable - NEVER hardcode passwords
def get_wp_password():
    pw = os.environ.get("WP_APP_PASSWORD", "")
    if not pw:
        raise ValueError("Set WP_APP_PASSWORD environment variable")
    return pw

PASS = get_wp_password()
USER = "admin"

def test_wordpress():
    auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    
    print("1. Testing /wp-json/ endpoint...")
    try:
        req = urllib.request.Request(
            f"{SITE}/wp-json/",
            headers={"User-Agent": "Inverion/1.0", "Authorization": f"Basic {auth}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"   OK: WordPress namespaces available: {len(data.get('namespaces', []))}")
    except Exception as e:
        print(f"   FAIL: {e}")
        return False
    
    print("\n2. Trying to read posts...")
    try:
        req = urllib.request.Request(
            f"{SITE}/wp-json/wp/v2/posts?per_page=1",
            headers={"Authorization": f"Basic {auth}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"   OK: Found {len(data)} posts")
    except urllib.error.HTTPError as e:
        print(f"   HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"   FAIL: {e}")
    
    print("\n3. Trying to create a test post...")
    payload = {
        "title": "KylosArc Inverion Test - Ignore",
        "content": "Testing the Inverion Sunrise Bridge for MapPress",
        "status": "draft",
        "meta": {
            "_mappress_veracity_score": "0.64",
            "_mappress_color": "#FFB300"
        }
    }
    
    try:
        req = urllib.request.Request(
            f"{SITE}/wp-json/wp/v2/posts",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
                "User-Agent": "Inverion/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"   OK: Created post ID {result.get('id')}")
            print(f"   Link: {result.get('link')}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"   HTTP {e.code}: {err_body[:300]}")
        return False
    except Exception as e:
        print(f"   FAIL: {e}")
        return False

if __name__ == "__main__":
    test_wordpress()
