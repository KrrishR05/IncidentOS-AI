"""
IncidentOS API — main FastAPI application.
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

import asyncio

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from schemas import (
    NewIncidentRequest,
    NewIncidentResponse,
    ResolveIncidentRequest,
    ResolveIncidentResponse,
    SimilarIncident,
    PostmortemResponse,
    InsightsResponse,
)
import memory
import agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: sync from Hindsight Cloud to populate local memory."""
    loop    = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, memory.sync_from_hindsight_cloud)
    logger.info(
        "[Startup] Hindsight cloud sync: fetched=%d added=%d updated=%d total=%d",
        summary["fetched"], summary["added"], summary["updated"], summary["total"],
    )
    yield


app = FastAPI(
    title="IncidentOS API",
    description="AI-powered incident management with semantic memory",
    version="0.2.0",
    lifespan=lifespan,
)




@app.post("/incident/new", response_model=NewIncidentResponse)
def create_incident(req: NewIncidentRequest):
    """Create (or retrieve existing) incident, run AI analysis, and return full context.

    This endpoint is idempotent: submitting the same title+description twice
    returns the existing incident ID instead of creating a duplicate.
    """
    incident_id = memory.store_incident(req.title, req.description)

    similar_raw = memory.find_similar_incidents(
        req.title, req.description, top_k=3, exclude_id=incident_id
    )

    similar_incident_objects = [
        SimilarIncident(
            incident_id=rec["incident_id"],
            title=rec["title"],
            description=rec.get("description") or "",
            root_cause=rec.get("root_cause"),
            mitigation_steps=rec.get("mitigation_steps"),
            similarity_score=round(score, 4),
            created_at=rec["created_at"],
        )
        for rec, score in similar_raw
    ]

    similar_dicts = [rec for rec, _ in similar_raw]
    analysis = agent.analyze_incident(
        req.title, req.description, similar_incidents=similar_dicts or None
    )
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
    """Resolve an existing incident.

    Updates root_cause and mitigation_steps on the local record and re-pushes
    the resolved content to Hindsight Cloud (best-effort).
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


@app.get("/status")
def health_check():
    """Health-check endpoint — used by the frontend to show backend/Hindsight status."""
    hindsight_connected = memory._get_hindsight() is not None
    return {
        "status": "online",
        "version": "0.2.0",
        "hindsight": hindsight_connected,
    }


@app.post("/sync")
async def trigger_sync():
    """Trigger a full sync from Hindsight Cloud into local memory on demand."""
    loop    = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, memory.sync_from_hindsight_cloud)
    return {
        "ok":      True,
        "fetched": summary["fetched"],
        "added":   summary["added"],
        "updated": summary["updated"],
        "total":   summary["total"],
    }


@app.post("/deduplicate")
async def deduplicate():
    """Remove duplicate incidents from local memory (exact-ID + semantic title dedup)."""
    loop    = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, memory.deduplicate_local_incidents)
    return {
        "ok":      True,
        "before":  summary["before"],
        "after":   summary["after"],
        "removed": summary["removed"],
    }


# Endpoint to provide incident statistics and full list for the frontend
@app.get("/incidents/all")
def get_all_incidents():
    """Return all local incidents with computed open/resolved stats."""
    records   = memory.get_all_incidents()
    resolved  = [r for r in records if r.get("root_cause")]
    unresolved = [r for r in records if not r.get("root_cause")]

    return {
        "total":    len(records),
        "resolved": len(resolved),
        "open":     len(unresolved),
        "incidents": [
            {
                "incident_id":     r["incident_id"],
                "title":           r["title"],
                "description":     r.get("description") or "",
                "status":          "resolved" if r.get("root_cause") else "open",
                "root_cause":      r.get("root_cause"),
                "mitigation_steps": r.get("mitigation_steps"),
                "created_at":      r["created_at"],
                "resolved_at":     r.get("resolved_at"),
            }
            for r in records
        ],
    }


# Endpoint to get a single incident by ID
@app.get("/incident/{incident_id}")
def get_incident(incident_id: str):
    """Return a single incident record by ID."""
    records = memory.get_all_incidents()
    for rec in records:
        if rec["incident_id"] == incident_id:
            return {
                "incident_id":     rec["incident_id"],
                "title":           rec["title"],
                "description":     rec.get("description") or "",
                "status":          "resolved" if rec.get("root_cause") else "open",
                "root_cause":      rec.get("root_cause"),
                "mitigation_steps": rec.get("mitigation_steps"),
                "created_at":      rec["created_at"],
                "resolved_at":     rec.get("resolved_at"),
            }
    raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")


@app.post("/incident/{incident_id}/postmortem", response_model=PostmortemResponse)
def generate_postmortem(incident_id: str):
    """Generate a markdown post-mortem for a resolved incident."""
    records = memory.get_all_incidents()
    incident = next((r for r in records if r["incident_id"] == incident_id), None)
    
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        
    if not incident.get("root_cause"):
        raise HTTPException(status_code=400, detail="Cannot generate postmortem for an unresolved incident.")
        
    markdown = agent.generate_postmortem(
        title=incident["title"],
        description=incident.get("description") or "",
        root_cause=incident["root_cause"],
        mitigation=incident.get("mitigation_steps") or "Unknown"
    )
    
    return PostmortemResponse(incident_id=incident_id, markdown=markdown)


@app.get("/incidents/insights", response_model=InsightsResponse)
def get_insights():
    """Analyze recent resolved incidents to provide systemic insights."""
    records = memory.get_all_incidents()
    resolved = [r for r in records if r.get("root_cause")]
    
    if not resolved:
        return InsightsResponse(insights=[])
        
    insights = agent.generate_insights(resolved)
    return InsightsResponse(insights=insights)

