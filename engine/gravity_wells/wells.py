"""
Gravity Wells: Inverse Square Displacement Engine
Implements the Inverion Protocol for manifold deformation.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np

@dataclass
class FallacyWell:
    """
    Represents a fallacy as a gravity well on the manifold.
    Uses Inverse Square law: displacement = magnitude / distance²
    """
    fallacy_type: str
    position: Tuple[float, float, float]
    magnitude: float
    persistence: float
    depth: int = 0
    parent_id: Optional[str] = None
    
    G_CONSTANT: float = 1.0
    COHERENCE_THRESHOLD: float = 1.5
    RADIUS_BASE: float = 3.0
    
    @property
    def radius(self) -> float:
        """Calculate influence radius based on magnitude."""
        return self.RADIUS_BASE * (1 - self.magnitude) + 0.5
    
    def calculate_displacement(self, target_pos: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Calculate displacement vector using Inverse Square law.
        Returns (dx, dy, dz) displacement.
        """
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]
        dz = target_pos[2] - self.position[2]
        
        distance_sq = dx * dx + dy * dy + dz * dz
        distance = math.sqrt(distance_sq)
        
        if distance < 0.001:
            return (0, 0, 0)
        
        inverse_square = self.magnitude * self.G_CONSTANT / distance_sq
        
        displacement = (
            -dx * inverse_square,
            -dy * inverse_square,  
            -dz * inverse_square
        )
        
        return displacement
    
    def get_z_offset(self, distance: float) -> float:
        """
        Get vertical (z-axis) offset.
        Negative for wells (pulling down), positive for peaks.
        """
        if distance < 0.001:
            return -self.magnitude * self.G_CONSTANT * 10
        
        return -(self.magnitude * self.G_CONSTANT) / (distance * distance)


class GravityWellRegistry:
    """
    Registry of all active gravity wells on the manifold.
    Handles superposition of multiple wells.
    """
    
    def __init__(self, max_wells: int = 50):
        self.wells: List[FallacyWell] = []
        self.max_wells = max_wells
        self._vertex_displacements: Optional[np.ndarray] = None
        
    def add_well(self, well: FallacyWell) -> None:
        """Register a new gravity well."""
        if len(self.wells) >= self.max_wells:
            oldest = self.wells.pop(0)
            print(f"GravityWellRegistry: Removed oldest well {oldest.fallacy_type} to make room")
        
        self.wells.append(well)
        self._vertex_displacements = None
    
    def remove_well(self, well_id: str) -> None:
        """Remove a gravity well by position identifier."""
        self.wells = [w for w in self.wells if w.position != well_id]
        self._vertex_displacements = None
    
    def clear(self) -> None:
        """Clear all gravity wells."""
        self.wells.clear()
        self._vertex_displacements = None
    
    def calculate_superposition(
        self, 
        vertex_positions: np.ndarray
    ) -> np.ndarray:
        """
        Calculate total displacement for all vertices from all wells.
        Uses superposition: total = Σ individual_well_displacement
        
        Args:
            vertex_positions: numpy array of shape (N, 3) with vertex coordinates
            
        Returns:
            numpy array of shape (N, 3) with total displacement vectors
        """
        n_vertices = vertex_positions.shape[0]
        total_displacement = np.zeros((n_vertices, 3), dtype=np.float32)
        
        for well in self.wells:
            for i in range(n_vertices):
                pos = tuple(vertex_positions[i])
                disp = well.calculate_displacement(pos)
                total_displacement[i] += disp
        
        return total_displacement
    
    def calculate_vertical_offset(
        self,
        vertex_positions: np.ndarray,
        vertex_count: int
    ) -> np.ndarray:
        """
        Calculate vertical (Z-axis) offsets for all vertices.
        Used for heat map coloring and deformation visualization.
        
        Args:
            vertex_positions: numpy array of shape (N, 3)
            vertex_count: total number of vertices in mesh
            
        Returns:
            numpy array of shape (N,) with Z offsets
        """
        z_offsets = np.zeros(vertex_count, dtype=np.float32)
        
        for well in self.wells:
            for i in range(vertex_count):
                pos = tuple(vertex_positions[i])
                
                dx = pos[0] - well.position[0]
                dy = pos[1] - well.position[1]
                dz = pos[2] - well.position[2]
                
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                z_offsets[i] += well.get_z_offset(distance)
        
        return z_offsets
    
    def check_tearing(self, total_displacement: np.ndarray, threshold: float = 1.5) -> bool:
        """
        Check if total displacement exceeds mesh coherence threshold.
        Returns True if tearing should occur.
        """
        magnitudes = np.linalg.norm(total_displacement, axis=1)
        max_displacement = np.max(magnitudes)
        
        return max_displacement > threshold
    
    def get_wells_by_depth(self, max_depth: int) -> List[FallacyWell]:
        """Get all wells up to specified cascade depth."""
        return [w for w in self.wells if w.depth <= max_depth]


