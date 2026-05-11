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

## The Sunrise Color-Ramp Logic

The **Inverion Sunrise Theme** maps Veracity Depth to a specific solar spectrum. The manifold's core represents "Ignition"—the moment of clarity—and shifts through sunrise colors as logic deforms into fallacy gravity wells.

### Color Ramp Table

| State | Distance to Origin | Hex Color | Visual Meaning |
|-------|-------------------|-----------|----------------|
| **Ignition** | 0.0 - 0.2 | `#FFFFFF` | Blinding white-hot clarity; objective truth |
| **Stable** | 0.2 - 1.5 | `#FFF9C4` → `#FFD54F` | Morning yellow; sound reasoning |
| **Distorted** | 1.5 - 4.0 | `#FF8F00` → `#E65100` | Golden hour amber; fallacy detected |
| **Void** | 4.0+ | `#4E342E` → `#212121` | Deep shadow; logic collapse |
| **Eclipse (Lockout)** | Gate Closed | `#880E4F` / `#000000` | Total structural failure; pre-dawn indigo |

### The Sunrise Gradient

```
#FFFFFF (Ignition)
    ↓ (distance 0.0-0.2)
#FFF9C4 (Pale Goldenrod)
    ↓ (distance 0.2-1.5)
#FFD54F (Morning Amber)
    ↓ (distance 1.5-4.0)
#FF8F00 (Vibrant Orange)
    ↓ (distance 4.0+)
#E65100 (Deep Burnt Orange)
    ↓
#4E342E (Shadow Brown)
    ↓
#212121 (Deep Void)
    ↓ (V_active < 0.1)
#880E4F (Eclipse Crimson)
    ↓
#000000 (Total Eclipse)
```

### Implementation (GLSL)

```glsl
// Sunrise Color Ramp - lerp based on distanceToOrigin
vec3 sunriseColorRamp(float distance) {
    if (distance < 0.2) {
        return vec3(1.0, 1.0, 1.0);  // #FFFFFF - Blinding Ignition
    } else if (distance < 1.5) {
        float t = (distance - 0.2) / 1.3;
        return mix(vec3(1.0, 0.98, 0.77), vec3(1.0, 0.84, 0.31), t);  // #FFF9C4 → #FFD54F
    } else if (distance < 4.0) {
        float t = (distance - 1.5) / 2.5;
        return mix(vec3(1.0, 0.56, 0.0), vec3(0.9, 0.32, 0.0), t);  // #FF8F00 → #E65100
    } else if (distance < 8.0) {
        float t = (distance - 4.0) / 4.0;
        return mix(vec3(0.9, 0.32, 0.0), vec3(0.26, 0.2, 0.18), t);  // #E65100 → #4E342E
    } else {
        float t = clamp((distance - 8.0) / 4.0, 0.0, 1.0);
        return mix(vec3(0.26, 0.2, 0.18), vec3(0.13, 0.13, 0.13), t);  // #4E342E → #212121
    }
}
```

### Shader Requirements

- **Tone Mapping:** `THREE.NoToneMapping` — Required for HDR Ignition breakthrough
- **Blending:** `THREE.AdditiveBlending` — Creates bloom effect at core
- **Intensity Overdrive:** R, G, B values can exceed 1.0 for Ignition (white-hot effect)

### Veracity Meter States

| State | V_active | Sunrise Color | Animation |
|-------|---------|--------------|----------|
| Ignition | > 0.8 | `#FFFFFF` | Soft pulse/bloom |
| Morning | 0.6-0.8 | `#FFF9C4` → `#FFD54F` | Stable glow |
| Distorted | 0.3-0.6 | `#FF8F00` | Faster pulse |
| Critical | 0.1-0.3 | `#E65100` | Rapid crimson pulse |
| Eclipse | ≤ 0.1 | `#880E4F` / `#000000` | **LOCKOUT** - All animations freeze |

## Visual States (Legacy Reference)

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