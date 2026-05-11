# The Fallacy Map — Technical Specification

## 1. Concept & Vision

The Fallacy Map transforms argument analysis into navigable topography. Sound logic forms a flat, stable plane; fallacies become gravity wells, peaks, and fractures that distort the surface. Critical thinkers explore the "geography of deception" — not reading definitions, but *feeling* where an argument collapses.

The experience should feel like a planetary gravity simulation: hover over a Strawman and watch the surrounding claims spiral inward. The map doesn't just label fallacies — it makes their *influence* visible and visceral.

---

## 2. Design Language

**Aesthetic Direction:** Dark void aesthetic — like a topographical map viewed from orbit at night. Arguments float in a black void; healthy logic glows cool cyan; fallacies pulse in thermal gradients (amber → red → crimson as severity increases).

**Color Palette:**
- Background: `#0a0a0f` (deep void)
- Healthy Logic: `#00f5d4` (cyan/teal stable)
- Low Severity: `#fee440` (amber)
- Medium Severity: `#f97316` (orange)
- High Severity: `#ef4444` (red)
- Critical: `#dc2626` (crimson with pulse animation)
- Claims (nodes): `#e2e8f0` (silver white)
- Edges: `#475569` (muted slate), brightening to `#94a3b8` when active
- UI Accent: `#8b5cf6` (violet for selections/focus)

**Typography:**
- Primary: `JetBrains Mono` (monospace for technical precision)
- Headings: `Space Grotesk` (geometric, modern)
- Fallback: `system-ui, sans-serif`

**Motion Philosophy:**
- Manifold deformation: Spring physics with damping `0.85`, stiffness `120`
- Fallacy pulses: Sine-wave opacity oscillation, 2s cycle, amplitude 0.3–1.0
- Node hover: Scale 1.0 → 1.15, 150ms ease-out
- Edge propagation: Animated dash pattern flowing toward false conclusions
- Camera: Smooth damped follow with 0.08 lerp factor

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   React +    │  │   Three.js /    │  │   State Manager     │  │
│  │   TypeScript │  │   WebGL Canvas  │  │   (Zustand)         │  │
│  └──────────────┘  └─────────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket / Streaming
┌────────────────────────────▼────────────────────────────────────┐
│                        BACKEND                                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   FastAPI    │  │   LLM Gateway   │  │   Graph Engine      │  │
│  │   (Python)   │  │   (Anthropic)   │  │   (NetworkX)        │  │
│  └──────────────┘  └─────────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                        STORAGE                                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   SQLite     │  │   Vector Store  │  │   File Archive      │  │
│  │   (Claims)   │  │   (FAISS)       │  │   (S3/Local)        │  │
│  └──────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Schema

### 4.1 Core Entities

