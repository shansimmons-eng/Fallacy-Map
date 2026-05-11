# The Fallacy Map — Design Document

## Concept

The Fallacy Map transforms argument analysis into navigable topography. Sound logic forms a flat, stable plane; fallacies become gravity wells, peaks, and fractures that distort the surface.

## Design Principles

### Dark Void Aesthetic
- Deep black void background (`#0a0a0f`) representing pure logical space
- Healthy logic glows cool cyan (`#00f5d4`)
- Fallacies pulse in thermal gradients (amber → red → crimson as severity increases)

### Typography
- Primary: JetBrains Mono (monospace for technical precision)
- Headings: Space Grotesk (geometric, modern)
- Fallback: system-ui, sans-serif

### Motion Philosophy
- Manifold deformation: Spring physics with damping 0.85, stiffness 120
- Fallacy pulses: Sine-wave opacity oscillation, 2s cycle, amplitude 0.3–1.0
- Node hover: Scale 1.0 → 1.15, 150ms ease-out
- Edge propagation: Animated dash pattern flowing toward false conclusions
- Camera: Smooth damped follow with 0.08 lerp factor

## Visual States

| V_active Range | State | Manifold Color | Center Glow |
|---------------|-------|---------------|------------|
| > 0.8 | Ignition | Cyan `#00f5d4` | White-hot ignition |
| 0.5–0.8 | Healthy | Teal → Amber | Dim amber |
| 0.2–0.5 | Stressed | Orange `#f97316` | Pulsing red |
| 0.0–0.2 | Critical | Deep red `#ef4444` | Fast pulse crimson |
| ≤ 0.0 | DIVIDE | Static/corruption | None (frozen) |

## Component Architecture

### ManifoldCanvas
- Three.js + React Three Fiber rendering
- Custom GLSL shaders for heat mapping and corruption texture
- 64×64 vertex deformable mesh
- GPU-based gravity calculations

### ClaimNode
- Individual claims rendered as 3D nodes
- Hover state with scale animation
- Color coding by veracity state

### VeracityMeter
- Real-time V_active gauge
- State indicator (Healthy/Stressed/Critical/Divide)
- Pulsing warning animation in critical states

### InverionDivideOverlay
- Full-screen diagnostic overlay when Inverion Divide triggers
- Root fallacy identification and causal chain display
- Corruption texture visualization

## API Design

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/arguments` | Create new argument |
| GET | `/arguments/{id}` | Get argument with claims/fallacies |
| POST | `/analyze` | Analyze text chunk for fallacies |
| GET | `/veracity/{id}` | Get current veracity state |
| GET | `/snapshots/{id}` | Get argument snapshots for playback |
| WS | `/ws/{id}` | WebSocket for real-time updates |

### Data Models

```python
Argument:
  id: str (UUID)
  title: str
  source_text: str
  V_active: float (0.0-1.0)
  V_initial: float (1.0)
  inverion_triggered: bool
  root_fallacy_id: str | None
  bypass_count: int
  collapse_timestamp: datetime | None

Claim:
  id: str (UUID)
  argument_id: str
  text: str
  position_x, y, z: float
  is_conclusion: bool

Fallacy:
  id: str (UUID)
  claim_id: str
  fallacy_type: str
  magnitude: float (0.0-1.0)
  persistence: float (0.0-1.0)
  parent_fallacy_id: str | None
  depth: int
```

## Veracity Calculation

```
V_cost = Magnitude × Persistence × Base_Weight
V_active = V_initial - Σ(V_cost for all detected fallacies)
```

## Fallacy Patterns

| Pattern | Type | Default Magnitude |
|---------|------|------------------|
| `you should believe me because I am always right` | appeal_to_authority | 0.6 |
| `either...or` | false_dilemma | 0.8 |
| `if...then...will happen` | slippery_slope | 0.7 |
| `obviously...therefore` | begging_the_question | 0.7 |

## Security Considerations

- API key stored in environment variable `ANTHROPIC_API_KEY`
- CORS configured for frontend origin
- Input validation on all endpoints
- SQLite database stored in user home directory (`~/.fallacy_map/`)

## Performance Targets

- 60 FPS with up to 50 simultaneous fallacies
- GPU-based vertex displacement via custom shaders
- CPU handles only fallacy addition/removal, not per-frame physics
- Throttle mesh updates to 30fps during streaming input