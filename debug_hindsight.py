"""
debug_hindsight.py — Step-by-step diagnostic for Hindsight recall.

Prints raw API requests and raw responses at every step.
Run: python debug_hindsight.py
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

BANK_ID_STORE   = "incidentos-incidents"   # what memory.py uses for retain()
BANK_ID_QUERY   = "incidentos-incidents"   # what memory.py uses for recall()
BASE_URL        = "https://api.hindsight.vectorize.io"

print(f"\n{BOLD}{'═'*70}{RESET}")
print(f"{BOLD}  Hindsight Recall Diagnostic — Step-by-Step{RESET}")
print(f"{BOLD}{'═'*70}{RESET}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Bank ID check
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}STEP 1 — Bank ID Verification{RESET}")
print(f"  retain() bank_id  : {CYAN}{BANK_ID_STORE}{RESET}")
print(f"  recall() bank_id  : {CYAN}{BANK_ID_QUERY}{RESET}")
if BANK_ID_STORE == BANK_ID_QUERY:
    print(f"  {GREEN}✅ Bank IDs match.{RESET}")
else:
    print(f"  {RED}❌ Bank IDs MISMATCH — this is the bug!{RESET}")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Raw recall response structure
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}STEP 2 — Raw Hindsight recall() response structure{RESET}")

api_key = os.getenv("HINDSIGHT_API_KEY", "")
if not api_key:
    print(f"  {RED}HINDSIGHT_API_KEY not set. Aborting.{RESET}")
    sys.exit(1)

try:
    from hindsight_client import Hindsight  # type: ignore
    client = Hindsight(base_url=BASE_URL, api_key=api_key)
    print(f"  {GREEN}✅ Hindsight client created.{RESET}")
except Exception as e:
    print(f"  {RED}Failed to create client: {e}{RESET}")
    sys.exit(1)

query_text = "database connections maxed out, API latency high"
print(f"\n  Sending recall():")
print(f"    bank_id : {CYAN}{BANK_ID_QUERY}{RESET}")
print(f"    query   : {CYAN}{query_text!r}{RESET}")

try:
    result = client.recall(bank_id=BANK_ID_QUERY, query=query_text)
    hits = result.results or []
    print(f"\n  Raw response type : {type(result)}")
    print(f"  result.results    : {type(hits)} with {len(hits)} items")

    print(f"\n  {BOLD}Full structure of first 3 result objects:{RESET}")
    for i, mem in enumerate(hits[:3], 1):
        print(f"\n  [{i}] type(mem)  = {type(mem)}")
        print(f"      dir(mem)   = {[a for a in dir(mem) if not a.startswith('_')]}")
        print(f"      mem.text   = {repr((mem.text or '')[:120])}")
        print(f"      mem.id     = {getattr(mem, 'id', 'N/A')}")
        print(f"      mem.type   = {getattr(mem, 'type', 'N/A')}")
        print(f"      mem.metadata  = {getattr(mem, 'metadata', 'N/A')}")
        print(f"      mem.context   = {getattr(mem, 'context', 'N/A')}")
        print(f"      mem.entities  = {getattr(mem, 'entities', 'N/A')}")
        print(f"      mem.tags      = {getattr(mem, 'tags', 'N/A')}")
        # Try to get the full dict representation
        try:
            as_dict = mem.model_dump() if hasattr(mem, 'model_dump') else vars(mem)
            print(f"      full dict  = {json.dumps(as_dict, default=str, indent=8)[:400]}")
        except Exception:
            pass

except Exception as e:
    print(f"  {RED}recall() failed: {e}{RESET}")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Check if incident_id is in metadata
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}STEP 3 — Check metadata field for incident_id{RESET}")
found_via_metadata = 0
found_via_text_parse = 0

for mem in hits:
    meta = getattr(mem, 'metadata', None) or {}
    if isinstance(meta, dict) and meta.get('incident_id'):
        found_via_metadata += 1
    text = mem.text or ""
    if "incident_id:" in text:
        found_via_text_parse += 1

print(f"  Results with incident_id in metadata : {found_via_metadata} / {len(hits)}")
print(f"  Results with 'incident_id:' in text  : {found_via_text_parse} / {len(hits)}")

if found_via_metadata == 0 and found_via_text_parse == 0:
    print(f"\n  {YELLOW}⚠ Root cause confirmed: incident_id is not findable in recall results.")
    print(f"  Hindsight extracts facts from text — it does NOT preserve raw lines.")
    print(f"  Fix: Pass incident_id in the metadata= dict parameter of retain().{RESET}")
elif found_via_metadata > 0:
    print(f"\n  {GREEN}✅ incident_id found via metadata. Recall parsing can use metadata['incident_id'].{RESET}")
else:
    print(f"\n  {YELLOW}⚠ incident_id found via text parsing. Metadata approach not yet in use.{RESET}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — Test retain with metadata, then immediately recall
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}STEP 4 — Test retain() with metadata={{}}, then recall(){RESET}")
print(f"  Storing a test incident with metadata parameter...")

TEST_ID = "debug-test-001"
try:
    client.retain(
        bank_id=BANK_ID_STORE,
        content=(
            "DB connection exhaustion test incident. "
            "API latency spiked to 8 seconds. Database connections maxed out at 500. "
            "Auth service failing. Root cause: connection pool exhaustion. "
            "Mitigation: increased pool size, added timeout config, restarted pods. "
            "Status: resolved."
        ),
        metadata={"incident_id": TEST_ID, "root_cause": "connection pool exhaustion", "status": "resolved"},
    )
    print(f"  {GREEN}✅ retain() with metadata succeeded  id={TEST_ID}{RESET}")
except TypeError as e:
    print(f"  {YELLOW}⚠ metadata param not supported by this SDK version: {e}{RESET}")
    print(f"  Will fall back to text-only retain().")
except Exception as e:
    print(f"  {RED}retain() failed: {e}{RESET}")

print(f"\n  Waiting 2 seconds for Hindsight to index...")
import time; time.sleep(2)

print(f"  Recalling with query: 'connection pool exhaustion database'")
try:
    r2 = client.recall(bank_id=BANK_ID_QUERY, query="connection pool exhaustion database")
    hits2 = r2.results or []
    print(f"  Results: {len(hits2)}")
    for mem in hits2[:3]:
        meta = getattr(mem, 'metadata', {}) or {}
        print(f"    text={repr((mem.text or '')[:80])}  metadata={meta}")
except Exception as e:
    print(f"  {RED}recall() failed: {e}{RESET}")

print(f"\n{BOLD}{'═'*70}{RESET}")
print(f"{BOLD}DIAGNOSIS COMPLETE{RESET}")
print(f"{'═'*70}\n")