```sql
-- Arguments are the top-level container
CREATE TABLE arguments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    V_active REAL DEFAULT 1.0,          -- Current Veracity (0.0 to 1.0)
    V_initial REAL DEFAULT 1.0,        -- Starting Veracity Constant
    inverion_triggered BOOLEAN DEFAULT FALSE,
    root_fallacy_id TEXT,              -- Fallacy that caused collapse
    bypass_count INTEGER DEFAULT 0,    -- Number of bypass events
    bypass_lockout_until TIMESTAMP,   -- When bypass lockout expires
    collapse_timestamp TIMESTAMP       -- When Inverion Divide was triggered
);

-- Veracity Event Log for playback and auditing
CREATE TABLE veracity_events (
    id TEXT PRIMARY KEY,
    argument_id TEXT REFERENCES arguments(id),
    tick_index INTEGER,                -- Sequence number for playback
    V_before REAL,
    V_after REAL,
    V_cost REAL,
    fallacy_id TEXT REFERENCES fallacies(id),
    event_type TEXT,                   -- 'fallacy', 'bypass', 'divide', 'reset'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claims are nodes in the argument graph
CREATE TABLE claims (
    id TEXT PRIMARY KEY,
    argument_id TEXT REFERENCES arguments(id),
    text TEXT NOT NULL,
    position_x REAL,
    position_y REAL,
    position_z REAL,
    is_conclusion BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fallacies are distortions with physics properties
CREATE TABLE fallacies (
    id TEXT PRIMARY KEY,
    claim_id TEXT REFERENCES claims(id),
    fallacy_type TEXT NOT NULL,  -- e.g., 'strawman', 'ad_hominem'
    magnitude REAL DEFAULT 0.5,  -- 0.0 to 1.0, severity
    persistence REAL DEFAULT 0.5, -- how much subsequent logic relies on it
    parent_fallacy_id TEXT REFERENCES fallacies(id),  -- root cause tracking
    depth INTEGER DEFAULT 0,      -- cascade depth from root
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logical edges between claims
CREATE TABLE claim_edges (
    id TEXT PRIMARY KEY,
    argument_id TEXT REFERENCES arguments(id),
    source_claim_id TEXT REFERENCES claims(id),
    target_claim_id TEXT REFERENCES claims(id),
    logical_strength REAL DEFAULT 1.0  -- weakened by connected fallacies
);

-- The 50+ fallacy taxonomy with physics properties
CREATE TABLE fallacy_types (
    name TEXT PRIMARY KEY,
    category TEXT,        -- 'relevance', 'credibility', 'causation', etc.
    base_weight REAL,     -- base gravitational influence
    visual_form TEXT,     -- 'well', 'peak', 'fracture'
    description TEXT
);
```

### 4.2 Fallacy Taxonomy (Abbreviated — Full in Appendix A)

| Fallacy | Category | Base Weight | Visual Form |
|---------|----------|-------------|-------------|
| Ad Hominem | Credibility | 0.9 | Deep Well |
| Strawman | Relevance | 0.85 | Peak |
| False Dilemma | Relevance | 0.9 | Twin Wells |
| Slippery Slope | Causation | 0.7 | Descending Chain |
| Sunk Cost | Causation | 0.6 | Gravity Well |
| Moving the Goalposts | Credibility | 0.75 | Shifting Well |
| Circular Reasoning | Logic | 0.8 | Recursive Loop |
| Non Sequitur | Logic | 0.85 | Fracture |
| Appeal to Authority | Credibility | 0.4 | Shallow Well |
| Hasty Generalization | Causation | 0.5 | Surface Ripple |

---

## 5. The Manifold Rendering System

### 5.1 Mesh Structure

The manifold is a deformable triangular mesh:
- Base resolution: 64×64 vertices (4096 triangles)
- Each vertex has a base height (from argument structure) + dynamic offset (from fallacy gravity)
- Mesh uses BufferGeometry with custom ShaderMaterial for heat mapping
- **Center ignition glow:** Shader samples distance from mesh center; healthy state ($V_{active} > 0.8$) creates white-hot glow that dims as veracity depletes

### 5.2 Veracity-Driven Visual States

The manifold shader responds to $V_{active}$ in real-time:

| $V_{active}$ Range | Manifold Base Color | Center Glow | Deformation Behavior |
|--------------------|---------------------|-------------|----------------------|
| $> 0.8$ | Cyan `#00f5d4` | White-hot ignition (intensity = $V_{active}$) | Stable, minimal warping |
| $0.5–0.8$ | Teal → Amber gradient | Dim amber | Moderate gravity wells visible |
| $0.2–0.5$ | Orange `#f97316` | Pulsing red | Significant deformation, peaks forming |
| $0.0–0.2$ | Deep red `#ef4444` | Fast pulse crimson | Aggressive warping, tearing at wells |
| $\leq 0.0$ | **CORRUPTION TEXTURE** | None (frozen) | **MESH FROZEN + SHATTERED** |

### 5.3 Ignition Effect (Healthy State)

