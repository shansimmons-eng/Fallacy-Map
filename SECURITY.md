# Security Notes

## Current Status

The Fallacy Map project has been pushed to GitHub. Review the following security considerations:

## Hardcoded Credentials (TODO)

The following should be moved to environment variables:

| File | Issue | Severity |
|------|-------|----------|
| `backend/app/services/llm_analyzer.py` | `ANTHROPIC_API_KEY` hardcoded as placeholder | Medium |

**Recommendation**: Use `python-dotenv` or environment variables:
```python
import os
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

## Dependencies

### Backend (Python)
- fastapi==0.109.0
- uvicorn==0.27.0
- sqlalchemy==2.0.25
- anthropic==0.18.0 (has known httpx compatibility issue)
- pydantic==2.5.3

### Frontend (Node.js)
- react==18.2.0
- three==0.160.0
- zustand==4.4.7

## Network Security

- CORS is configured to allow all origins (`*`) — restrict in production
- SQLite database stored in user home directory (`~/.fallacy_map/`)
- No authentication on API endpoints

## Input Validation

- All user inputs should be validated before processing
- SQL injection protection via SQLAlchemy ORM (parameterized queries)

## Production Recommendations

1. Move all secrets to environment variables
2. Implement API authentication (JWT or similar)
3. Configure CORS for specific frontend origin only
4. Use managed database (Postgres) instead of SQLite
5. Enable HTTPS
6. Add rate limiting