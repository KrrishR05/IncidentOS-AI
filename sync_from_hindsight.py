"""
sync_from_hindsight.py — Pull ALL records from Hindsight Cloud into IncidentOS.

Uses client.list_memories() with limit+offset pagination (official Hindsight API).
Falls back to 30-query recall() sweep if list_memories is unavailable.

REST endpoint: GET /v1/default/banks/:bank_id/memories/list?limit=100&offset=N

Usage:
  python sync_from_hindsight.py           # merge into local JSON
  python sync_from_hindsight.py --replace # overwrite local JSON completely
"""

import argparse
import json
import os
import re as _re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "incident_memory.json")
BANK_ID     = "incidentos-incidents"
BASE_URL    = "https://api.hindsight.vectorize.io"
PAGE_SIZE   = 100

# 30 broad queries for recall() fallback sweep
SWEEP_QUERIES = [
    "database connection exhaustion incident",
    "API latency spike production outage",
    "connection pool exhaustion root cause",
    "database connections rising API latency",
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


def _load_local() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE) as f:
        return json.load(f)


def _save_local(records: list) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


# ── Strategy 1: list_memories() SDK pagination ───────────────────────────────

def _fetch_via_list_memories(client) -> list:
    """
    Use client.list_memories(bank_id, limit, offset) to page through everything.
    Returns list of raw RecallResult-like objects.
    """
    all_items = []
    offset = 0
    total_hint = None

    print(f"  Using {BOLD}client.list_memories(){RESET} with limit={PAGE_SIZE}, offset pagination")

    while True:
        try:
            result = client.list_memories(
                bank_id=BANK_ID,
                limit=PAGE_SIZE,
                offset=offset,
            )
        except AttributeError:
            print(f"  {YELLOW}list_memories() not available on this SDK version.{RESET}")
            return []
        except Exception as e:
            print(f"  {RED}list_memories() error at offset={offset}: {e}{RESET}")
            break

        # Parse response — may be list or object with .results / .items
        if isinstance(result, list):
            items = result
        elif hasattr(result, "results"):
            items = result.results or []
            if total_hint is None and hasattr(result, "total"):
                total_hint = result.total
        elif hasattr(result, "items"):
            items = result.items or []
            if total_hint is None and hasattr(result, "total"):
                total_hint = result.total
        elif hasattr(result, "memories"):
            items = result.memories or []
        else:
            print(f"  {YELLOW}Unexpected result type: {type(result)} — {result}{RESET}")
            break

        if not items:
            break  # no more pages

        all_items.extend(items)

        # Progress counter
        count_str = str(len(all_items))
        if total_hint:
            count_str += f" / {total_hint}"
        print(f"  {CYAN}Fetched {count_str} records...{RESET}", end="\r", flush=True)

        if len(items) < PAGE_SIZE:
            break  # last page (partial)

        offset += PAGE_SIZE

    print()  # newline
    return all_items


# ── Strategy 2: REST API with httpx ─────────────────────────────────────────

