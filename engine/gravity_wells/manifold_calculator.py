import numpy as np
from typing import List, Dict, Tuple, Union
import json

class ManifoldCalculator:
    GRID_SIZE = 64
    GRAVITY_CONSTANT = 2.5
    COHERENCE_THRESHOLD = 1.5

    def __init__(self, grid_size: int = 64):
        self.grid_size = grid_size
        self.vertices = self._create_base_grid()
        self.fallacy_positions: List[Tuple[float, float, float]] = []
        self.fallacy_magnitudes: List[float] = []
        self.fallacy_types: List[str] = []

    def _create_base_grid(self) -> np.ndarray:
        x = np.linspace(-5, 5, self.grid_size)
        y = np.linspace(-5, 5, self.grid_size)
        xx, yy = np.meshgrid(x, y)
        zz = np.zeros_like(xx)
        return np.stack([xx, yy, zz], axis=-1)

    def add_fallacy(self, position: Tuple[float, float, float], magnitude: float, fallacy_type: str):
        self.fallacy_positions.append(position)
        self.fallacy_magnitudes.append(magnitude)
        self.fallacy_types.append(fallacy_type)

    def remove_fallacy(self, index: int):
        if index < len(self.fallacy_positions):
            self.fallacy_positions.pop(index)
            self.fallacy_magnitudes.pop(index)
            self.fallacy_types.pop(index)

    def clear_fallacies(self):
        self.fallacy_positions = []
        self.fallacy_magnitudes = []
        self.fallacy_types = []

    def calculate_displacement(self, vertex: np.ndarray, fallacy_idx: int) -> float:
        fx, fy, fz = self.fallacy_positions[fallacy_idx]
        vx, vy, vz = vertex
        
        distance = np.sqrt((vx - fx)**2 + (vy - fy)**2)
        if distance < 0.1:
            distance = 0.1
            
        magnitude = self.fallacy_magnitudes[fallacy_idx]
        fall_type = self.fallacy_types[fallacy_idx]
        
        displacement = (magnitude * self.GRAVITY_CONSTANT) / (distance ** 2)
        
        if fall_type in ['peak', 'hyperbole', 'strawman']:
            return displacement
        elif fall_type in ['fracture', 'non_sequitur', 'equivocation']:
            return -displacement * 0.5
        else:
            return -displacement

    def calculate_vertex(self, vertex: np.ndarray) -> Tuple[float, float, float, bool]:
        total_displacement = 0.0
        
        for i in range(len(self.fallacy_positions)):
            disp = self.calculate_displacement(vertex, i)
            total_displacement += disp
        
        is_tearing = abs(total_displacement) > self.COHERENCE_THRESHOLD
        
        return (vertex[0], vertex[1], max(-3, min(3, total_displacement)), is_tearing)

    def calculate_mesh(self) -> Dict:
        result = np.zeros_like(self.vertices)
        tearing_mask = np.zeros((self.grid_size, self.grid_size), dtype=bool)
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                v = self.vertices[i, j]
                x: float
                y: float
                z: float
                tearing: bool
                x, y, z, tearing = self.calculate_vertex(v)
                result[i, j] = [x, y, z]
                tearing_mask[i, j] = tearing
        
        return {
            "vertices": result.tolist(),
            "grid_size": self.grid_size,
            "tearing_mask": tearing_mask.tolist()
        }

    def get_heatmap_values(self) -> List[List[float]]:
        heatmap = np.zeros((self.grid_size, self.grid_size))
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                vertex = self.vertices[i, j]
                total_intensity = 0.0
                for k in range(len(self.fallacy_positions)):
                    fx, fy, fz = self.fallacy_positions[k]
                    vx, vy, vz = vertex
                    distance = np.sqrt((vx - fx)**2 + (vy - fy)**2) + 0.1
                    intensity = self.fallacy_magnitudes[k] / (distance ** 2)
                    total_intensity += intensity
                heatmap[i, j] = min(1.0, total_intensity)
        
        return heatmap.tolist()

    def get_center_glow(self, V_active: float) -> float:
        return max(0, min(1, V_active))

    def calculate_snapshot(self) -> str:
        mesh_data = self.calculate_mesh()
        return json.dumps(mesh_data)