import json
from typing import List, Dict, Any, AsyncIterator, Union
from pathlib import Path
import re

from .fallacy_detector import FallacyDetector

ANTHROPIC_API_KEY = "sk-ant-api03-placeholder"

class LLMAnalyzer:
    SYSTEM_PROMPT = """You are a logical fallacy detector analyzing arguments. For each argument segment, identify any logical fallacies present.

For each fallacy found, return:
- fallacy_type: The specific type (e.g., "strawman", "ad_hominem", "sunk_cost")
- claim_text: The specific text containing the fallacy
- magnitude: 0.0-1.0 (how severe is this fallacy, 1.0 being most severe)
- persistence: 0.0-1.0 (how much does subsequent argument rely on this fallacy)
- parent_fallacy_id: If this fallacy depends on a previous one, reference its index

Return a JSON array of fallacies found. If none, return empty array.
Only identify fallacies you are confident about."""

    FALLACY_PATTERNS = [
        {"pattern": r"\b(flat earth|globe|refrigerator)\b", "type": "false_cause", "magnitude": 0.7, "persistence": 0.5},
        {"pattern": r"\b(you|your)\s+(should|must|have to)\b.*\b(believe me|I am right|trust me)\b", "type": "appeal_to_authority", "magnitude": 0.6, "persistence": 0.6},
        {"pattern": r"\b(you|everyone)\s+(should|must|need to)\b.*\bbecause\s+.*said\s+so\b", "type": "appeal_to_authority", "magnitude": 0.6, "persistence": 0.6},
        {"pattern": r"\b(can't|cannot)\s+(possibly|really)\s+be(lieve|true)\b", "type": "appeal_to_emotion", "magnitude": 0.5, "persistence": 0.4},
        {"pattern": r"\b(either|only|just)\s+(we|you|i|they)\s+(do|have|are)\b.*\bor\b", "type": "false_dilemma", "magnitude": 0.8, "persistence": 0.7},
        {"pattern": r"\bif\s+.*\bthen\s+.*\bwill\s+(also|too|as well)\b", "type": "slippery_slope", "magnitude": 0.7, "persistence": 0.6},
        {"pattern": r"\b(obviously|certainly|clearly|everyone knows)\b.*\b(so|therefore|thus)\b", "type": "begging_the_question", "magnitude": 0.7, "persistence": 0.6},
        {"pattern": r"\bdoesn't\s+(actually|really|truly)\b", "type": "strawman", "magnitude": 0.6, "persistence": 0.5},
    ]

    def __init__(self, api_key: Union[str, None] = None):
        self.client = None
        self.fallacy_detector = FallacyDetector()

    def _build_prompt(self, text: str, context: Union[List[Dict], None] = None) -> str:
        prompt = f"Analyze this text for logical fallacies:\n\n{text}"
        if context:
            prompt += "\n\nPreviously identified fallacies (for cascade tracking):"
            for i, c in enumerate(context):
                prompt += f"\n{i+1}. {c['type']}: {c['text'][:50]}..."
        return prompt

    async def analyze_stream(self, text: str, context: Union[List[Dict], None] = None) -> AsyncIterator[Dict]:
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": self._build_prompt(text, context)
                }],
                system=self.SYSTEM_PROMPT
            )
            
            content = response.content[0].text
            
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                fallacies = json.loads(json_match.group())
                for f in fallacies:
                    info = self.fallacy_detector.get_fallacy_info(f.get('fallacy_type', ''))
                    if info:
                        f['base_weight'] = info.get('base_weight', 0.5)
                        f['visual_form'] = info.get('visual_form', 'well')
                    yield f
                    
        except Exception as e:
            yield {"error": str(e)}

    def _pattern_analyze(self, text: str) -> List[Dict]:
        fallacies = []
        text_lower = text.lower()
        
        for fp in self.FALLACY_PATTERNS:
            if re.search(fp["pattern"], text_lower, re.IGNORECASE):
                info = self.fallacy_detector.get_fallacy_info(fp["type"])
                base_weight = info.get("base_weight", 0.5) if info else 0.5
                
                fallacies.append({
                    "fallacy_type": fp["type"],
                    "claim_text": text,
                    "magnitude": fp["magnitude"],
                    "persistence": fp["persistence"],
                    "base_weight": base_weight,
                    "visual_form": info.get("visual_form", "well") if info else "well"
                })
        
        return fallacies

    def analyze_sync(self, text: str, context: Union[List[Dict], None] = None) -> List[Dict]:
        fallacies = self._pattern_analyze(text)
        
        if not fallacies:
            try:
                import httpx
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1024,
                        "messages": [{
                            "role": "user",
                            "content": self._build_prompt(text, context)
                        }]
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", [{}])[0].get("text", "")
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        fallacies = json.loads(json_match.group())
                        for f in fallacies:
                            info = self.fallacy_detector.get_fallacy_info(f.get('fallacy_type', ''))
                            if info:
                                f['base_weight'] = info.get('base_weight', 0.5)
                                f['visual_form'] = info.get('visual_form', 'well')
            except Exception as e:
                print(f"API fallback error: {e}")
        
        return fallacies