When $V_{active} \approx 1.0$, the manifold center emits a white-hot glow:

```glsl
// Fragment shader pseudo-code
float centerDist = length(uv - 0.5);
float ignition = smoothstep(0.5, 0.0, centerDist) * V_active;
vec3 glowColor = mix(cyan, white, ignition);
```

This represents "pure logical fuel burning cleanly."

### 5.4 Freeze Effect (Inverion Divide)

When $V_{active} \leq 0$, the manifold enters a frozen corruption state:
- Vertex positions lock (no more deformation)
- Surface texture switches to monochrome static/noise pattern
- Shattering animation: vertices near high-severity fallacies separate (fracture lines appear)
- Color desaturates to grey with crimson accent on fracture edges

### 5.2 Gravity Well Physics

Each fallacy exerts gravitational pull on vertices within radius `R = 3.0 * (1 - magnitude) + 0.5`:

```
displacement = (fallacy.magnitude * G) / distance²
vertical_offset = -displacement  // downward for wells
```

For peaks (hyperbole, strawman), displacement is positive:
```
displacement = (fallacy.magnitude * G) / distance²
vertical_offset = +displacement
```

For fractures (non sequitur, equivocation):
```
Creates vertex separation beyond threshold → mesh split visualization
```

### 5.3 Multi-Fallacy Superposition

When multiple fallacies interact, their gravity fields superpose:
```
total_offset = Σ (fallacy_i.magnitude * G) / distance_i²
```

If `total_offset` exceeds mesh coherence threshold (`1.5`), visual "tearing" occurs.

### 5.4 Performance Targets

- Target: 60 FPS with up to 50 simultaneous fallacies
- Use GPU-based calculation via custom vertex shader
- CPU handles only fallacy addition/removal, not per-frame physics
- Throttle mesh updates to 30fps during streaming input

---

## 6. The Logic Engine (LLM Integration)

### 6.1 Streaming Analysis Pipeline

```
User Input (Transcript)
       │
       ▼
┌─────────────────────┐
│  Chunking Buffer     │  ← 512 token sliding window
│  (maintains context) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LLM Streaming      │  ← Anthropic Claude API
│  /complete stream   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Fallacy Extractor  │  ← JSON structured output
│  (regex + validation│
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌────────┐  ┌──────────┐
│ Claims │  │ Fallacy  │  ← Both written to DB
│ Graph  │  │ Register │
└────────┘  └──────────┘
           │
           ▼
┌─────────────────────┐
│  Manifold Updater   │  ← WebSocket push to frontend
│  (delta events)     │
└─────────────────────┘
```

### 6.2 Root Fallacy Tracking

When a fallacy is identified, we track its causal lineage:
1. First fallacy in argument = Root Fallacy (depth = 0)
2. Subsequent fallacies that rely on the root inherit `parent_fallacy_id`
3. Cascade depth calculated via recursive query
4. Root fallacies render with pulsing outer ring indicator

### 6.3 Context Window Management

- Sliding context of last 8 claims maintained for causality detection
- LLM prompt includes "Previously identified fallacies" section
- If a new fallacy contradicts earlier claims, flag for human review

---

## 7. The Veracity Auditor (Inverion Gate)

### 7.1 Veracity Constant ($V_c$) — The Integrity Fuel Tank

The system maintains a real-time **Veracity Constant** that represents logical fuel:

- **Base State:** $V_c = 1.0$ (Pure Integrity — a perfectly sound argument)
- **Interpretation:** 1.0 = full logical validity, 0.0 = complete structural collapse

### 7.2 Veracity Cost Calculation

Each detected fallacy consumes Veracity fuel:

$$V_{cost} = Magnitude \times Persistence$$

| Fallacy Type | Magnitude | Persistence | $V_{cost}$ |
|--------------|-----------|-------------|------------|
| Sunk Cost | 0.6 | 0.5 | 0.30 |
| Ad Hominem | 0.9 | 0.8 | 0.72 |
| Hasty Generalization | 0.5 | 0.3 | 0.15 |

