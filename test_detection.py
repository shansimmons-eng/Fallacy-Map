#!/usr/bin/env python3
"""
Test script to verify the multi-layer detection is working.
"""
import sys
sys.path.insert(0, '.')

from server import SemanticScrubber, VERACITY_CONSTANT

scrubber = SemanticScrubber()

test_cases = [
    ("All women are bad drivers.", ["hasty_generalization"]),
    ("I met one tall man who loved cheese. Now all tall people like cheese.", ["hasty_generalization"]),
    ("Either we act now or we face total collapse.", ["false_dilemma"]),
    ("If we allow this, then bad things will happen, and then worse things, and then disaster.", ["slippery_slope"]),
    ("God exists because the Bible says so, and the Bible is true because it is the word of God.", ["circular_reasoning"]),
    ("You should trust this because everyone knows the truth.", ["begging_the_question", "bandwagon"]),
    ("Don't listen to him - he's just a dumb actor!", ["ad_hominem"]),
    ("Think of the children who will suffer if we don't act!", ["appeal_to_emotion"]),
    ("Everyone is doing it, so you should too!", ["bandwagon"]),
    ("The rooster crows before sunrise, therefore the rooster causes the sun to rise.", ["post_hoc"]),
]

print("=" * 70)
print("MULTI-LAYER FALLACY DETECTION TEST")
print("=" * 70)
print(f"Veracity Constant: {VERACITY_CONSTANT}")
print()

for text, expected_types in test_cases:
    fallacies = scrubber.analyze(text)
    detected_types = [f.type for f in fallacies]
    total_cost = sum(f.magnitude * f.persistence for f in fallacies)
    veracity = max(0.0, VERACITY_CONSTANT - total_cost)
    
    match = "✓" if any(et in detected_types for et in expected_types) else "✗"
    
    print(f"{match} \"{text[:50]}...\"")
    print(f"   Detected: {detected_types}")
    print(f"   Depth breakdown: {[f.depth for f in fallacies]}")
    print(f"   Veracity: {veracity:.2f} (decay: {total_cost:.2f})")
    print()

print("=" * 70)
print("LAYER STATISTICS")
print("=" * 70)

layer_names = {0: "Regex", 1: "Template", 2: "N-gram", 3: "Quantifier", 4: "Sentiment", 5: "Discourse"}
for layer_id, layer_name in layer_names.items():
    count = sum(1 for text, _ in test_cases for f in scrubber.analyze(text) if f.depth == layer_id)
    print(f"  Layer {layer_id} ({layer_name}): {count} detections")