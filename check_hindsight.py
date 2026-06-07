"""
check_hindsight.py — Diagnostic script for IncidentOS memory layer.

Does three things:
  1. Lists all incidents (local JSON + verifies Hindsight recall)
  2. Prints resolved vs unresolved counts
  3. Prints the raw embedding vector of one incident

Usage:
  python check_hindsight.py
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ── Load local JSON ──────────────────────────────────────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "incident_memory.json")

if not os.path.exists(MEMORY_FILE):
    print("❌  incident_memory.json not found. No incidents stored locally yet.")
    sys.exit(1)

with open(MEMORY_FILE) as f:
    records = json.load(f)

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
DIM    = "\033[2m"

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — List all incidents
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*72}{RESET}")
print(f"{BOLD}  IncidentOS — Memory Audit{RESET}")
print(f"{BOLD}{'═'*72}{RESET}")
print(f"\n{BOLD}[1] All incidents in local memory ({len(records)} total):{RESET}\n")
print(f"  {'ID':<12} {'TITLE':<45} {'STATUS':<12} {'ROOT CAUSE'}")
print(f"  {'-'*10} {'-'*43} {'-'*10} {'-'*30}")

for rec in records:
    status = "resolved" if rec.get("root_cause") else "open"
    status_color = GREEN if status == "resolved" else YELLOW
    synced = "✅" if rec.get("hindsight_synced") else "⬜"
    root_cause = (rec.get("root_cause") or "—")[:30]
    title = rec["title"][:43]
    print(
        f"  {synced}{rec['incident_id']:<10} "
        f"{title:<45} "
        f"{status_color}{status:<12}{RESET} "
        f"{root_cause}"
    )

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Counts
# ════════════════════════════════════════════════════════════════════════════
resolved   = [r for r in records if r.get("root_cause")]
unresolved = [r for r in records if not r.get("root_cause")]
synced_cnt = sum(1 for r in records if r.get("hindsight_synced"))

print(f"\n{BOLD}[2] Summary:{RESET}")
print(f"  Total incidents  : {BOLD}{len(records)}{RESET}")
print(f"  Resolved         : {GREEN}{BOLD}{len(resolved)}{RESET}")
print(f"  Unresolved       : {YELLOW}{BOLD}{len(unresolved)}{RESET}")
print(f"  Hindsight-synced : {CYAN}{BOLD}{synced_cnt}{RESET} / {len(records)}")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Raw embedding vector of one incident
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}[3] Raw embedding vector (first incident with embedding):{RESET}")

sample = next((r for r in records if r.get("embedding")), None)
if sample:
    emb = sample["embedding"]
    print(f"  Incident  : {sample['incident_id']} — {sample['title'][:60]}")
    print(f"  Dimensions: {len(emb)}")
    print(f"  First 10  : {[round(v, 6) for v in emb[:10]]}")
    print(f"  Last  10  : {[round(v, 6) for v in emb[-10:]]}")
    print(f"  Min / Max : {round(min(emb), 6)} / {round(max(emb), 6)}")
else:
    print(f"  {RED}No embeddings found in local memory.{RESET}")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Live Hindsight recall ping
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}[4] Hindsight Cloud — live recall check:{RESET}")

api_key = os.getenv("HINDSIGHT_API_KEY", "")
if not api_key or "your_hindsight" in api_key:
    print(f"  {YELLOW}HINDSIGHT_API_KEY not configured — skipping live check.{RESET}")
else:
    try:
        from hindsight_client import Hindsight  # type: ignore

        client = Hindsight(
            base_url="https://api.hindsight.vectorize.io",
            api_key=api_key,
        )
        BANK = "incidentos-incidents"

        # Try a broad recall that should return any stored incident
        result = client.recall(bank_id=BANK, query="database connection exhaustion incident")
        hits = result.results or []

        print(f"  Bank ID  : {CYAN}{BANK}{RESET}")
        print(f"  Query    : 'database connection exhaustion incident'")
        print(f"  Results  : {BOLD}{len(hits)}{RESET} records returned from Hindsight\n")

        if hits:
            print(f"  {'#':<4} {'TEXT PREVIEW':<60} SCORE")
            print(f"  {'-'*3} {'-'*58} {'-'*8}")
            for i, mem in enumerate(hits[:5], 1):
                preview = (mem.text or "").replace("\n", " | ")[:58]
                score = getattr(mem, "score", "N/A")
                score_str = f"{score:.4f}" if isinstance(score, float) else str(score)
                print(f"  {i:<4} {preview:<60} {score_str}")
        else:
            print(f"  {YELLOW}⚠ Hindsight returned 0 results. "
                  f"Records may still be processing (Hindsight uses async indexing).{RESET}")

        # Second recall to confirm resolution data is stored
        result2 = client.recall(bank_id=BANK, query="connection pool exhaustion root cause")
        hits2 = result2.results or []
        print(f"\n  Query    : 'connection pool exhaustion root cause'")
        print(f"  Results  : {BOLD}{len(hits2)}{RESET} records returned")
        if hits2:
            print(f"  First hit: {(hits2[0].text or '').replace(chr(10), ' | ')[:80]}")

    except ImportError:
        print(f"  {RED}hindsight-client not installed. Run: pip install hindsight-client{RESET}")
    except Exception as e:
        print(f"  {RED}Hindsight recall failed: {e}{RESET}")

print(f"\n{BOLD}{'═'*72}{RESET}\n")
