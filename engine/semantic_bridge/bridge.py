"""
Semantic-to-Spatial Bridge
Maps LLM JSON output directly to manifold vertex displacement.
Implements the Inverion Protocol for semantic → spatial translation.
"""

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class FallacyCategory(Enum):
    """Fallacy categories mapped to visual forms."""
    RELEVANCE = "well"      # Ad Hominem, Strawman - Deep wells
    CREDIBILITY = "peak"   # Appeal to Authority - Elevated peaks
    CAUSATION = "chain"    # Slippery Slope, Sunk Cost - Descending chains
    LOGIC = "loop"         # Circular Reasoning - Recursive loops
    UNKNOWN = "fracture"   # Non Sequitur - Mesh fractures


@dataclass
class SemanticNode:
    """
    Represents a claim/fallacy as a semantic node.
    Maps to spatial coordinates on the manifold.
    """
    id: str
    text: str
    fallacy_type: Optional[str]
    magnitude: float
    persistence: float
    position: Tuple[float, float, float]
    temporal_index: int = 0
    
    @classmethod
    def from_llm(cls, llm_output: Dict[str, Any], index: int) -> 'SemanticNode':
        """Create SemanticNode from LLM analyzer JSON output."""
        pos = cls._calculate_position(
            llm_output.get('fallacy_type', 'unknown'),
            index,
            llm_output.get('magnitude', 0.5)
        )
        
        return cls(
            id=hashlib.md5(llm_output.get('claim_text', '').encode()).hexdigest()[:12],
            text=llm_output.get('claim_text', ''),
            fallacy_type=llm_output.get('fallacy_type'),
            magnitude=llm_output.get('magnitude', 0.5),
            persistence=llm_output.get('persistence', 0.5),
            position=pos,
            temporal_index=index
        )
    
    @staticmethod
    def _calculate_position(
        fallacy_type: str, 
        temporal_index: int, 
        magnitude: float
    ) -> Tuple[float, float, float]:
        """
        Calculate 3D position from semantic properties.
        
        X-Axis: Temporal flow (temporal_index * spacing)
        Y-Axis: Relationship density (based on persistence)
        Z-Axis: Gravity depth (based on magnitude)
        """
        x_spacing = 2.0
        y_base = 0.0
        z_base = 0.0
        
        x = temporal_index * x_spacing
        
        y = magnitude * 2.0
        
        z = -magnitude * 3.0
        
        return (x, y, z)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ManifoldUpdate:
    """
    A manifold update command from semantic analysis.
    Contains all data needed to deform the 3D mesh.
    """
    nodes: List[SemanticNode]
    V_active: float
    V_cost: float
    bypass_triggered: bool
    inverion_triggered: bool
    timestamp: float
    root_fallacy_id: Optional[str] = None
    
    def to_manifold_command(self) -> Dict[str, Any]:
        """Convert to manifold engine command format."""
        return {
            "type": "manifold_update",
            "V_active": self.V_active,
            "bypass_triggered": self.bypass_triggered,
            "inverion_triggered": self.inverion_triggered,
            "nodes": [
                {
                    "id": n.id,
                    "position": n.position,
                    "fallacy_type": n.fallacy_type,
                    "magnitude": n.magnitude,
                    "persistence": n.persistence
                }
                for n in self.nodes
            ],
            "timestamp": self.timestamp
        }


class SemanticBridge:
    """
    Bridge between LLM semantic analysis and spatial manifold.
    
    Transforms JSON fallacy analysis into:
    1. Semantic nodes with temporal/spatial positions
    2. Manifold update commands for deformation
    3. Veracity audit records for sovereign ledger
    """
    
    def __init__(self, manifold_deformer=None):
        self.manifold_deformer = manifold_deformer
        self.nodes: List[SemanticNode] = []
        self._temporal_counter = 0
        
    def process_llm_output(
        self, 
        llm_json: List[Dict[str, Any]], 
        V_active: float,
        V_cost: float = 0,
        bypass_triggered: bool = False
    ) -> ManifoldUpdate:
        """
        Process raw LLM JSON output into manifold update.
        
        Args:
            llm_json: List of fallacy objects from LLM analyzer
            V_active: Current veracity score
            V_cost: Cost of this analysis tick
            bypass_triggered: Whether bypass was detected
            
        Returns:
            ManifoldUpdate ready for 3D engine consumption
        """
        nodes = []
        root_id = None
        inverion_triggered = V_active <= 0
        
        for i, fallacy_data in enumerate(llm_json):
            if "error" in fallacy_data:
                continue
                
            node = SemanticNode.from_llm(fallacy_data, self._temporal_counter)
            nodes.append(node)
            
            if i == 0 and inverion_triggered and not root_id:
                root_id = node.id
                
            self._temporal_counter += 1
        
        self.nodes.extend(nodes)
        
        return ManifoldUpdate(
            nodes=nodes,
            V_active=V_active,
            V_cost=V_cost,
            bypass_triggered=bypass_triggered,
            inverion_triggered=inverion_triggered,
            timestamp=0,
            root_fallacy_id=root_id
        )
    
    def apply_to_manifold(self, update: ManifoldUpdate) -> None:
        """
        Apply manifold update to the 3D deformer.
        
        Args:
            update: ManifoldUpdate from process_llm_output
        """
        if self.manifold_deformer is None:
            return
            
        for node in update.nodes:
            if node.fallacy_type:
                self.manifold_deformer.add_fallacy(
                    fallacy_type=node.fallacy_type,
                    position=node.position,
                    magnitude=node.magnitude,
                    persistence=node.persistence,
                    depth=0,
                    parent_id=None
                )
    
    def get_category_for_fallacy(self, fallacy_type: str) -> FallacyCategory:
        """Map fallacy type to visual category."""
        category_map = {
            'ad_hominem': FallacyCategory.RELEVANCE,
            'strawman': FallacyCategory.RELEVANCE,
            'false_dilemma': FallacyCategory.RELEVANCE,
            'appeal_to_authority': FallacyCategory.CREDIBILITY,
            'sunk_cost': FallacyCategory.CAUSATION,
            'slippery_slope': FallacyCategory.CAUSATION,
            'begging_the_question': FallacyCategory.LOGIC,
            'circular_reasoning': FallacyCategory.LOGIC,
            'non_sequitur': FallacyCategory.UNKNOWN,
        }
        
        return category_map.get(
            fallacy_type.lower().replace(' ', '_'),
            FallacyCategory.UNKNOWN
        )
    
    def export_topology(self, filepath: str = "data/topology/topology.json") -> None:
        """Export current semantic topology to JSON."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        topology = {
            "export_timestamp": 0,
            "node_count": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes],
            "temporal_span": self._temporal_counter
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(topology, f, indent=2)
    
    def reset(self) -> None:
        """Reset bridge state for new analysis session."""
        self.nodes.clear()
        self._temporal_counter = 0
        
        if self.manifold_deformer:
            self.manifold_deformer.registry.clear()