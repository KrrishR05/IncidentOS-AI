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

import concurrent.futures as _cf
import json
import logging
import os
import threading as _threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
MEMORY_FILE      = os.path.join(os.path.dirname(__file__), "incident_memory.json")
SIMILARITY_THRESHOLD = 0.40
HINDSIGHT_BANK_ID    = "incidentos-incidents"
HINDSIGHT_BASE_URL   = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")

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


# ── Thread-isolated Hindsight wrappers ────────────────────────────────────────
# The SDK's sync methods (retain, recall, list_memories) use _run_async()
# internally which calls loop.run_until_complete().  When FastAPI's async
# startup is running that raises RuntimeError("This event loop is already running").
#
# Fix: run every SDK call in a FRESH daemon thread that has NO running event
# loop. Each threading.Thread starts with a clean asyncio state, so the SDK's
# _run_async creates a brand-new loop and succeeds.
#
# We also instantiate a FRESH Hindsight client inside the thread so that
# aiohttp's ClientSession is bound to that thread's event loop — not to a
# stale loop from a previous call.

def _in_thread(fn, *args, **kwargs):
    """Execute fn(*args, **kwargs) in a brand-new thread with no event loop.

    Returns the result or re-raises any exception from inside the thread.
    """
    result_holder = [None]
    exc_holder    = [None]

    def _run():
        try:
            result_holder[0] = fn(*args, **kwargs)
        except Exception as e:
            exc_holder[0] = e

    t = _threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=60)

    if t.is_alive():
        raise TimeoutError(f"Hindsight SDK call timed out after 60 s: {getattr(fn, '__name__', fn)}")
    if exc_holder[0] is not None:
        raise exc_holder[0]
    return result_holder[0]


def _fresh_client():
    """Return a brand-new Hindsight client using env-var credentials.
    Must be called from INSIDE a fresh thread (no running event loop).
    """
    from hindsight_client import Hindsight  # type: ignore
    return Hindsight(
        base_url=HINDSIGHT_BASE_URL,
        api_key=os.getenv("HINDSIGHT_API_KEY", ""),
    )


def _hindsight_retain(content: str, metadata: dict) -> None:
    """Call retain() in a fresh thread with a brand-new client."""
    if not _get_hindsight():
        return

    def _do():
        _fresh_client().retain(
            bank_id=HINDSIGHT_BANK_ID,
            content=content,
            metadata=metadata,
        )

    _in_thread(_do)


def _hindsight_recall(query: str):
    """Call recall() in a fresh thread with a brand-new client."""
    if not _get_hindsight():
        return None

    def _do():
        return _fresh_client().recall(bank_id=HINDSIGHT_BANK_ID, query=query)

    return _in_thread(_do)


# ── Hindsight content helpers ────────────────────────────────────────────────

