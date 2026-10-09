# Accord API (TASK 003)

Backend core service for Accord's simulated household-negotiation prototype.

## Run locally
From repository root:

```bash
pip install fastapi uvicorn
PYTHONPATH=/home/runner/work/accord-alexa-plus/accord-alexa-plus/apps/api/src python -m uvicorn accord_api.app:app --reload
```

API base path: `/api`

## Notes
- All integrations are simulated.
- Privacy enforcement is server-side (authorization + private/shared serializers).
- The fairness solver is a deterministic placeholder (non-LLM) behind a replaceable interface.
