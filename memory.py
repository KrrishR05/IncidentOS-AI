"""
Memory module — Hindsight Cloud as primary memory layer, local JSON as fallback.

Flow:
  store_incident   → Hindsight.retain()  (+ local JSON backup)
  find_similar     → Hindsight.recall()  (fallback: local cosine search)
  resolve_incident → Hindsight.retain()  with resolution content (+ local JSON update)

Hindsight uses natural-language `retain` / `recall` so we send structured text
summaries as the content string. All raw metadata is kept in the local JSON file
so we can map Hindsight recall results back to full incident records.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "incident_memory.json")
SIMILARITY_THRESHOLD = 0.40
HINDSIGHT_BANK_ID = "incidentos-incidents"
HINDSIGHT_BASE_URL = "https://api.hindsight.vectorize.io"

# ── Lazy singletons ──────────────────────────────────────────────────────────
_model: Optional[SentenceTransformer] = None
_hindsight_client = None          # hindsight_client.Hindsight or None if unavailable


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_hindsight():
    """Return a Hindsight client if the SDK and API key are available, else None."""
    global _hindsight_client
    if _hindsight_client is not None:
        return _hindsight_client

    api_key = os.getenv("HINDSIGHT_API_KEY")
    if not api_key or api_key == "your_hindsight_api_key_here":
        logger.warning(
            "[Memory] HINDSIGHT_API_KEY not set — using local JSON fallback only."
        )
        return None

    try:
        from hindsight_client import Hindsight  # type: ignore

        _hindsight_client = Hindsight(
            base_url=HINDSIGHT_BASE_URL,
            api_key=api_key,
        )
        logger.info(
            "[Memory] Hindsight client initialised ✅  bank_id=%s", HINDSIGHT_BANK_ID
        )
        return _hindsight_client
    except ImportError:
        logger.warning(
            "[Memory] hindsight-client not installed. "
            "Run: pip install hindsight-client -U"
        )
        return None
    except Exception as exc:
        logger.warning("[Memory] Failed to init Hindsight client: %s", exc)
        return None


# ── Hindsight content helpers ────────────────────────────────────────────────

def _incident_to_content(record: dict) -> str:
    """Serialise an incident record into human-readable text for Hindsight fact extraction."""
    lines = [
        f"Incident ID {record['incident_id']}: {record['title']}.",
        f"Description: {record['description']}.",
    ]
    if record.get("root_cause"):
        lines.append(f"Root cause: {record['root_cause']}.")
    if record.get("mitigation_steps"):
        lines.append(f"Mitigation that resolved it: {record['mitigation_steps']}.")
    lines.append(f"Status: {'resolved' if record.get('root_cause') else 'open'}.")
    return " ".join(lines)


def _incident_to_metadata(record: dict) -> dict:
    """Build the metadata dict passed alongside retain() so incident_id is
    preserved verbatim and can be read back from mem.metadata on recall."""
    return {
        "incident_id": record["incident_id"],
        "title": record["title"],
        "root_cause": record.get("root_cause") or "",
        "mitigation_steps": record.get("mitigation_steps") or "",
        "status": "resolved" if record.get("root_cause") else "open",
    }


# ── Local JSON helpers ───────────────────────────────────────────────────────

def _load_memory() -> List[dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def _save_memory(records: List[dict]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


# ── Public API ───────────────────────────────────────────────────────────────

def store_incident(title: str, description: str) -> str:
    """Store a new incident.

    1. Dedup-check local JSON (exact title+description match → return existing ID).
    2. Persist to local JSON with embedding.
    3. Send to Hindsight via retain() (best-effort, won't crash if unavailable).
    """
    records = _load_memory()

    # ── Duplicate guard ──────────────────────────────────────────────────────
    title_norm = title.strip().lower()
    desc_norm = description.strip().lower()
    for rec in records:
        if (
            rec["title"].strip().lower() == title_norm
            and rec["description"].strip().lower() == desc_norm
        ):
            logger.info("[Memory] Duplicate incident detected — returning existing id=%s", rec["incident_id"])
            # Still push to Hindsight if this record was never synced
            if not rec.get("hindsight_synced"):
                client = _get_hindsight()
                if client:
                    try:
                        client.retain(
                            bank_id=HINDSIGHT_BANK_ID,
                            content=_incident_to_content(rec),
                            metadata=_incident_to_metadata(rec),
                        )
                        rec["hindsight_synced"] = True
                        _save_memory(records)
                        logger.info("[Hindsight] retain (dedup-sync) ✅  id=%s", rec["incident_id"])
                    except Exception as exc:
                        logger.warning("[Hindsight] retain (dedup-sync) failed: %s", exc)
            return rec["incident_id"]
    # ────────────────────────────────────────────────────────────────────────

    model = _get_model()
    embedding = model.encode(f"{title} {description}").tolist()
    incident_id = str(uuid.uuid4())[:8]

    record = {
        "incident_id": incident_id,
        "title": title,
        "description": description,
        "root_cause": None,
        "mitigation_steps": None,
        "embedding": embedding,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
    }

    # ── Local JSON persist ───────────────────────────────────────────────────
    records.append(record)
    _save_memory(records)
    logger.info("[Memory] Stored incident locally  id=%s  title=%r", incident_id, title)

    # ── Hindsight retain (best-effort) ───────────────────────────────────────
    client = _get_hindsight()
    if client:
        try:
            content = _incident_to_content(record)
            client.retain(
                bank_id=HINDSIGHT_BANK_ID,
                content=content,
                metadata=_incident_to_metadata(record),
            )
            record["hindsight_synced"] = True
            _save_memory(records)  # persist the synced flag
            logger.info(
                "[Hindsight] retain ✅  bank=%s  id=%s", HINDSIGHT_BANK_ID, incident_id
            )
        except Exception as exc:
            logger.warning("[Hindsight] retain failed (using local fallback): %s", exc)

    return incident_id


def resolve_incident(incident_id: str, root_cause: str, mitigation_steps: str) -> bool:
    """Resolve an incident — updates local JSON and sends resolution to Hindsight."""
    records = _load_memory()
    resolved_at = datetime.now(timezone.utc).isoformat()

    target = None
    for rec in records:
        if rec["incident_id"] == incident_id:
            rec["root_cause"] = root_cause
            rec["mitigation_steps"] = mitigation_steps
            rec["resolved_at"] = resolved_at
            rec["hindsight_synced"] = False  # force re-sync with resolution data
            target = rec
            break

    if target is None:
        return False

    # ── Local JSON persist ───────────────────────────────────────────────────
    _save_memory(records)
    logger.info("[Memory] Resolved incident locally  id=%s", incident_id)

    # ── Hindsight retain with resolution (best-effort) ───────────────────────
    client = _get_hindsight()
    if client:
        try:
            content = _incident_to_content(target)
            client.retain(
                bank_id=HINDSIGHT_BANK_ID,
                content=content,
                metadata=_incident_to_metadata(target),
            )
            target["hindsight_synced"] = True
            _save_memory(records)
            logger.info(
                "[Hindsight] retain (resolve) ✅  bank=%s  id=%s",
                HINDSIGHT_BANK_ID,
                incident_id,
            )
        except Exception as exc:
            logger.warning(
                "[Hindsight] retain (resolve) failed (local data still saved): %s", exc
            )

    return True


def bulk_sync_to_hindsight() -> int:
    """Push all unsynced local incidents to Hindsight. Returns count synced.

    Called once at server startup so existing local incidents become
    searchable via Hindsight recall immediately.
    """
    client = _get_hindsight()
    if not client:
        return 0

    records = _load_memory()
    synced = 0
    dirty = False

    for rec in records:
        if rec.get("hindsight_synced"):
            continue
        try:
            client.retain(
                bank_id=HINDSIGHT_BANK_ID,
                content=_incident_to_content(rec),
                metadata=_incident_to_metadata(rec),
            )
            rec["hindsight_synced"] = True
            dirty = True
            synced += 1
            logger.info("[Hindsight] bulk-sync retain ✅  id=%s", rec["incident_id"])
        except Exception as exc:
            logger.warning("[Hindsight] bulk-sync retain failed  id=%s  err=%s", rec["incident_id"], exc)

    if dirty:
        _save_memory(records)

    logger.info("[Hindsight] bulk-sync complete — %d records synced.", synced)
    return synced


def find_similar_incidents(
    title: str, description: str, top_k: int = 3, exclude_id: Optional[str] = None
) -> List[Tuple[dict, float]]:
    """Return the top_k most similar past incidents with (record, score) tuples.

    Primary:  Hindsight.recall() — uses semantic + BM25 + graph + temporal fusion.
    Fallback: Local cosine similarity over sentence-transformer embeddings.

    Resolved incidents always rank before unresolved ones at the same score.
    """
    records = _load_memory()

    # Build a lookup map for quick record retrieval when processing Hindsight results
    record_map = {r["incident_id"]: r for r in records}

    client = _get_hindsight()

    # ── Hindsight recall path ────────────────────────────────────────────────
    if client:
        try:
            query = f"{title}. {description}"
            logger.info("[Hindsight] recall →  bank=%s  query=%r", HINDSIGHT_BANK_ID, query[:80])

            result = client.recall(
                bank_id=HINDSIGHT_BANK_ID,
                query=query,
            )
            hits = result.results or []
            logger.info(
                "[Hindsight] recall ←  bank=%s  raw_hits=%d",
                HINDSIGHT_BANK_ID, len(hits),
            )

            # Debug: log raw structure of first result
            if hits:
                mem0 = hits[0]
                meta0 = getattr(mem0, 'metadata', None)
                logger.info(
                    "[Hindsight] hit[0] text=%r  metadata=%s",
                    (mem0.text or "")[:80], meta0
                )

            scored: List[Tuple[dict, float]] = []
            for mem in hits:
                # ── Primary: read incident_id from metadata (reliable) ─────
                meta = getattr(mem, 'metadata', None) or {}
                inc_id = meta.get('incident_id') if isinstance(meta, dict) else None

                # ── Fallback: scan text for incident_id mention ───────────
                if not inc_id:
                    for line in (mem.text or "").split("."):
                        line = line.strip()
                        if line.lower().startswith("incident id "):
                            # e.g. "Incident ID abc12345:"
                            parts = line.split()
                            if len(parts) >= 3:
                                inc_id = parts[2].rstrip(":")
                                break

                if not inc_id:
                    logger.debug("[Hindsight] hit skipped — no incident_id found. text=%r", (mem.text or '')[:60])
                    continue

                if inc_id == exclude_id:
                    continue

                rec = record_map.get(inc_id)
                if rec is None:
                    logger.debug("[Hindsight] hit skipped — incident_id=%s not in local map", inc_id)
                    continue

                # Compute cosine score against stored embedding
                model = _get_model()
                q_emb = model.encode(f"{title} {description}")
                emb = np.array(rec.get("embedding", []))
                score = _cosine_similarity(q_emb, emb) if emb.size else 0.5

                logger.info(
                    "[Hindsight] matched  id=%s  title=%r  score=%.4f  resolved=%s",
                    inc_id, rec['title'][:40], score, bool(rec.get('root_cause'))
                )

                if score >= SIMILARITY_THRESHOLD:
                    scored.append((rec, float(score)))

            if scored:
                scored.sort(key=lambda x: (0 if x[0].get("root_cause") else 1, -x[1]))
                logger.info("[Hindsight] returning %d results (primary path)", len(scored[:top_k]))
                return scored[:top_k]

            logger.info("[Hindsight] 0 usable results — falling through to local search.")

        except Exception as exc:
            logger.warning("[Hindsight] recall failed (using local fallback): %s", exc)

    # ── Local cosine fallback ────────────────────────────────────────────────
    logger.info("[Memory] Using local cosine similarity search.")
    if not records:
        return []

    model = _get_model()
    query_embedding = model.encode(f"{title} {description}")

    scored_local: List[Tuple[dict, float]] = []
    for rec in records:
        if exclude_id and rec["incident_id"] == exclude_id:
            continue
        if not rec.get("embedding"):
            continue
        emb = np.array(rec["embedding"])
        score = _cosine_similarity(query_embedding, emb)
        if score >= SIMILARITY_THRESHOLD:
            scored_local.append((rec, score))

    scored_local.sort(key=lambda x: (0 if x[0].get("root_cause") else 1, -x[1]))
    return scored_local[:top_k]