### 7.3 Active Veracity ($V_{active}$) — The Decay Formula

The current Veracity is updated per analysis tick:

$$V_{active} = V_c - \sum_{i=1}^{n} V_{cost_i}$$

**Tick:** A single LLM analysis pass that processes a chunk of transcript (typically 1-3 sentences).

### 7.4 The Sudden Veracity Spike (Bypass Detection)

If $V_{active}$ drops more than **0.5 units** in a single tick, the system flags a **Bypass Detected**:

```
if (previous_Vactive - current_Vactive > 0.5):
    trigger_bypass_lockout()
    display_warning("Gish Galloping Detected — Rate of decay exceeds threshold")
```

**Purpose:** Prevents "Gish Galloping" — overwhelming the auditor with rapid-fire fallacies designed to saturate the system before it can respond.

**Lockout Duration:** 3 seconds, during which no new fallacies are registered.

### 7.5 The Inverion Divide — Terminal Lockout

When $V_{active} \leq 0$, the **Inverion Divide** is triggered:

| Threshold | State | Visual Effect |
|-----------|-------|---------------|
| $V_{active} > 0.6$ | Healthy | Cool cyan manifold, stable plane |
| $0.3 < V_{active} \leq 0.6$ | Stressed | Amber warnings, minor warping |
| $0.1 < V_{active} \leq 0.3$ | Critical | Deep red, pulsing "COLLAPSE IMMINENT" |
| $V_{active} \leq 0.0$ | **DIVIDE TRIGGERED** | Manifold shatters, static/corruption overlay |

**Inverion Divide Effects:**
1. **UI Shift:** Manifold freezes in current state, transforms to high-contrast crimson/monochrome corruption texture
2. **P-Gate Activation:** All data nodes become disconnected (greyed out, non-interactive)
3. **Resonance Trajectory Shatters:** The visual flow-lines between claims fragment into static noise
4. **Diagnostic Overlay:** System displays the **Root Fallacy** that caused the collapse with causal chain citation

### 7.6 Visual Thresholds

| Threshold | State | Visual Effect |
|-----------|-------|---------------|
| $V_{active} > 0.8$ | **Ignition** | White-hot center glow, stable cyan plane |
| $0.5 < V_{active} \leq 0.8$ | Healthy | Cool cyan, minimal warping |
| $0.3 < V_{active} \leq 0.5$ | Stressed | Amber warnings, moderate deformation |
| $0.1 < V_{active} \leq 0.3$ | Critical | Deep red, "COLLAPSE IMMINENT" pulsing |
| $V_{active} \leq 0.0$ | **INVERION DIVIDE** | Shattered, static, disconnected nodes |

### 7.7 Structural Integrity Score (Legacy Support)

```
integrity = 1.0 - Σ(fallacy.magnitude * fallacy.persistence * decay_factor)
```

Where `decay_factor = 0.9 ^ depth` (root fallacies decay slowest).

**Note:** This is a derived metric from $V_{active}$, maintained for backward compatibility. $V_{active}$ is the authoritative scoring mechanism.

---

## 8. Temporal Evolution (Time-Travel)

### 8.1 Snapshot System

Every analysis step creates an immutable snapshot:
```sql
CREATE TABLE manifold_snapshots (
    id TEXT PRIMARY KEY,
    argument_id TEXT,
    timestamp TIMESTAMP,
    integrity_score REAL,
    mesh_vertices_json TEXT,  -- serialized vertex positions
    fallacies_json TEXT        -- fallacy state at this moment
);
```

### 8.2 Playback UI

- Timeline scrubber at bottom of screen
- Play/Pause button with speed control (0.5x, 1x, 2x, 4x)
- "Moment of Collapse" button jumps to when integrity drops below 0.5
- Each playback step animates the manifold from previous → current state

