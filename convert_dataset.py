#!/usr/bin/env python3
"""
Convert logical-fallacy CSV dataset to mock_ledger.json format.
Downloads and processes data from: https://github.com/tmakesense/logical-fallacy

Usage:
    python3 convert_dataset.py [--download] [--limit 100]
"""

import json
import urllib.request
import csv
import re
import sys
from io import StringIO
from typing import Dict, List, Optional

CSV_URL = "https://raw.githubusercontent.com/tmakesense/logical-fallacy/main/dataset-fixed/edu_all_fixed.csv"

FALLACY_LABEL_MAP = {
    "faulty generalization": "hasty_generalization",
    "hasty generalization": "hasty_generalization",
    "false causality": "false_cause",
    "cum hoc ergo propter hoc": "post_hoc",
    "post hoc ergo propter hoc": "post_hoc",
    "circular reasoning": "circular_reasoning",
    "ad populum": "bandwagon",
    "ad hominem": "ad_hominem",
    "ad hominem; tu quoque": "tu_quoque",
    "fallacy of logic": "formal_fallacy",
    "false analogy": "false_analogy",
    "affirming the consequent": "affirming_consequent",
    "denying the antecedent": "denying_antecedent",
    "non-sequitur": "non_sequitur",
    "appeal to emotion": "appeal_to_emotion",
    "appeal to pity": "appeal_to_pity",
    "appeal to fear": "appeal_to_fear",
    "slippery slope": "slippery_slope",
    "false dilemma": "false_dilemma",
    "false authority": "false_authority",
    "strawman": "strawman",
    "begging the question": "begging_the_question",
    "red herring": "red_herring",
    "hasty generalization; faulty generalization": "hasty_generalization",
    "false cause": "false_cause",
}

VERACITY_BY_TYPE = {
    "hasty_generalization": (0.25, 0.45),
    "post_hoc": (0.35, 0.55),
    "false_cause": (0.35, 0.55),
    "circular_reasoning": (0.15, 0.35),
    "bandwagon": (0.40, 0.60),
    "ad_hominem": (0.25, 0.45),
    "appeal_to_emotion": (0.40, 0.60),
    "appeal_to_pity": (0.40, 0.55),
    "appeal_to_fear": (0.30, 0.50),
    "slippery_slope": (0.30, 0.50),
    "false_dilemma": (0.30, 0.50),
    "false_authority": (0.45, 0.65),
    "strawman": (0.40, 0.60),
    "begging_the_question": (0.25, 0.45),
    "red_herring": (0.45, 0.65),
    "false_analogy": (0.45, 0.65),
    "affirming_consequent": (0.40, 0.60),
    "denying_antecedent": (0.40, 0.60),
    "non_sequitur": (0.35, 0.55),
    "tu_quoque": (0.40, 0.60),
    "formal_fallacy": (0.40, 0.60),
}

LOCATION_POOL = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Seattle",
    "Denver", "Boston", "Detroit", "Las Vegas", "Portland", "Miami",
    "Atlanta", "Washington DC", "London", "Paris", "Berlin", "Tokyo",
    "Sydney", "Toronto", "Singapore", "Hong Kong", "Mumbai", "Dubai"
]

SOURCE_POOL = [
    "Quizizz", "Education Weekly", "ThoughtCo", "Wikipedia", "Logical Fallacies dot com",
    "Purdue OWL", "Annenberg Classroom", "Lifehacker", "Towards Data Science"
]

def fetch_csv(url: str) -> str:
    """Fetch CSV content from URL."""
    print(f"Fetching CSV from {url}...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode('utf-8')

def parse_csv(content: str) -> List[Dict]:
    """Parse CSV content into list of dicts."""
    reader = csv.DictReader(StringIO(content))
    return list(reader)

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    text = re.sub(r'^[""]|[""]$', '', text.strip())
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def get_fallacy_type(label: str) -> Optional[str]:
    """Map CSV label to internal fallacy type."""
    label_lower = label.lower().strip()
    return FALLACY_LABEL_MAP.get(label_lower, label_lower.replace(' ', '_'))

def get_veracity_score(fallacy_type: str) -> float:
    """Get veracity score range for fallacy type."""
    if fallacy_type in VERACITY_BY_TYPE:
        low, high = VERACITY_BY_TYPE[fallacy_type]
        import random
        return round(random.uniform(low, high), 2)
    return round(0.5 + hash(fallacy_type) % 30 / 100, 2)

def generate_mock_entries(csv_rows: List[Dict], limit: int = 100) -> List[Dict]:
    """Convert CSV rows to mock ledger entries."""
    entries = []
    seen_titles = set()
    counter = 1

    for row in csv_rows:
        if len(entries) >= limit:
            break

        text = clean_text(row.get('source_article', ''))
        label = row.get('updated_label', '')
        old_label = row.get('old_label', '')

        if not text or len(text) < 20 or len(text) > 300:
            continue

        if text in seen_titles:
            continue

        fallacy_type = get_fallacy_type(label)
        if not fallacy_type:
            fallacy_type = get_fallacy_type(old_label)

        veracity = get_veracity_score(fallacy_type)
        veracity = min(0.99, max(0.10, veracity))

        import random
        location = random.choice(LOCATION_POOL)
        source = random.choice(SOURCE_POOL)

        entry = {
            "id": f"dataset_{counter:04d}",
            "title": text,
            "raw_location": location,
            "source_url": row.get('original_url', f'https://quizizz.com/mock/{counter}'),
            "source_name": source,
            "veracity_score": veracity,
            "fallacy_types": [fallacy_type],
            "dataset_label": label,
            "dataset_old_label": old_label
        }
        entries.append(entry)
        seen_titles.add(text)
        counter += 1

    return entries

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert logical-fallacy CSV to mock_ledger.json")
    parser.add_argument("--download", action="store_true", help="Download fresh CSV from GitHub")
    parser.add_argument("--input", help="Use local CSV file instead of downloading")
    parser.add_argument("--limit", type=int, default=150, help="Number of entries to generate")
    parser.add_argument("--output", default="mock_ledger.json", help="Output file")
    args = parser.parse_args()

    if args.download or args.input:
        if args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                csv_content = f.read()
        else:
            csv_content = fetch_csv(CSV_URL)

        rows = parse_csv(csv_content)
        print(f"Parsed {len(rows)} rows from CSV", file=sys.stderr)
    else:
        print("Usage: python3 convert_dataset.py --download --limit 150", file=sys.stderr)
        print("  Or: python3 convert_dataset.py --input /path/to/edu_all_fixed.csv --limit 150", file=sys.stderr)
        sys.exit(1)

    entries = generate_mock_entries(rows, limit=args.limit)
    print(f"Generated {len(entries)} mock entries", file=sys.stderr)

    output = {
        "metadata": {
            "description": "Mock ledger generated from logical-fallacy dataset",
            "version": "3.0",
            "source": "https://github.com/tmakesense/logical-fallacy",
            "count": len(entries),
            "fallacy_types": list(set(e["fallacy_types"][0] for e in entries))
        },
        "events": entries
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()