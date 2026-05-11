# The Fallacy Map

**The Geography of Logic** — Transform argument analysis into navigable topography.

To learn more about our project and goals, please visit [KylosArc.com](https://kylosarc.com).

## Overview

The Fallacy Map is a real-time argument analysis tool that visualizes logical fallacies as gravitational distortions on a 3D manifold surface. Sound logic forms a flat, stable plane; fallacies become gravity wells, peaks, and fractures that distort the surface.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    FRONTEND                      │
│  React + TypeScript + Three.js (WebGL Canvas)   │
└───────────────────────────┬─────────────────────┘
                            │ WebSocket / HTTP
┌───────────────────────────▼─────────────────────┐
│                    BACKEND                       │
│  FastAPI (Python) + SQLite + LLM Gateway       │
└─────────────────────────────────────────────────┘
```

## Quick Start

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd backend/fallacy_map/frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to use the application.

## Features

- **Veracity Auditor**: Tracks logical integrity (V_active) from 1.0 (perfect) to 0 (collapse)
- **Real-time Detection**: Pattern-based fallacy detection with regex patterns
- **3D Manifold Visualization**: WebGL-powered deformable mesh showing logical distortion
- **Inverion Divide**: Terminal state when V_active ≤ 0, triggering manifold corruption visualization
- **Time-Travel Playback**: Review argument analysis snapshots

## Tech Stack

| Component | Technology |
|-----------|-------------|
| Frontend | React 18, TypeScript, Three.js, React Three Fiber, Zustand |
| Backend | FastAPI (Python), SQLAlchemy, SQLite |
| Visualization | Custom GLSL shaders, Three.js |
| API | REST + WebSocket |

## License

MIT License

## Links

- [KylosArc.com](https://kylosarc.com) — Learn more about our project and goals
- GitHub Repository: https://github.com/shansimmons-eng/Fallacy-Map