### 8.3 Cascade Visualization

During playback, a secondary view shows the fallacy cascade:
- Root fallacy highlights first
- Secondary failures "light up" in causal order
- Edge animation shows propagation direction

---

## 9. Technical Stack Recommendation

### 9.1 Frontend (Web-Based)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | React 18 + TypeScript | Strong ecosystem, good for complex state |
| 3D Rendering | Three.js + React Three Fiber | Best WebGL abstraction, R3F gives React ergonomics |
| State Management | Zustand | Minimal boilerplate, good for real-time updates |
| 3D UI Components | @react-three/drei | Helpers (OrbitControls, Text, etc.) |
| WebSocket | Native WebSocket + socket.io | For streaming LLM input |

### 9.2 Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| API Framework | FastAPI (Python) | Async native, great for streaming |
| LLM Integration | Anthropic SDK | Claude's streaming + structured output |
| Graph Engine | NetworkX | Built-in algorithms for cascade analysis |
| Database | SQLite + SQLAlchemy | Local-first, zero config; upgradeable to Postgres |
| Vector Store | FAISS | Fast similarity search for claim matching |

### 9.3 Deployment Options

**Local Desktop (Electron):**
- Bundles Everything
- No internet required
- Best for sensitive argument analysis

**Cloud (Docker):**
- Frontend: Static hosting (Vercel/Netlify)
- Backend: Docker container on Railway/Render
- Database: Managed SQLite (PlanetScale) or Postgres

**Recommended for MVP:** Electron + local SQLite (data sovereignty focus)

---

## 10. Input-to-Map Pipeline

### 10.1 Latency Budget

| Step | Target Latency |
|------|----------------|
| Text input → LLM parsing | 200–500ms (streaming) |
| Fallacy detection → DB write | < 50ms |
| DB write → WebSocket push | < 20ms |
| WebSocket → Frontend render | < 16ms (60fps) |
| **Total perception** | **< 300ms end-to-end** |

### 10.2 Streaming Input UX

- User pastes transcript into textarea
- "Analyze" button triggers streaming
- Manifold begins deforming in real-time as fallacies are detected
- Claims appear as nodes with edges forming incrementally
- Fallacies animate in as "hot spots" with magnitude indicators

---

## 11. File Structure

```
fallacy-map/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ManifoldCanvas.tsx    # Three.js rendering
│   │   │   ├── ClaimNode.tsx         # Individual claim nodes
│   │   │   ├── FallacyOverlay.tsx    # Click-to-inspect panel
│   │   │   ├── TimelinePlayer.tsx    # Playback controls
│   │   │   ├── VeracityMeter.tsx     # V_active gauge + state indicator
│   │   │   └── InverionDivideOverlay.tsx  # Lockout diagnostic display
│   │   ├── shaders/
│   │   │   ├── manifold.vert.glsl    # Vertex displacement + ignition glow
│   │   │   └── manifold.frag.glsl    # Heat map + corruption static
│   │   ├── stores/
│   │   │   └── argumentStore.ts      # Zustand store (includes V_active)
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts       # Real-time updates
│   │   └── App.tsx
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── analyze.py            # Streaming analysis endpoint
│   │   │   └── snapshots.py         # Playback snapshot retrieval
│   │   ├── services/
│   │   │   ├── llm_analyzer.py       # LLM integration
│   │   │   ├── fallacy_detector.py   # Pattern matching
│   │   │   ├── manifold_calculator.py # Physics simulation
│   │   │   └── veracity_auditor.py   # V_active tracking + Inverion Gate
│   │   ├── models/
│   │   │   ├── claim.py
│   │   │   ├── fallacy.py
│   │   │   └── argument.py
│   │   └── database.py               # SQLAlchemy setup
│   ├── fallacy_taxonomy.json         # Full 50+ fallacy definitions
│   ├── requirements.txt
│   └── main.py
└── README.md
```

