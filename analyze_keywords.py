#!/usr/bin/env python3
"""
Keyword frequency analysis for fallacious texts.
Extracts keywords from patterns and mock_ledger to understand what words
signal fallacious reasoning most often.

Usage:
    python3 analyze_keywords.py [--patterns] [--ledger] [--top N]
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

KEYWORD_PATTERNS = [
    # Quantifiers / Generalizers
    r'\ball\b', r'\bevery\b', r'\ball\b', r'\beveryone\b', r'\benobody\b', 
    r'\bno one\b', r'\bnobody\b', r'\banyone\b', r'\bsomeone\b', r'\bany\b',
    r'\balways\b', r'\bnever\b', r'\bonly\b', r'\bjust\b', r'\banybody\b',
    
    # Modal / Authority
    r'\bshould\b', r'\bmust\b', r'\bneed\b', r'\bhave to\b', r'\bcan\b', 
    r'\bcan\'t\b', r'\bcannot\b', r'\bwill\b', r'\bwould\b', r'\bcould\b',
    r'\bmight\b', r'\bmay\b',
    
    # Comparison / Superlative
    r'\bbetter\b', r'\bbest\b', r'\bworst\b', r'\bmore\b', r'\bmost\b',
    r'\bgreater\b', r'\bgreater\b', r'\bsuperior\b', r'\binferior\b',
    r'\bdominant\b', r'\bmaximum\b', r'\bminimum\b',
    
    # Pronouns (personal)
    r'\bI\b', r'\byou\b', r'\bhe\b', r'\bshe\b', r'\bwe\b', r'\bthey\b',
    r'\bit\b', r'\bthem\b', r'\bus\b', r'\bme\b', r'\bhim\b', r'\bher\b',
    r'\bmy\b', r'\byour\b', r'\bour\b', r'\btheir\b', r'\bits\b',
    
    # Certainty / Truth
    r'\bknow\b', r'\bbelieve\b', r'\bthink\b', r'\btrue\b', r'\btruth\b',
    r'\bfalse\b', r'\breal\b', r'\breally\b', r'\bactually\b', r'\bobviously\b',
    r'\bcertainly\b', r'\bclearly\b', r'\bdefinitely\b', r'\bperhaps\b',
    r'\bmaybe\b', r'\bprobably\b', r'\bcertainly\b',
    
    # Cause / Effect
    r'\bcause\b', r'\bcauses\b', r'\bcaused\b', r'\beffect\b', r'\beffects\b',
    r'\bbecause\b', r'\bsince\b', r'\btherefore\b', r'\bthus\b', r'\bso\b',
    r'\bif\b', r'\bthen\b', r'\bwhen\b', r'\bafter\b', r'\bbefore\b',
    
    # Authority / Appeal
    r'\bexpert\b', r'\bexperts\b', r'\bscientist\b', r'\bscientists\b',
    r'\bstudy\b', r'\bstudies\b', r'\bresearch\b', r'\bproof\b', r'\bevidence\b',
    r'\bfact\b', r'\bfacts\b', r'\bdata\b', r'\bstatistic\b', r'\bpercent\b',
    
    # Emotion / Appeal
    r'\bfear\b', r'\bafraid\b', r'\b恐\b', r'\bhope\b', r'\bhopes\b',
    r'\bpeace\b', r'\bwar\b', r'\bkill\b', r'\bdie\b', r'\bdead\b', r'\blife\b',
    r'\bdeath\b', r'\bharm\b', r'\bhurt\b', r'\bsuffer\b', r'\bpity\b',
    
    # Group / Social
    r'\beveryone\b', r'\ball\b', r'\bmost\b', r'\bmost\b', r'\bgroup\b',
    r'\bpeople\b', r'\bsociety\b', r'\bworld\b', r'\bnation\b', r'\bcountry\b',
    r'\bgovernment\b', r'\bpolicy\b', r'\bpolicies\b',
    
    # Fallacy Indicators
    r'\bor\b', r'\beither\b', r'\bneither\b', r'\bnor\b', r'\bbut\b',
    r'\bhowever\b', r'\balthough\b', r'\byet\b', r'\bstill\b',
    r'\beven\b', r'\bonly\b', r'\bmerely\b', r'\bjust\b',
    
    # Moral / Judgment
    r'\bright\b', r'\bwrong\b', r'\bgood\b', r'\bbad\b', r'\bevil\b',
    r'\bjust\b', r'\bunjust\b', r'\bfair\b', r'\bunfair\b', r'\bdeserve\b',
    r'\bworthy\b', r'\bblame\b', r'\bpraise\b',
]

FALLACY_KEYWORDS = {
    'hasty_generalization': ['all', 'every', 'everyone', 'nobody', 'no one', 'always', 'never', 'any', 'all'],
    'circular_reasoning': ['because', 'true', 'truth', 'since', 'know', 'believe'],
    'post_hoc': ['after', 'then', 'since', 'because', 'therefore', 'caused'],
    'bandwagon': ['everyone', 'everybody', 'all', 'most', 'millions', 'billion', 'popular'],
    'ad_hominem': ['you', 'your', 'they', 'them', 'stupid', 'dumb', 'idiot'],
    'appeal_to_emotion': ['fear', 'hope', 'peace', 'war', 'kill', 'die', 'love', 'hate'],
    'appeal_to_fear': ['fear', 'afraid', 'die', 'kill', 'harm', 'hurt', 'danger', 'threat'],
    'appeal_to_pity': ['pity', 'sorry', 'poor', 'unfortunate', 'mercy', 'help'],
    'slippery_slope': ['if', 'then', 'eventually', 'next', 'soon', 'will', 'would'],
    'false_dilemma': ['either', 'or', 'both', 'neither', 'only', 'black', 'white'],
    'false_authority': ['expert', 'scientist', 'famous', 'well-known', 'says', 'according'],
    'begging_the_question': ['obviously', 'certainly', 'clearly', 'true', 'fact'],
    'strawman': ['actually', 'really', 'doesn\'t', 'isn\'t', 'don\'t'],
    'tu_quoque': ['you', 'too', 'also', 'both', 'same', 'hypocrisy'],
    'false_cause': ['correlation', 'linked', 'connected', 'related', 'because', 'causes'],
    'gamblers_fallacy': ['due', 'overdue', 'chance', 'odds', 'probability', 'luck'],
    'sunk_cost_fallacy': ['already', 'invested', 'spent', 'wasted', 'might as well'],
    'red_herring': ['but', 'however', 'anyway', 'side note', 'by the way'],
    'non_sequitur': ['therefore', 'thus', 'so', 'hence', 'conclusion'],
    'affirming_consequent': ['if', 'then', 'therefore', 'conclusion'],
    'denying_antecedent': ['if', 'not', 'then', 'therefore', 'conclusion'],
    'appeal_to_tradition': ['always', 'tradition', 'historically', 'custom', 'past'],
    'appeal_to_novelty': ['new', 'newest', 'latest', 'modern', 'cutting-edge', 'innovative'],
    'appeal_to_nature': ['natural', 'organic', 'nature', 'earth', 'green'],
    'middle_ground': ['balance', 'compromise', 'middle', 'halfway', 'both'],
    'loaded_question': ['have you', 'are you', 'when did', 'stopped'],
    'no_true_scotsman': ['true', 'real', 'actual', 'genuine', 'authentic'],
    'equivocation': ['depends', 'meaning', 'definition', 'interpret'],
    'special_pleading': ['exception', 'special', 'deserves', 'justify'],
    'moving_goalposts': ['enough', 'more', 'need', 'prove', 'evidence', 'proof'],
    'genetic_fallacy': ['comes from', 'origin', 'source', 'history', 'tradition'],
    'appeal_to_silence': ['no evidence', 'absence', 'nobody', 'silent', 'silent'],
    'ignoratio_elenchi': ['point', 'basically', 'really', 'truth', 'matter'],
    'thought_terminating_cliche': ['end of the day', 'it is what it is', 'what can you do'],
    'prosecutors_fallacy': ['probability', 'chance', 'rare', 'unlikely', 'million'],
    'composition_division': ['all', 'every', 'each', 'whole', 'part'],
    'false_analogy': ['like', 'similar', 'same', ' analogy', 'compare'],
    'formal_fallacy': ['logic', 'reasoning', 'premise', 'conclusion', 'valid'],
}

def extract_keywords_from_patterns():
    """Extract all keyword regexes from FALLACY_PATTERNS."""
    keywords = []
    for pattern_def in FALLACY_PATTERNS:
        pattern = pattern_def['pattern']
        found = re.findall(r'\\b\w+\\?*\b', pattern)
        keywords.extend([w.replace('\\b', '') for w in found])
    return keywords

def count_keywords_in_text(text, keywords):
    """Count keyword occurrences in text."""
    text_lower = text.lower()
    counts = Counter()
    for kw_pattern in KEYWORD_PATTERNS:
        matches = re.findall(kw_pattern, text_lower)
        if matches:
            kw_name = kw_pattern.replace(r'\b', '').replace('\\', '')
            counts[kw_name] += len(matches)
    return counts

def analyze_patterns():
    """Analyze which keywords are most common in fallacy patterns."""
    print("\n" + "="*70)
    print("KEYWORD ANALYSIS FROM FALLACY PATTERNS")
    print("="*70)
    
    keyword_counts = Counter()
    fallacy_keyword_map = defaultdict(list)
    
    for fp in FALLACY_PATTERNS:
        pattern = fp['pattern']
        fallacy_type = fp['type']
        found = re.findall(r"\\b([\w']+)\b", pattern)
        for kw in found:
            if len(kw) > 2 and kw not in ['the', 'and', 'for', 'nor', 'but', 'ore', 'yet', 'so', 'not', 'are']:
                keyword_counts[kw] += 1
                fallacy_keyword_map[fallacy_type].append(kw)
    
    print("\nTop 30 keywords across all patterns:")
    print("-" * 40)
    for kw, count in keyword_counts.most_common(30):
        print(f"  {kw:<20} {count:>5} occurrences")
    
    print("\nKeywords by fallacy type:")
    print("-" * 40)
    for fallacy, kws in sorted(fallacy_keyword_map.items()):
        unique_kws = set(kws)
        print(f"  {fallacy}: {', '.join(sorted(unique_kws)[:10])}")

def analyze_mock_ledger(filepath):
    """Analyze keywords in mock ledger headlines."""
    print("\n" + "="*70)
    print("KEYWORD ANALYSIS FROM MOCK LEDGER HEADLINES")
    print("="*70)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    events = data.get('events', [])
    
    overall_counts = Counter()
    by_fallacy = defaultdict(Counter)
    total_words = 0
    
    for event in events:
        text = event.get('title', '')
        text_lower = text.lower()
        total_words += len(text.split())
        fallacy_types = event.get('fallacy_types', [])
        
        for kw_pattern in KEYWORD_PATTERNS:
            matches = re.findall(kw_pattern, text_lower)
            if matches:
                kw_name = kw_pattern.replace(r'\b', '').replace('\\', '')
                overall_counts[kw_name] += len(matches)
                
                for ft in fallacy_types:
                    by_fallacy[ft][kw_name] += len(matches)
    
    print(f"\nTotal events analyzed: {len(events)}")
    print(f"Total words analyzed: {total_words}")
    print(f"Average words per headline: {total_words/len(events):.1f}")
    
    print("\nTop 30 keywords in fallacious headlines:")
    print("-" * 50)
    for kw, count in overall_counts.most_common(30):
        pct = (count / total_words) * 100 if total_words > 0 else 0
        print(f"  {kw:<18} {count:>6}  ({pct:>5.2f}% of words)")
    
    print("\nTop keywords by fallacy type:")
    print("-" * 50)
    for fallacy in sorted(by_fallacy.keys()):
        counter = by_fallacy[fallacy]
        total_ft = sum(counter.values())
        print(f"\n  [{fallacy}] ({sum(counter.values())} total keywords)")
        for kw, count in counter.most_common(5):
            print(f"    {kw:<18} {count:>4}")

def analyze_specific_keywords():
    """Analyze specific high-signal keywords."""
    print("\n" + "="*70)
    print("HIGH-SIGNAL KEYWORD ANALYSIS")
    print("="*70)
    
    specific_kw = {
        'Universal Quantifiers': [r'\ball\b', r'\bevery\b', r'\beveryone\b', r'\bnobody\b', r'\bno one\b', r'\banybody\b'],
        'Temporal Extremes': [r'\balways\b', r'\bnever\b', r'\bconstantly\b'],
        'Authority Modal': [r'\bshould\b', r'\bmust\b', r'\bneed\b', r'\bhave to\b', r'\bcan\'t\b'],
        'Comparison': [r'\bbetter\b', r'\bbest\b', r'\bworst\b', r'\bmore\b', r'\bmost\b'],
        'Causal Indicators': [r'\bbecause\b', r'\bsince\b', r'\btherefore\b', r'\bthus\b', r'\bif\b', r'\bthen\b'],
        'Uncertainty Markers': [r'\bprobably\b', r'\bmaybe\b', r'\bperhaps\b', r'\bpossibly\b'],
        'Personal Pronouns': [r'\bI\b', r'\byou\b', r'\bwe\b', r'\bthey\b', r'\bmy\b', r'\bour\b'],
        'Truth Claims': [r'\btrue\b', r'\btruth\b', r'\bfact\b', r'\bobviously\b', r'\bcertainly\b'],
    }
    
    print("\nKeyword categories and their patterns:")
    for category, patterns in specific_kw.items():
        print(f"\n  {category}:")
        for p in patterns:
            clean = p.replace('\\b', '').replace('\\', '')
            print(f"    - {clean}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze keywords in fallacy patterns and texts")
    parser.add_argument("--patterns", action="store_true", help="Analyze patterns only")
    parser.add_argument("--ledger", help="Analyze mock ledger file")
    parser.add_argument("--top", type=int, default=30, help="Show top N keywords")
    parser.add_argument("--specific", action="store_true", help="Show specific high-signal keywords")
    args = parser.parse_args()
    
    if args.patterns:
        analyze_patterns()
    elif args.ledger:
        analyze_mock_ledger(args.ledger)
    elif args.specific:
        analyze_specific_keywords()
    else:
        analyze_patterns()
        if Path('mock_ledger.json').exists():
            analyze_mock_ledger('mock_ledger.json')
        analyze_specific_keywords()

if __name__ == "__main__":
    main()