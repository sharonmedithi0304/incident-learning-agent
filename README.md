# Incident Learning Agent

Past incident -> Hindsight memory -> future incident -> changed investigation.

## Setup (Windows PowerShell)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Leave `HINDSIGHT_BASE_URL` empty to use the local FAKE client (API reports `memory_backend: "fake"`).
Set `HINDSIGHT_BASE_URL` (+ `HINDSIGHT_API_KEY` for Cloud) to use real Hindsight.

## Run
```
python -m pytest -q
uvicorn app.main:app --reload --app-dir backend
```

## Demo flow (API)
- `POST /api/seed` retains INC-1041 (failed DB scaling, pool exhaustion, rollback fix)
- `POST /api/compare` returns memory OFF vs ON plans, evidence, and why the plan changed
- `POST /api/investigate` with `{"memory": true|false}`