---

## 12. Veracity Gate Implementation

### 12.1 State Machine

```
                    ┌─────────────┐
                    │   HEALTHY   │ Vactive > 0.6
                    └──────┬──────┘
                           │
                    Vactive ≤ 0.6
                           │
                    ┌──────▼──────┐
                    │   STRESSED  │ 0.3 < Vactive ≤ 0.6
                    └──────┬──────┘
                           │
                    Vactive ≤ 0.3
                           │
              ┌────────────▼────────────┐
              │        CRITICAL          │ 0.0 < Vactive ≤ 0.3
              │  (Pulsing warning UI)    │
              └────────────┬────────────┘
                           │
                    Vactive ≤ 0.0
                           │
              ┌────────────▼────────────┐
              │   INVERION DIVIDE        │
              │  (LOCKOUT - READ ONLY)  │
              └──────────────────────────┘
```

### 12.2 Bypass Detection Logic

```python
class VeracityAuditor:
    def __init__(self):
        self.V_c = 1.0
        self.V_active = 1.0
        self.previous_V_active = 1.0
        self.spike_threshold = 0.5
        self.bypass_lockout_active = False
    
    def process_fallacy(self, fallacy):
        if self.bypass_lockout_active:
            return None  # Reject new fallacies during lockout
        
        V_cost = fallacy.magnitude * fallacy.persistence
        self.previous_V_active = self.V_active
        self.V_active -= V_cost
        
        # Spike detection
        if (self.previous_V_active - self.V_active) > self.spike_threshold:
            self.trigger_bypass_lockout()
        
        return {
            "V_active": self.V_active,
            "V_cost": V_cost,
            "bypass_triggered": self.bypass_lockout_active
        }
    
    def trigger_bypass_lockout(self):
        self.bypass_lockout_active = True
        schedule_reset(3.0)  # 3 second lockout
    
    def reset_bypass_lockout(self):
        self.bypass_lockout_active = False
```

### 12.3 Visual States

| State | Manifold Color | Center Glow | Node Behavior | Overlay |
|-------|---------------|-------------|---------------|---------|
| Healthy | Cyan stable | White-hot ignition (intensity ∝ Vactive) | Interactive, glowing edges | None |
| Stressed | Amber/Warning | Dim amber | Interactive, warning halos | "Integrity Degrading" |
| Critical | Deep Red | Pulsing crimson | Interactive, red halos | "COLLAPSE IMMINENT" |
| Divide | Static/Corruption | None (frozen) | **DISCONNECTED** (greyed, locked) | Root Fallacy Diagnostic |

---

## 13. Success Criteria

| Criterion | Verification |
|-----------|--------------|
| 50+ fallacies modeled | Taxonomy JSON covers all major logical failures |
| Real-time manifold deformation | Target 60fps with 20 simultaneous fallacies |
| Sub-300ms end-to-end latency | Chrome DevTools trace verification |
| Veracity Constant initialization | $V_c$ starts at 1.0 on new argument |
| Fallacy cost calculation | $V_{cost} = Magnitude \times Persistence$ verified |
| Single-claim decay | A "Sunk Cost" (M=0.6, P=0.5) reduces $V_{active}$ by 0.30 |
| Bypass detection | Rapid-fire fallacies (>0.5 drop/tick) trigger lockout |
| Inverion Divide trigger | Manifold shatters and locks at $V_{active} \leq 0$ |
| Ignition effect | Perfect logic ($V_{active}=1.0$) shows white-hot center |
| Freeze effect | Divide triggers static/corruption texture, nodes disconnect |
| Time-travel playback | Smooth interpolation between snapshots |
| Local data sovereignty | All data stored in local SQLite, no cloud required |
| Extensible schema | New fallacy types addable without code changes |

---

## Appendix A: Full Fallacy Taxonomy

(Full table with 50+ entries — stored in `backend/fallacy_taxonomy.json`)