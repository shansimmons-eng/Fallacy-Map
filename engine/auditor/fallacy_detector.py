import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

class FallacyDetector:
    def __init__(self, taxonomy_path: Union[str, None] = None):
        if taxonomy_path is None:
            taxonomy_path = str(Path(__file__).parent.parent.parent / "fallacy_taxonomy.json")
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.fallacies: Dict[str, Dict] = {f['name']: f for f in data['fallacies']}
        self.categories = set(f['category'] for f in data['fallacies'])

    def get_fallacy_info(self, fallacy_name: str) -> Optional[Dict]:
        key = fallacy_name.lower().replace(' ', '_')
        return self.fallacies.get(key)

    def calculate_v_cost(self, fallacy_name: str, magnitude: float, persistence: float) -> float:
        info = self.get_fallacy_info(fallacy_name)
        if info:
            base_weight: float = info.get('base_weight', 0.5)
            return magnitude * persistence * base_weight
        return magnitude * persistence

    def get_visual_form(self, fallacy_name: str) -> str:
        info = self.get_fallacy_info(fallacy_name)
        if info:
            form: str = info.get('visual_form', 'well')
            return form
        return 'well'

    def list_fallacies(self, category: Union[str, None] = None) -> List[Dict]:
        if category:
            return [f for f in self.fallacies.values() if f['category'] == category]
        return list(self.fallacies.values())

    def get_categories(self) -> List[str]:
        return list(self.categories)