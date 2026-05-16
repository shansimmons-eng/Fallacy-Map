#!/usr/bin/env python3
"""
Rank Math SEO Meta Generator

Analyzes existing Rank Math data to understand writing style,
then fills empty meta tags for all posts.

Usage:
    export STIFLI_USERNAME="shan.simmons@gmail.com"
    export STIFLI_PASSWORD="your-app-password"
    python3 rankmath_meta_filler.py
"""

import os
import sys
import json
from collections import defaultdict

# Import the connector
from stifli_connector import StifliMCP


class RankMathMetaFiller:
    def __init__(self):
        self.mcp = StifliMCP()
        self.style_analysis = {
            "title_tone": "professional",
            "description_length": 155,
            "focus_keyword_style": "comma-separated phrases",
            "social_style": "engaging",
        }
    
    def analyze_existing_style(self) -> dict:
        """Sample existing Rank Math data to understand writing style."""
        print("[*] Analyzing existing Rank Math SEO data...")
        
        # Get posts with existing SEO data
        result = self.mcp._post("tools/call", {
            "name": "wp_get_posts",
            "arguments": {"limit": 10, "post_type": "post"}
        })
        
        sample_data = []
        if result.get("result", {}).get("posts"):
            for post in result["result"]["posts"][:5]:
                post_id = post.get("ID")
                if not post_id:
                    continue
                
                # Get Rank Math SEO data
                seo_result = self.mcp._post("tools/call", {
                    "name": "wp_rm_get_post_seo",
                    "arguments": {"post_id": post_id}
                })
                
                if seo_result.get("result"):
                    seo = seo_result["result"]
                    sample_data.append({
                        "title": post.get("title", {}).get("rendered", ""),
                        "seo_title": seo.get("title", ""),
                        "seo_description": seo.get("description", ""),
                        "focus_keyword": seo.get("focus_keyword", ""),
                    })
        
        # Analyze style from sample
        if sample_data:
            titles = [s["seo_title"] for s in sample_data if s["seo_title"]]
            descriptions = [s["seo_description"] for s in sample_data if s["seo_description"]]
            keywords = [s["focus_keyword"] for s in sample_data if s["focus_keyword"]]
            
            if titles:
                print(f"   - Found {len(titles)} titles with Rank Math data")
                self.style_analysis["sample_titles"] = titles[:3]
            if descriptions:
                print(f"   - Found {len(descriptions)} descriptions")
                self.style_analysis["sample_descriptions"] = descriptions[:3]
            if keywords:
                print(f"   - Found {len(keywords)} focus keywords")
                self.style_analysis["sample_keywords"] = keywords[:3]
        
        return self.style_analysis
    
    def generate_seo_content(self, post: dict, style: dict) -> dict:
        """Generate SEO content based on post content and existing style."""
        title = post.get("title", {}).get("rendered", "")
        content = post.get("content", {}).get("rendered", "")
        raw_content = post.get("content", {}).get("raw", "")
        
        # Clean HTML from content
        import re
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        # Generate title (Rank Math allows ~60 chars)
        seo_title = title
        if len(seo_title) > 60:
            seo_title = seo_title[:57] + "..."
        
        # Generate description (Rank Math recommends 155-160 chars)
        if len(clean_content) > 160:
            description = clean_content[:155].rsplit(' ', 1)[0] + "..."
        else:
            description = clean_content
        
        # Generate focus keyword from title
        focus_keyword = title.split('|')[0].split('-')[0].strip()
        focus_keyword = re.sub(r'[^\w\s]', '', focus_keyword)
        
        # Generate social meta
        facebook_title = seo_title
        facebook_description = description[:160] if len(description) > 160 else description
        
        twitter_title = seo_title
        twitter_description = description[:160] if len(description) > 160 else description
        
        return {
            "title": seo_title,
            "description": description,
            "focus_keyword": focus_keyword,
            "facebook_title": facebook_title,
            "facebook_description": facebook_description[:200],
            "twitter_title": twitter_title,
            "twitter_description": twitter_description[:200],
        }
    
    def fill_empty_meta(self, dry_run: bool = True):
        """Find posts with empty meta and fill them."""
        print(f"\n[*] Fetching all posts (dry_run={dry_run})...")
        
        all_posts = []
        offset = 0
        batch_size = 50
        
        while True:
            result = self.mcp._post("tools/call", {
                "name": "wp_get_posts",
                "arguments": {
                    "limit": batch_size,
                    "offset": offset,
                    "post_type": "post",
                    "post_status": "any"
                }
            })
            
            posts = result.get("result", {}).get("posts", [])
            if not posts:
                break
            
            all_posts.extend(posts)
            print(f"   - Fetched {len(posts)} posts (total: {len(all_posts)})")
            
            if len(posts) < batch_size:
                break
            
            offset += batch_size
        
        print(f"[*] Total posts: {len(all_posts)}")
        
        # Analyze existing style first
        self.analyze_existing_style()
        
        # Check each post for missing meta
        needs_update = []
        for post in all_posts:
            post_id = post.get("ID")
            if not post_id:
                continue
            
            title = post.get("title", {}).get("rendered", "")
            excerpt = post.get("excerpt", {}).get("raw", "")
            
            # Get Rank Math SEO data
            seo_result = self.mcp._post("tools/call", {
                "name": "wp_rm_get_post_seo",
                "arguments": {"post_id": post_id}
            })
            
            seo = seo_result.get("result", {})
            seo_title = seo.get("title", "")
            seo_desc = seo.get("description", "")
            
            # Check if meta is empty
            if not seo_title or not seo_desc or not excerpt.strip():
                needs_update.append({
                    "post_id": post_id,
                    "title": title,
                    "current_seo_title": seo_title,
                    "current_seo_desc": seo_desc,
                    "current_excerpt": excerpt,
                })
        
        print(f"[*] Posts needing meta updates: {len(needs_update)}")
        
        if not needs_update:
            print("[*] All posts already have complete meta!")
            return
        
        # Show sample of what will be updated
        print("\n[*] Sample updates:")
        for item in needs_update[:3]:
            print(f"   Post #{item['post_id']}: {item['title'][:50]}...")
            print(f"     Current SEO: title='{item['current_seo_title'][:30]}...' desc='{item['current_seo_desc'][:30]}...'")
        
        if dry_run:
            print(f"\n[*] DRY RUN - No changes made. Run with dry_run=False to apply.")
            return
        
        # Apply updates
        print(f"\n[*] Applying {len(needs_update)} updates...")
        for i, item in enumerate(needs_update):
            post_id = item["post_id"]
            
            # Get fresh post data for content analysis
            post_result = self.mcp._post("tools/call", {
                "name": "wp_get_post",
                "arguments": {"ID": post_id}
            })
            
            post_data = post_result.get("result", {})
            
            # Generate new meta content
            new_meta = self.generate_seo_content(post_data, self.style_analysis)
            
            # Update Rank Math SEO
            seo_update = self.mcp._post("tools/call", {
                "name": "wp_rm_update_post_seo",
                "arguments": {
                    "post_id": post_id,
                    "title": new_meta["title"],
                    "description": new_meta["description"],
                    "focus_keyword": new_meta["focus_keyword"],
                    "facebook_title": new_meta["facebook_title"],
                    "facebook_description": new_meta["facebook_description"],
                    "twitter_title": new_meta["twitter_title"],
                    "twitter_description": new_meta["twitter_description"],
                }
            })
            
            # Update WordPress excerpt if empty
            if not item["current_excerpt"].strip():
                excerpt_update = self.mcp._post("tools/call", {
                    "name": "wp_update_post",
                    "arguments": {
                        "ID": post_id,
                        "fields": {"post_excerpt": new_meta["description"]}
                    }
                })
            
            print(f"   Updated #{post_id}: {new_meta['title'][:40]}...")
            
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{len(needs_update)}")
        
        print(f"\n[*] COMPLETE: Updated {len(needs_update)} posts")
    
    def fill_pages(self, dry_run: bool = True):
        """Also fill meta for pages."""
        print(f"\n[*] Fetching all pages...")
        
        all_pages = []
        offset = 0
        batch_size = 50
        
        while True:
            result = self.mcp._post("tools/call", {
                "name": "wp_get_pages",
                "arguments": {
                    "limit": batch_size,
                    "offset": offset,
                }
            })
            
            pages = result.get("result", {}).get("pages", [])
            if not pages:
                break
            
            all_pages.extend(pages)
            print(f"   - Fetched {len(pages)} pages (total: {len(all_pages)})")
            
            if len(pages) < batch_size:
                break
            
            offset += batch_size
        
        print(f"[*] Total pages: {len(all_pages)}")
        
        needs_update = []
        for page in all_pages:
            page_id = page.get("ID")
            if not page_id:
                continue
            
            title = page.get("title", {}).get("rendered", "")
            excerpt = page.get("excerpt", {}).get("raw", "")
            
            # Get Rank Math SEO data
            seo_result = self.mcp._post("tools/call", {
                "name": "wp_rm_get_post_seo",
                "arguments": {"post_id": page_id}
            })
            
            seo = seo_result.get("result", {})
            seo_title = seo.get("title", "")
            seo_desc = seo.get("description", "")
            
            # Check if meta is empty
            if not seo_title or not seo_desc or not excerpt.strip():
                needs_update.append({
                    "post_id": page_id,
                    "title": title,
                    "current_seo_title": seo_title,
                    "current_seo_desc": seo_desc,
                    "current_excerpt": excerpt,
                })
        
        print(f"[*] Pages needing meta updates: {len(needs_update)}")
        
        if not needs_update:
            print("[*] All pages already have complete meta!")
            return
        
        if dry_run:
            print(f"\n[*] DRY RUN - No changes made.")
            return
        
        print(f"\n[*] Applying {len(needs_update)} page updates...")
        for item in needs_update:
            post_id = item["post_id"]
            
            post_result = self.mcp._post("tools/call", {
                "name": "wp_get_post",
                "arguments": {"ID": post_id}
            })
            
            post_data = post_result.get("result", {})
            new_meta = self.generate_seo_content(post_data, self.style_analysis)
            
            self.mcp._post("tools/call", {
                "name": "wp_rm_update_post_seo",
                "arguments": {
                    "post_id": post_id,
                    "title": new_meta["title"],
                    "description": new_meta["description"],
                    "focus_keyword": new_meta["focus_keyword"],
                    "facebook_title": new_meta["facebook_title"],
                    "facebook_description": new_meta["facebook_description"],
                    "twitter_title": new_meta["twitter_title"],
                    "twitter_description": new_meta["twitter_description"],
                }
            })
            
            if not item["current_excerpt"].strip():
                self.mcp._post("tools/call", {
                    "name": "wp_update_page",
                    "arguments": {
                        "ID": post_id,
                        "post_excerpt": new_meta["description"]
                    }
                })
            
            print(f"   Updated page #{post_id}: {new_meta['title'][:40]}...")
        
        print(f"\n[*] COMPLETE: Updated {len(needs_update)} pages")


def main():
    dry_run = "--apply" not in sys.argv
    
    print("=" * 60)
    print("Rank Math SEO Meta Filler")
    print("=" * 60)
    
    if dry_run:
        print("\n[*] DRY RUN MODE - No changes will be made")
        print("    Run with --apply to actually make changes")
    
    try:
        filler = RankMathMetaFiller()
        
        print("\n[1] Processing posts...")
        filler.fill_empty_meta(dry_run=dry_run)
        
        print("\n[2] Processing pages...")
        filler.fill_pages(dry_run=dry_run)
        
        if dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN complete. To apply changes, run:")
            print("  python3 rankmath_meta_filler.py --apply")
    
    except ValueError as e:
        print(f"\nError: {e}")
        print("Set environment variables:")
        print("  export STIFLI_USERNAME='your-email@example.com'")
        print("  export STIFLI_PASSWORD='your-app-password'")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()