class ManifoldDeformer:
    """
    High-performance manifold deformation engine.
    Uses Float32Arrays for GPU-compatible calculations.
    """
    
    def __init__(self, mesh_resolution: int = 64):
        self.resolution = mesh_resolution
        self.vertex_count = mesh_resolution * mesh_resolution
        
        self._positions: Optional[np.ndarray] = None
        self._base_heights: Optional[np.ndarray] = None
        self._displacements: Optional[np.ndarray] = None
        self._registry = GravityWellRegistry()
        
    def initialize_mesh(self, size: float = 10.0) -> None:
        """
        Initialize the deformable mesh.
        
        Args:
            size: Total size of mesh in world units
        """
        positions = np.zeros((self.vertex_count, 3), dtype=np.float32)
        base_heights = np.zeros(self.vertex_count, dtype=np.float32)
        
        step = size / (self.resolution - 1)
        half = size / 2
        
        idx = 0
        for z in range(self.resolution):
            for x in range(self.resolution):
                positions[idx] = [
                    x * step - half,
                    0,
                    z * step - half
                ]
                base_heights[idx] = 0
                idx += 1
        
        self._positions = positions
        self._base_heights = base_heights
        self._displacements = np.zeros(self.vertex_count, dtype=np.float32)
        
    def add_fallacy(
        self,
        fallacy_type: str,
        position: Tuple[float, float, float],
        magnitude: float,
        persistence: float,
        depth: int = 0,
        parent_id: Optional[str] = None
    ) -> FallacyWell:
        """
        Add a fallacy gravity well to the manifold.
        
        Args:
            fallacy_type: Type of fallacy (e.g., 'ad_hominem', 'strawman')
            position: (x, y, z) world position
            magnitude: 0.0-1.0 severity
            persistence: 0.0-1.0 how much subsequent logic relies on it
            depth: cascade depth from root
            parent_id: parent fallacy ID for cascade tracking
            
        Returns:
            Created FallacyWell instance
        """
        well = FallacyWell(
            fallacy_type=fallacy_type,
            position=position,
            magnitude=magnitude,
            persistence=persistence,
            depth=depth,
            parent_id=parent_id
        )
        
        self._registry.add_well(well)
        self._recalculate_displacements()
        
        return well
    
    def _recalculate_displacements(self) -> None:
        """Recalculate all vertex displacements from registered wells."""
        if self._positions is None:
            return
            
        self._displacements = self._registry.calculate_vertical_offset(
            self._positions,
            self.vertex_count
        )
    
    def get_vertex_data(self) -> np.ndarray:
        """
        Get current vertex positions as Float32Array.
        Compatible with Three.js BufferGeometry.
        
        Returns:
            numpy array of shape (N, 3) with world positions
        """
        if self._positions is None or self._base_heights is None:
            return np.zeros((self.vertex_count, 3), dtype=np.float32)
            
        result = self._positions.copy()
        result[:, 1] = self._base_heights + self._displacements
        
        return result
    
    def get_heatmap_values(self) -> np.ndarray:
        """
        Get heat map values for shader coloring.
        Returns normalized 0-1 values based on displacement magnitude.
        """
        if self._displacements is None:
            return np.zeros(self.vertex_count, dtype=np.float32)
            
        normalized = np.abs(self._displacements)
        max_val = np.max(normalized) if np.max(normalized) > 0 else 1
        
        return normalized / max_val
    
    def check_collapse_imminent(self) -> bool:
        """Check if deformation indicates imminent structural collapse."""
        return self._registry.check_tearing(
            np.column_stack([
                np.zeros(self.vertex_count),
                self._displacements,
                np.zeros(self.vertex_count)
            ])
        )
    
    @property
    def registry(self) -> GravityWellRegistry:
        """Access the gravity well registry."""
        return self._registry