def _fetch_via_rest(api_key: str) -> list:
    """
    Direct REST API call: GET /v1/default/banks/{bank_id}/memories/list
    Uses httpx (already installed via hindsight-client).
    """
    try:
        import httpx
    except ImportError:
        print(f"  {YELLOW}httpx not available — skipping REST strategy.{RESET}")
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # Try known endpoint patterns
    endpoints = [
        f"{BASE_URL}/v1/default/banks/{BANK_ID}/memories/list",
        f"{BASE_URL}/v1/banks/{BANK_ID}/memories/list",
        f"{BASE_URL}/hindsight/contents",
        f"{BASE_URL}/api/v1/memories",
    ]

    working_url = None
    for url in endpoints:
        try:
            r = httpx.get(url, headers=headers,
                          params={"bank_id": BANK_ID, "limit": 1, "offset": 0},
                          timeout=10)
            if r.status_code == 200:
                working_url = url
                print(f"  {GREEN}✅ REST endpoint: {url}{RESET}")
                break
            else:
                print(f"  {DIM}{url} → {r.status_code}{RESET}")
        except Exception as e:
            print(f"  {DIM}{url} → {e}{RESET}")

    if not working_url:
        return []

    all_items = []
    offset = 0
    total_hint = None

    while True:
        try:
            r = httpx.get(working_url, headers=headers,
                          params={"bank_id": BANK_ID, "limit": PAGE_SIZE,
                                  "offset": offset, "q": ""},
                          timeout=30)
        except Exception as e:
            print(f"  {RED}REST request failed at offset={offset}: {e}{RESET}")
            break

        if r.status_code != 200:
            print(f"  {RED}REST {r.status_code} at offset={offset}: {r.text[:200]}{RESET}")
            break

        data = r.json()
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (data.get("items") or data.get("results") or
                     data.get("memories") or data.get("data") or [])
            if total_hint is None:
                total_hint = data.get("total") or data.get("count")
        else:
            break

        if not items:
            break

        all_items.extend(items)
        count_str = str(len(all_items))
        if total_hint:
            count_str += f" / {total_hint}"
        print(f"  {CYAN}Fetched {count_str} records...{RESET}", end="\r", flush=True)

        if len(items) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print()
    return all_items


# ── Strategy 3: recall() sweep ───────────────────────────────────────────────

def _fetch_via_recall_sweep(client) -> list:
    """Fire 30 broad recall() queries and collect unique hits by mem.id."""
    seen_ids: set = set()
    all_hits = []
    n = len(SWEEP_QUERIES)

    for i, q in enumerate(SWEEP_QUERIES, 1):
        try:
            result = client.recall(bank_id=BANK_ID, query=q)
            hits = result.results or []
            new_cnt = 0
            for mem in hits:
                mem_id = str(getattr(mem, "id", ""))
                if mem_id and mem_id not in seen_ids:
                    seen_ids.add(mem_id)
                    all_hits.append(mem)
                    new_cnt += 1
            print(
                f"  [{i:>2}/{n}] {q[:50]:<50}  "
                f"hits={len(hits):>3}  new={new_cnt:>3}  total={CYAN}{len(all_hits)}{RESET}"
            )
        except Exception as e:
            print(f"  [{i:>2}/{n}] {q[:50]:<50}  {YELLOW}error: {e}{RESET}")

    return all_hits


# ── Record parsers ────────────────────────────────────────────────────────────


