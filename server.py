#!/usr/bin/env python3
"""
Inverion Semantic Bridge — The Sovereign Scrubber

This module processes raw text into fallacy telemetry for the Sunrise manifold.
It acts as the bridge between input sources and the 3D visualization engine.

Usage:
    uv run server.py

The server outputs JSON telemetry to stdout for stitching with the frontend.
"""

import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Logic Constants: The Inverion Thresholds
VERACITY_CONSTANT = 1.0
BYPASS_THRESHOLD = 0.5
LOCKOUT_THRESHOLD = 0.1
SHUTDOWN_THRESHOLD = 0.0


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