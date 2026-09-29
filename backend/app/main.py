from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import compare, investigate
from .config import load_settings
from .hindsight_store import HindsightStore, build_store
from .models import Comparison, Investigation, NewIncident
from .seed import INC_1041, INC_NEW

app = FastAPI(title="Incident Learning Agent")


@lru_cache
def get_store() -> HindsightStore:
    s = build_store(load_settings())
    s.ensure_bank()
    return s


class InvestigateRequest(BaseModel):
    incident: Optional[NewIncident] = None  # defaults to the demo incident
    memory: bool = True


class CompareRequest(BaseModel):
    incident: Optional[NewIncident] = None


@app.get("/api/health")
def health(store: HindsightStore = Depends(get_store)):
    try:
        store.healthcheck()
    except Exception:
        raise HTTPException(status_code=503, detail="Hindsight backend is unavailable.")
    return {"ok": True, "memory_backend": store.backend}


@app.get("/api/scenario")
def scenario():
    return {"past_incident": INC_1041, "new_incident": INC_NEW}


@app.post("/api/seed")
def seed(store: HindsightStore = Depends(get_store)):
    try:
        narrative = store.retain_incident(INC_1041)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retain incident in Hindsight.")
    return {"retained": INC_1041.id, "memory_backend": store.backend, "narrative": narrative}


@app.post("/api/investigate", response_model=Investigation)
def api_investigate(req: InvestigateRequest, store: HindsightStore = Depends(get_store)):
    try:
        return investigate(req.incident or INC_NEW, store, memory=req.memory)
    except Exception:
        raise HTTPException(status_code=502, detail="Investigation failed while reading Hindsight.")


@app.post("/api/compare", response_model=Comparison)
def api_compare(req: CompareRequest, store: HindsightStore = Depends(get_store)):
    try:
        return compare(req.incident or INC_NEW, store)
    except Exception:
        raise HTTPException(status_code=502, detail="Comparison failed while reading Hindsight.")


_frontend = Path(__file__).resolve().parents[2] / "frontend"
if (_frontend / "index.html").exists():
    app.mount("/static", StaticFiles(directory=_frontend), name="static")

    @app.get("/")
    def index():
        return FileResponse(_frontend / "index.html")