def _parse_item(item) -> dict | None:
    """Convert a Hindsight memory item (dict or SDK object) into IncidentOS format.

    TWO item types arrive:
      A) recall() result  — SDK RecallResult object with .metadata dict containing our fields
      B) list_memories()  — plain dict with NLP-extracted fact, NO metadata field

    For (A): read incident_id from metadata dict.
    For (B): regex-extract the incident_id from the fact text:
        - "Incident ID d56b2cad: ..."
        - "Incident d56b2cad ..."

    CRITICAL: Items with no identifiable incident_id are SKIPPED (return None).
    Never generate a random UUID — that creates 2000+ duplicate records on every sync.
    """
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

    # ── B: text-extraction path (list_memories() NLP fact items) ─────────────
    if not inc_id and text:
        # Pattern 1: 8-char hex IDs — "Incident ID d56b2cad" or "Incident d56b2cad"
        id_match = _re.search(
            r'[Ii]ncident\s+(?:ID\s+)?([0-9a-f]{8})(?:[^0-9a-f]|$)',
            text,
        )
        if id_match:
            inc_id = id_match.group(1)

        # Pattern 2: INCxxxxxxx IDs — "Incident INC0027946 occurred..."
        if not inc_id:
            inc_match = _re.search(
                r'[Ii]ncident\s+(INC\d+)',
                text,
            )
            if inc_match:
                inc_id = inc_match.group(1)

        # Try to detect root_cause from resolution fact text
        if not root_cause and inc_id:
            rc_match = _re.search(
                r'(?:root cause(?:\s+(?:of|was identified as))?[^.]*?|caused by)\s+'
                r'([A-Za-z][A-Za-z0-9 _,\-]{2,80}?)'
                r'(?:\s+and resolved|\s*\.|$)',
                text, _re.I,
            )
            if rc_match:
                root_cause = rc_match.group(1).strip()

        # Try to detect mitigation from resolution fact text
        if not mitigation and inc_id:
            mit_match = _re.search(
                r'resolved using(?:\s+mitigation(?:\s+step)?)?\s+'
                r'([A-Za-z][A-Za-z0-9 _,\-]{2,120}?)(?:\.|$)',
                text, _re.I,
            )
            if mit_match:
                mitigation = mit_match.group(1).strip()

    # ── CRITICAL: skip items with no identifiable incident_id ─────────────────
    # DO NOT fall back to uuid.uuid4() — that creates a new garbage record for
    # every NLP fact Hindsight extracted, causing ~2000 duplicates per sync run.
    if not inc_id:
        return None

    # ── Build title ───────────────────────────────────────────────────────────
    if not title and text:
        tm = _re.match(r'[Ii]ncident\s+(?:ID\s+)?[0-9a-f]+[:\s]+(.+?)(?:\.|$)', text)
        if tm:
            title = tm.group(1).strip()[:80]
    if not title:
        title = text.split(".")[0].strip()[:80]
    if not title or len(title) < 3:
        return None

    # ── Extract description ───────────────────────────────────────────────────
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main(replace: bool = False) -> None:
    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  sync_from_hindsight.py — Full Paginated Hindsight Sync{RESET}")
    print(f"{BOLD}{'═'*70}{RESET}\n")

    api_key = os.getenv("HINDSIGHT_API_KEY", "")
    if not api_key:
        print(f"{RED}HINDSIGHT_API_KEY not set. Aborting.{RESET}")
        sys.exit(1)

    print(f"  API key : {CYAN}{api_key[:14]}...{api_key[-6:]}{RESET}")
    print(f"  Bank ID : {CYAN}{BANK_ID}{RESET}\n")

    # Connect SDK
    client = None
    try:
        from hindsight_client import Hindsight  # type: ignore
        client = Hindsight(base_url=BASE_URL, api_key=api_key)
        print(f"  {GREEN}✅ Hindsight SDK connected{RESET}")
        avail = [m for m in dir(client) if not m.startswith("_")]
        print(f"  SDK methods: {DIM}{avail}{RESET}\n")
    except Exception as e:
        print(f"  {YELLOW}SDK init warning: {e}{RESET}\n")

    raw_items = []

    # ── Try list_memories() first ─────────────────────────────────────────────
    print(f"{BOLD}[STRATEGY 1] SDK list_memories() — paginated bulk list{RESET}")
    if client:
        raw_items = _fetch_via_list_memories(client)

    # ── Try REST if SDK list failed ───────────────────────────────────────────
    if not raw_items:
        print(f"\n{BOLD}[STRATEGY 2] REST API paginated list{RESET}")
        raw_items = _fetch_via_rest(api_key)

    # ── Fall back to recall() sweep ───────────────────────────────────────────
    if not raw_items:
        print(f"\n{BOLD}[STRATEGY 3] recall() sweep ({len(SWEEP_QUERIES)} queries){RESET}")
        if not client:
            print(f"  {RED}No SDK client. Cannot proceed.{RESET}")
            sys.exit(1)
        raw_items = _fetch_via_recall_sweep(client)

    print(f"\n  {BOLD}Total raw items fetched: {len(raw_items)}{RESET}")

    # ── Parse ─────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Parsing records...{RESET}")
    parsed, skipped = [], 0
    for item in raw_items:
        rec = _parse_item(item)
        if rec:
            parsed.append(rec)
        else:
            skipped += 1
    print(f"  Parsed {GREEN}{len(parsed)}{RESET}   Skipped (meta-facts) {YELLOW}{skipped}{RESET}")

    # ── Dedup (prefer resolved over open) ────────────────────────────────────
    deduped: dict = {}
    for rec in parsed:
        inc_id = rec["incident_id"]
        ex = deduped.get(inc_id)
        if not ex or (rec.get("root_cause") and not ex.get("root_cause")):
            deduped[inc_id] = rec
    unique = list(deduped.values())
    print(f"  After dedup: {BOLD}{len(unique)}{RESET} unique incident IDs")

    # ── Embeddings ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Generating embeddings...{RESET}")
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        model = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [f"{r['title']} {r['description']}" for r in unique]
        embs  = model.encode(texts, batch_size=32, show_progress_bar=True)
        for rec, emb in zip(unique, embs):
            rec["embedding"] = emb.tolist()
        print(f"  {GREEN}✅ {len(unique)} embeddings generated (384-dim){RESET}")
    except Exception as e:
        print(f"  {YELLOW}⚠ Embedding skipped: {e}{RESET}")

    # ── Merge ─────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'Replacing' if replace else 'Merging into'} local memory...{RESET}")
    if replace:
        final = unique
        print(f"  REPLACE mode: {len(unique)} records written")
    else:
        local = _load_local()
        merged: dict = {r["incident_id"]: r for r in local}
        added = updated = 0
        for rec in unique:
            inc_id = rec["incident_id"]
            if inc_id not in merged:
                merged[inc_id] = rec
                added += 1
            else:
                ex = merged[inc_id]
                changed = False
                if rec.get("root_cause") and not ex.get("root_cause"):
                    ex["root_cause"]       = rec["root_cause"]
                    ex["mitigation_steps"] = rec.get("mitigation_steps")
                    ex["resolved_at"]      = rec.get("resolved_at")
                    changed = True
                if rec.get("embedding") and not ex.get("embedding"):
                    ex["embedding"] = rec["embedding"]
                    changed = True
                if changed:
                    updated += 1
        final = list(merged.values())
        print(f"  Added: {GREEN}{added}{RESET}  Updated: {CYAN}{updated}{RESET}  Total: {BOLD}{len(final)}{RESET}")

    _save_local(final)
    print(f"  {GREEN}✅ Saved → {MEMORY_FILE}{RESET}")

    # ── Summary ───────────────────────────────────────────────────────────────
    resolved_lst   = [r for r in final if r.get("root_cause")]
    unresolved_lst = [r for r in final if not r.get("root_cause")]
    with_emb       = sum(1 for r in final if r.get("embedding"))

    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  SYNC SUMMARY{RESET}")
    print(f"{BOLD}{'═'*70}{RESET}")
    print(f"  Fetched from Hindsight Cloud : {BOLD}{len(raw_items)}{RESET}")
    print(f"  Written to local memory      : {BOLD}{len(final)}{RESET}")
    print(f"  ├─ Resolved (root_cause set) : {GREEN}{BOLD}{len(resolved_lst)}{RESET}")
    print(f"  └─ Open (no root cause)      : {YELLOW}{BOLD}{len(unresolved_lst)}{RESET}")
    print(f"  Embeddings ready             : {CYAN}{with_emb}{RESET} / {len(final)}")

    if resolved_lst:
        print(f"\n  {BOLD}Resolved incidents:{RESET}")
        for r in resolved_lst:
            print(f"    {GREEN}✅{RESET} [{r['incident_id']}] {r['title'][:55]}")
            print(f"         root_cause : {r.get('root_cause')}")
            print(f"         mitigation : {(r.get('mitigation_steps') or '—')[:65]}")

    if not raw_items:
        print(f"\n  {YELLOW}⚠ 0 records fetched. Possible reasons:")
        print(f"    1. API key '{api_key[:14]}...{api_key[-6:]}' may not match the bank where data was stored.")
        print(f"    2. Bank ID '{BANK_ID}' may be empty or wrong.")
        print(f"    3. Check ui.hindsight.vectorize.io to confirm which bank has your data.{RESET}")

    print(f"\n{BOLD}{'═'*70}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true",
                        help="Replace local JSON entirely (default: merge/upsert)")
    args = parser.parse_args()
    main(replace=args.replace)
