"""
IncidentOS API — main FastAPI application.

Startup validates that required environment variables are present so the
server fails immediately with a clear message rather than crashing mid-request.
"""

import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

# ── Env-var validation (fail fast on startup) ────────────────────────────────
_REQUIRED_ENV = ["GROQ_API_KEY"]

def _check_env() -> None:
    missing = [k for k in _REQUIRED_ENV if not os.getenv(k)]
    if missing:
        print(
            f"[IncidentOS] FATAL: Missing required environment variable(s): "
            f"{', '.join(missing)}. "
            f"Please set them in your .env file and restart.",
            file=sys.stderr,
        )
        sys.exit(1)

_check_env()
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from schemas import (
    NewIncidentRequest,
    NewIncidentResponse,
    ResolveIncidentRequest,
    ResolveIncidentResponse,
    SimilarIncident,
)
import memory
import agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sync all unsynced local incidents to Hindsight on startup (in thread pool)."""
    import asyncio
    loop = asyncio.get_event_loop()
    # Run the sync SDK calls in a thread so they can create their own event loop
    count = await loop.run_in_executor(None, memory.bulk_sync_to_hindsight)
    logger.info("[Startup] Hindsight bulk-sync pushed %d records.", count)
    yield


app = FastAPI(
    title="IncidentOS API",
    description="AI-powered incident management with semantic memory",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {
        "message": "IncidentOS API is running ✅",
        "version": "0.2.0",
        "model": agent.MODEL,
    }


@app.post("/incident/new", response_model=NewIncidentResponse)
def create_incident(req: NewIncidentRequest):
    """
    Create a new incident. Automatically:
    1. Deduplicates — if exact title+description already exists, returns existing record.
    2. Stores it in vector memory (JSON-backed, survives restarts).
    3. Searches for similar past incidents (resolved ones ranked first).
    4. Calls the LLM to analyse (with memory context).
    5. Suggests 4 immediate actions.
    """
    # 1. Store in memory (dedup handled inside)
    incident_id = memory.store_incident(req.title, req.description)

    # 2. Find similar past incidents (exclude the current one)
    similar_raw = memory.find_similar_incidents(
        req.title, req.description, top_k=3, exclude_id=incident_id
    )

    similar_incident_objects = [
        SimilarIncident(
            incident_id=rec["incident_id"],
            title=rec["title"],
            description=rec["description"],
            root_cause=rec.get("root_cause"),
            mitigation_steps=rec.get("mitigation_steps"),
            similarity_score=round(score, 4),
            created_at=rec["created_at"],
        )
        for rec, score in similar_raw
    ]

    similar_dicts = [rec for rec, _ in similar_raw]

    # 3. LLM analysis (errors surface as clean HTTP 502/500)
    analysis = agent.analyze_incident(
        req.title, req.description, similar_incidents=similar_dicts or None
    )

    # 4. Suggested actions
    actions = agent.suggest_actions(
        req.title, req.description, analysis, similar_incidents=similar_dicts or None
    )

    return NewIncidentResponse(
        incident_id=incident_id,
        title=req.title,
        description=req.description,
        status="open",
        ai_analysis=analysis,
        similar_past_incidents=similar_incident_objects,
        suggested_actions=actions,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/incident/resolve", response_model=ResolveIncidentResponse)
def resolve_incident(req: ResolveIncidentRequest):
    """
    Resolve an existing incident.
    Updates root_cause and mitigation_steps on the existing record in memory —
    no new record is created. Future similar incidents will learn from this.
    """
    success = memory.resolve_incident(
        req.incident_id, req.root_cause, req.mitigation_steps
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Incident '{req.incident_id}' not found in memory.",
        )

    return ResolveIncidentResponse(
        incident_id=req.incident_id,
        status="resolved",
        root_cause=req.root_cause,
        mitigation_steps=req.mitigation_steps,
        memory_stored=True,
        resolved_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/incidents/all")
def list_all_incidents():
    """
    Return all incidents in local memory with counts.
    Used for health-checks and demo validation.
    """
    records = memory._load_memory()
    resolved   = [r for r in records if r.get("root_cause")]
    unresolved = [r for r in records if not r.get("root_cause")]
    return {
        "total":      len(records),
        "resolved":   len(resolved),
        "open":       len(unresolved),
        "incidents":  [
            {
                "incident_id":     r["incident_id"],
                "title":           r["title"],
                "status":          "resolved" if r.get("root_cause") else "open",
                "root_cause":      r.get("root_cause"),
                "mitigation_steps": r.get("mitigation_steps"),
                "created_at":      r["created_at"],
            }
            for r in records
        ],
    }