def _incident_to_content(record: dict) -> str:
    """Serialise an incident record into human-readable text for Hindsight."""
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
        "incident_id":     record["incident_id"],
        "title":           record["title"],
        "root_cause":      record.get("root_cause") or "",
        "mitigation_steps": record.get("mitigation_steps") or "",
        "status":          "resolved" if record.get("root_cause") else "open",
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
    3. Send to Hindsight via _hindsight_retain() (best-effort).
    """
    records = _load_memory()

    # ── Duplicate guard ──────────────────────────────────────────────────────
    title_norm = title.strip().lower()
    desc_norm  = description.strip().lower()
    for rec in records:
        if (
            rec["title"].strip().lower() == title_norm
            and rec["description"].strip().lower() == desc_norm
        ):
            logger.info("[Memory] Duplicate incident detected — returning existing id=%s", rec["incident_id"])
            if not rec.get("hindsight_synced"):
                try:
                    _hindsight_retain(
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

    model     = _get_model()
    embedding = model.encode(f"{title} {description}").tolist()
    incident_id = str(uuid.uuid4())[:8]

    record = {
        "incident_id":     incident_id,
        "title":           title,
        "description":     description,
        "root_cause":      None,
        "mitigation_steps": None,
        "embedding":       embedding,
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "resolved_at":     None,
    }

    records.append(record)
    _save_memory(records)
    logger.info("[Memory] Stored incident locally  id=%s  title=%r", incident_id, title)

    try:
        _hindsight_retain(
            content=_incident_to_content(record),
            metadata=_incident_to_metadata(record),
        )
        record["hindsight_synced"] = True
        _save_memory(records)
        logger.info("[Hindsight] retain ✅  bank=%s  id=%s", HINDSIGHT_BANK_ID, incident_id)
    except Exception as exc:
        logger.warning("[Hindsight] retain failed (using local fallback): %s", exc)

    return incident_id


def resolve_incident(incident_id: str, root_cause: str, mitigation_steps: str) -> bool:
    """Resolve an incident — updates local JSON and sends resolution to Hindsight."""
    records    = _load_memory()
    resolved_at = datetime.now(timezone.utc).isoformat()

    target = None
    for rec in records:
        if rec["incident_id"] == incident_id:
            rec["root_cause"]      = root_cause
            rec["mitigation_steps"] = mitigation_steps
            rec["resolved_at"]     = resolved_at
            rec["hindsight_synced"] = False
            target = rec
            break

    if target is None:
        return False

    _save_memory(records)
    logger.info("[Memory] Resolved incident locally  id=%s", incident_id)

    try:
        _hindsight_retain(
            content=_incident_to_content(target),
            metadata=_incident_to_metadata(target),
        )
        target["hindsight_synced"] = True
        _save_memory(records)
        logger.info(
            "[Hindsight] retain (resolve) ✅  bank=%s  id=%s",
            HINDSIGHT_BANK_ID, incident_id,
        )
    except Exception as exc:
        logger.warning(
            "[Hindsight] retain (resolve) failed (local data still saved): %s", exc
        )

    return True


def bulk_sync_to_hindsight() -> int:
    """Push all unsynced local incidents to Hindsight. Returns count synced."""
    if not _get_hindsight():
        return 0

    records = _load_memory()
    synced  = 0
    dirty   = False

    for rec in records:
        if rec.get("hindsight_synced"):
            continue
        try:
            _hindsight_retain(
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
    records    = _load_memory()
    record_map = {r["incident_id"]: r for r in records}

    # Pre-compute query embedding ONCE (used in both paths)
    model   = _get_model()
    q_emb   = model.encode(f"{title} {description}")

    # ── Hindsight recall path ────────────────────────────────────────────────
    if _get_hindsight():
        try:
            query = f"{title}. {description}"
            logger.info("[Hindsight] recall →  bank=%s  query=%r", HINDSIGHT_BANK_ID, query[:80])

            result = _hindsight_recall(query)
            hits   = (result.results if result else None) or []
            logger.info(
                "[Hindsight] recall ←  bank=%s  raw_hits=%d",
                HINDSIGHT_BANK_ID, len(hits),
            )

            if hits:
                mem0  = hits[0]
                meta0 = getattr(mem0, "metadata", None)
                logger.info(
                    "[Hindsight] hit[0] text=%r  metadata=%s",
                    (getattr(mem0, "text", "") or "")[:80], meta0,
                )

            scored: List[Tuple[dict, float]] = []
            for mem in hits:
                meta   = getattr(mem, "metadata", None) or {}
                inc_id = meta.get("incident_id") if isinstance(meta, dict) else None

                # Fallback: parse ID from "Incident ID xxx:" text
                if not inc_id:
                    for line in (getattr(mem, "text", "") or "").split("."):
                        line = line.strip()
                        if line.lower().startswith("incident id "):
                            parts = line.split()
                            if len(parts) >= 3:
                                inc_id = parts[2].rstrip(":")
                                break

                if not inc_id or inc_id == exclude_id:
                    continue

                rec = record_map.get(inc_id)
                if rec is None:
                    continue

                emb   = np.array(rec.get("embedding") or [])
                score = _cosine_similarity(q_emb, emb) if emb.size else 0.5

                logger.info(
                    "[Hindsight] matched  id=%s  title=%r  score=%.4f  resolved=%s",
                    inc_id, rec["title"][:40], score, bool(rec.get("root_cause")),
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

    scored_local: List[Tuple[dict, float]] = []
    for rec in records:
        if exclude_id and rec["incident_id"] == exclude_id:
            continue
        if not rec.get("embedding"):
            continue
        emb   = np.array(rec["embedding"])
        score = _cosine_similarity(q_emb, emb)
        if score >= SIMILARITY_THRESHOLD:
            scored_local.append((rec, score))

    scored_local.sort(key=lambda x: (0 if x[0].get("root_cause") else 1, -x[1]))
    return scored_local[:top_k]


def get_all_incidents() -> List[dict]:
    """Return all incident records from local memory."""
    return _load_memory()


# ── Hindsight Cloud full-sync helpers ─────────────────────────────────────────

_SWEEP_QUERIES = [
    "database connection exhaustion incident",
    "API latency spike production outage",
    "auth service failing pods restart",
    "incident resolved mitigation steps",
    "open incident unresolved status",
    "memory leak CPU spike disk I/O",
    "timeout config pool size restart",
    "error rate spike users reporting errors",
    "kubernetes deployment restart rollout",
    "network timeout connection refused",
    "out of memory OOM killed pod",
    "disk full storage capacity exceeded",
    "CPU throttling high load average",
    "cache miss Redis memcached failure",
    "queue backlog consumer lag",
    "certificate expired TLS SSL error",
    "deploy rollback regression hotfix",
    "postgres MySQL slow query lock",
    "HTTP 500 502 503 gateway error",
    "microservice dependency health check",
    "load balancer upstream unavailable",
    "rate limit throttle quota exceeded",
    "data pipeline ETL job failed",
    "batch job timeout worker crash",
    "DNS resolution failure lookup",
    "incident postmortem root cause analysis",
    "alert firing on-call PagerDuty",
    "service degraded partial outage recovery",
]


def _parse_cloud_item(item) -> Optional[dict]:
    """Convert a Hindsight recall/list_memories result into an IncidentOS record.

    TWO item types come in:
      A) recall() result  — SDK object with .metadata dict holding our stored fields
      B) list_memories()  — plain dict with extracted NLP facts, NO metadata field

    For (A) we read incident_id directly from metadata.
    For (B) we regex-extract the incident_id from the fact text.
    """
    import re as _re

    # ── Unpack based on item type ─────────────────────────────────────────────
    if isinstance(item, dict):
        meta     = item.get("metadata") or {}
        text     = item.get("text") or item.get("content") or ""
        occurred = (item.get("occurred_start") or item.get("date")
                    or item.get("mentioned_at") or item.get("created_at"))
    else:
        meta     = getattr(item, "metadata", None) or {}
        text     = getattr(item, "text", "") or ""
        occurred = getattr(item, "occurred_start", None)

    meta = meta if isinstance(meta, dict) else {}

    # ── A: metadata path (recall() results carry our stored metadata) ─────────
    inc_id     = (meta.get("incident_id") or "").strip()
    title      = (meta.get("title") or "").strip()
    root_cause = (meta.get("root_cause") or "").strip()
    mitigation = (meta.get("mitigation_steps") or "").strip()

    # ── B: text-extraction path (fact items without metadata) ────────────────
    if not inc_id and text:
        # Pattern 1: 8-char hex — "Incident ID d56b2cad" or "Incident d56b2cad"
        id_match = _re.search(
            r'[Ii]ncident\s+(?:ID\s+)?([0-9a-f]{8})(?:[^0-9a-f]|$)',
            text,
        )
        if id_match:
            inc_id = id_match.group(1)

        # Pattern 2: INCxxxxxxx dataset IDs — "Incident INC0027946 occurred..."
        if not inc_id:
            inc_match = _re.search(
                r'[Ii]ncident\s+(INC\d+)',
                text,
            )
            if inc_match:
                inc_id = inc_match.group(1)

        # Detect root_cause: "caused by X and resolved" / "root cause…identified as X"
        if not root_cause and inc_id:
            rc_match = _re.search(
                r'(?:root cause(?:\s+(?:of|was identified as))?[^.]*?|caused by)\s+'
                r'([A-Za-z][A-Za-z0-9 _,\-]{2,80}?)'
                r'(?:\s+and resolved|\s*\.|$)',
                text, _re.I,
            )
            if rc_match:
                root_cause = rc_match.group(1).strip()

        # Detect mitigation: "resolved using (mitigation step) X"
        if not mitigation and inc_id:
            mit_match = _re.search(
                r'resolved using(?:\s+mitigation(?:\s+step)?)?\s+'
                r'([A-Za-z][A-Za-z0-9 _,\-]{2,120}?)(?:\.|$)',
                text, _re.I,
            )
            if mit_match:
                mitigation = mit_match.group(1).strip()

    # ── Skip if we still can't identify the incident ──────────────────────────
    if not inc_id:
        return None

    # ── Build title from metadata or from "Incident ID xxx: Title" pattern ────
    if not title and text:
        tm = _re.match(r'[Ii]ncident\s+(?:ID\s+)?[0-9a-f]+[:\s]+(.+?)(?:\.|$)', text)
        if tm:
            title = tm.group(1).strip()[:80]
    if not title:
        # Use first sentence fragment as title
        title = text.split(".")[0].strip()[:80]
    if not title or len(title) < 3:
        return None

    # ── Extract description from "Description: <text>. Root cause:" pattern ───
    description = ""
    desc_match = _re.search(
        r'[Dd]escription:\s*(.+?)(?:\s*\.\s*(?:Root cause:|Mitigation|Status:|$))',
        text, _re.DOTALL,
    )
    if desc_match:
        description = desc_match.group(1).strip().rstrip(".")
    if not description:
        description = text[:300]

    created_at = str(occurred) if occurred else datetime.now(timezone.utc).isoformat()

    return {
        "incident_id":      inc_id,
        "title":            title,
        "description":      description[:500],
        "root_cause":       root_cause or None,
        "mitigation_steps": mitigation or None,
        "embedding":        [],
        "created_at":       created_at,
        "resolved_at":      created_at if root_cause else None,
        "hindsight_synced": True,
    }


def _fetch_list_memories() -> list:
    """Fetch ALL pages from list_memories() inside a single thread.

    Running all pages in ONE thread ensures they share the same event loop
    and aiohttp ClientSession — crossing threads causes the
    "Timeout context manager should be used inside a task" error.
    """
    if not _get_hindsight():
        return []

    def _all_pages():
        client    = _fresh_client()
        all_items = []
        offset    = 0
        page_size = 100
        while True:
            try:
                result = client.list_memories(
                    bank_id=HINDSIGHT_BANK_ID, limit=page_size, offset=offset
                )
            except Exception as exc:
                logger.warning("[Hindsight] list_memories() error at offset=%d: %s", offset, exc)
                break

            if result is None:
                break
            elif isinstance(result, list):
                items = result
            elif hasattr(result, "items"):
                items = result.items or []
            elif hasattr(result, "results"):
                items = result.results or []
            elif hasattr(result, "memories"):
                items = result.memories or []
            else:
                break

            if not items:
                break
            all_items.extend(items)
            if len(items) < page_size:
                break
            offset += page_size

        return all_items

    try:
        return _in_thread(_all_pages)
    except Exception as exc:
        logger.warning("[Hindsight] _fetch_list_memories failed: %s", exc)
        return []


def _fetch_recall_sweep() -> list:
    """Broad recall() sweep with diverse queries inside ONE thread.

    recall() results carry our stored metadata (incident_id, title, root_cause…)
    so this is the best path for recovering resolved-status information.
    """
    if not _get_hindsight():
        return []

    def _all_recalls():
        client   = _fresh_client()
        seen: set     = set()
        all_hits: list = []
        for q in _SWEEP_QUERIES:
            try:
                result = client.recall(bank_id=HINDSIGHT_BANK_ID, query=q)
                for mem in ((result.results if result else None) or []):
                    mem_id = str(getattr(mem, "id", ""))
                    if mem_id and mem_id not in seen:
                        seen.add(mem_id)
                        all_hits.append(mem)
            except Exception as exc:
                logger.debug("[Hindsight] recall sweep query %r failed: %s", q[:40], exc)
        return all_hits

    try:
        return _in_thread(_all_recalls)
    except Exception as exc:
        logger.warning("[Hindsight] _fetch_recall_sweep failed: %s", exc)
        return []


def sync_from_hindsight_cloud() -> dict:
    """Pull ALL records from Hindsight Cloud and merge into local JSON.

    Strategy:
      1. list_memories() — gets all NLP fact items (no metadata); parse incident_id from text.
      2. recall() sweep  — gets items WITH metadata (title, root_cause, etc.).
      Combine both; recall wins on metadata quality.

    Returns summary dict: {fetched, added, updated, total}.
    """
    if not _get_hindsight():
        logger.info("[Hindsight] sync skipped — no client available.")
        return {"fetched": 0, "added": 0, "updated": 0, "total": len(_load_memory())}

    # ── 1. Fetch from cloud — list_memories first, recall sweep always ────────
    logger.info("[Hindsight] Starting cloud sync via list_memories()...")
    list_items   = _fetch_list_memories()
    logger.info("[Hindsight] list_memories fetched %d raw items. Running recall sweep...", len(list_items))
    recall_items = _fetch_recall_sweep()
    logger.info("[Hindsight] recall sweep fetched %d items.", len(recall_items))

    # recall items override list_memories items for the same incident_id
    raw_items = list_items + recall_items
    logger.info("[Hindsight] Total raw items from cloud: %d", len(raw_items))

    # ── 2. Parse ───────────────────────────────────────────────────────────────
    parsed: List[dict] = []
    for item in raw_items:
        rec = _parse_cloud_item(item)
        if rec:
            parsed.append(rec)

    # Dedup cloud items — recall results (with metadata) beat list_memories facts
    # Prefer resolved over open when merging same incident_id
    cloud_map: dict = {}
    for rec in parsed:
        inc_id   = rec["incident_id"]
        existing = cloud_map.get(inc_id)
        if not existing:
            cloud_map[inc_id] = rec
        else:
            # Prefer the record that has more data (root_cause > no root_cause)
            if rec.get("root_cause") and not existing.get("root_cause"):
                cloud_map[inc_id] = rec
            # Also prefer longer title/description (metadata quality)
            elif not rec.get("root_cause") and not existing.get("root_cause"):
                if len(rec.get("title", "")) > len(existing.get("title", "")):
                    cloud_map[inc_id] = rec

    # ── 3. Generate embeddings for new cloud records ───────────────────────────
    need_emb = [r for r in cloud_map.values() if not r.get("embedding")]
    if need_emb:
        try:
            model = _get_model()
            texts = [f"{r['title']} {r['description']}" for r in need_emb]
            embs  = model.encode(texts)
            for rec, emb in zip(need_emb, embs):
                rec["embedding"] = emb.tolist()
        except Exception as exc:
            logger.warning("[Hindsight] Embedding generation failed: %s", exc)

    # ── 4. Merge into local JSON ───────────────────────────────────────────────
    local     = _load_memory()
    local_map = {r["incident_id"]: r for r in local}
    added = updated = 0

    for inc_id, rec in cloud_map.items():
        if inc_id not in local_map:
            local_map[inc_id] = rec
            added += 1
        else:
            ex      = local_map[inc_id]
            changed = False

            # Update resolved status if cloud knows it and local doesn't
            cloud_rc = rec.get("root_cause") or ""
            local_rc = ex.get("root_cause") or ""
            if cloud_rc and not local_rc:
                ex["root_cause"]       = cloud_rc
                ex["mitigation_steps"] = rec.get("mitigation_steps") or ex.get("mitigation_steps")
                ex["resolved_at"]      = rec.get("resolved_at") or datetime.now(timezone.utc).isoformat()
                changed = True

            # Update title/description if cloud has better data
            if rec.get("title") and len(rec.get("title", "")) > len(ex.get("title", "") or ""):
                ex["title"] = rec["title"]
                changed = True
            if rec.get("description") and len(rec.get("description", "")) > len(ex.get("description", "") or ""):
                ex["description"] = rec["description"]
                changed = True

            # Fill in missing embedding
            if rec.get("embedding") and not ex.get("embedding"):
                ex["embedding"] = rec["embedding"]
                changed = True

            if changed:
                updated += 1

    final = list(local_map.values())
    _save_memory(final)
    logger.info(
        "[Hindsight] Sync complete — fetched=%d added=%d updated=%d total=%d",
        len(raw_items), added, updated, len(final),
    )
    return {"fetched": len(raw_items), "added": added, "updated": updated, "total": len(final)}


def get_all_incidents_from_cloud() -> List[dict]:
    """Sync from Hindsight Cloud then return the full merged local list.

    NOTE: Expensive — only call from startup lifespan and explicit /sync endpoint.
    For normal reads use get_all_incidents() which reads local JSON only.
    """
    sync_from_hindsight_cloud()
    return _load_memory()


def deduplicate_local_incidents(similarity_threshold: float = 0.97) -> dict:
    """Remove duplicate incidents from local memory.

    Two passes:
      1. Exact-ID dedup: multiple records with same incident_id → keep resolved or newest.
      2. Semantic dedup: title embeddings above similarity_threshold → collapse, keep resolved.

    Returns summary dict: {before, after, removed}.
    """
    records = _load_memory()
    before  = len(records)

    # ── Pass 1: exact incident_id dedup ───────────────────────────────────────
    id_map: dict = {}
    for rec in records:
        inc_id   = rec["incident_id"]
        existing = id_map.get(inc_id)
        if not existing:
            id_map[inc_id] = rec
        else:
            if rec.get("root_cause") and not existing.get("root_cause"):
                id_map[inc_id] = rec
            elif not rec.get("root_cause") and not existing.get("root_cause"):
                try:
                    if rec["created_at"] > existing["created_at"]:
                        id_map[inc_id] = rec
                except Exception:
                    pass

    after_id_dedup = list(id_map.values())
    logger.info(
        "[Dedup] Pass 1 (exact ID): %d → %d (removed %d)",
        before, len(after_id_dedup), before - len(after_id_dedup),
    )

    # ── Pass 2: semantic title dedup ──────────────────────────────────────────
    try:
        model      = _get_model()
        titles     = [r["title"] for r in after_id_dedup]
        title_embs = model.encode(titles)

        norms         = np.linalg.norm(title_embs, axis=1, keepdims=True) + 1e-10
        title_embs_n  = title_embs / norms
        keep_mask     = [True] * len(after_id_dedup)
        n             = len(after_id_dedup)

        for i in range(n):
            if not keep_mask[i]:
                continue
            for j in range(i + 1, n):
                if not keep_mask[j]:
                    continue
                sim = float(np.dot(title_embs_n[i], title_embs_n[j]))
                if sim >= similarity_threshold:
                    ri, rj = after_id_dedup[i], after_id_dedup[j]
                    if rj.get("root_cause") and not ri.get("root_cause"):
                        ri["root_cause"]       = rj["root_cause"]
                        ri["mitigation_steps"] = rj["mitigation_steps"]
                        ri["resolved_at"]      = rj["resolved_at"]
                    keep_mask[j] = False

        after_semantic = [r for r, keep in zip(after_id_dedup, keep_mask) if keep]
        logger.info(
            "[Dedup] Pass 2 (semantic title, thresh=%.2f): %d → %d (removed %d)",
            similarity_threshold,
            len(after_id_dedup), len(after_semantic),
            len(after_id_dedup) - len(after_semantic),
        )
    except Exception as exc:
        logger.warning("[Dedup] Semantic pass skipped: %s", exc)
        after_semantic = after_id_dedup

    _save_memory(after_semantic)
    after = len(after_semantic)
    logger.info("[Dedup] Complete — before=%d after=%d removed=%d", before, after, before - after)
    return {"before": before, "after": after, "removed": before - after}
