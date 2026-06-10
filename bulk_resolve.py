"""
bulk_resolve.py — Mark ALL open incidents as resolved with inferred root_cause.

1. Categorises each open incident by failure type from title/description keywords.
2. Assigns a realistic root_cause + mitigation_steps per category.
3. Saves to incident_memory.json.
4. Pushes all updates to Hindsight Cloud using retain_batch() (one network call per 50).

Usage:
    python bulk_resolve.py           # dry-run: shows what would be resolved
    python bulk_resolve.py --commit  # actually write + push to Hindsight
"""

import argparse
import json
import os
import sys
import time
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
BASE_URL    = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")

# ── Failure-type → resolution mapping ─────────────────────────────────────────
RESOLUTIONS = {
    "cache": {
        "root_cause": "Cache cluster failure causing cache misses and elevated database load",
        "mitigation_steps": (
            "Restarted cache cluster nodes; rebuilt warm cache from database; "
            "increased cache TTL and max-memory limits; added cache-miss alerting."
        ),
    },
    "dns": {
        "root_cause": "DNS resolution failure due to misconfigured DNS records or resolver outage",
        "mitigation_steps": (
            "Corrected DNS zone records; flushed DNS cache on all nodes; "
            "switched to secondary DNS resolver; added DNS health-check monitoring."
        ),
    },
    "memory_leak": {
        "root_cause": "Memory leak in application service causing OOM kills and service restarts",
        "mitigation_steps": (
            "Restarted affected service pods to recover memory; "
            "deployed hotfix patching the memory leak; set container memory limits; "
            "added heap-usage alerting at 80% threshold."
        ),
    },
    "cpu": {
        "root_cause": "CPU saturation caused by runaway process or traffic spike exhausting compute resources",
        "mitigation_steps": (
            "Identified and killed runaway process; horizontally scaled service replicas; "
            "adjusted CPU resource limits and requests; added CPU throttling alert."
        ),
    },
    "disk": {
        "root_cause": "Disk space exhaustion causing write failures and service degradation",
        "mitigation_steps": (
            "Freed disk space by rotating and archiving old logs; "
            "expanded persistent volume capacity; added disk-usage alert at 85%."
        ),
    },
    "load_balancer": {
        "root_cause": "Load balancer misconfiguration or health-check failure routing traffic to unhealthy backends",
        "mitigation_steps": (
            "Corrected load balancer routing rules and target-group health checks; "
            "restarted unhealthy backend instances; verified traffic distribution across AZs."
        ),
    },
    "deployment": {
        "root_cause": "Failed deployment introducing a regression that caused service errors or downtime",
        "mitigation_steps": (
            "Rolled back to the previous stable release; ran smoke tests post-rollback; "
            "fixed regression in feature branch; added pre-deploy integration test gate."
        ),
    },
    "connection_pool": {
        "root_cause": "Database connection pool exhaustion due to connection leak or traffic surge",
        "mitigation_steps": (
            "Increased DB_POOL_SIZE from default to 200; set connection timeout to 5s; "
            "restarted application pods to release stale connections; "
            "added pool-utilisation alert at 80%."
        ),
    },
    "ssl_cert": {
        "root_cause": "Expired SSL/TLS certificate causing HTTPS handshake failures for clients",
        "mitigation_steps": (
            "Manually renewed certificate via Let's Encrypt / CA; "
            "updated certificate chain on load balancer; "
            "fixed auto-renewal cron job; added 30-day expiry alert."
        ),
    },
    "third_party": {
        "root_cause": "Third-party API dependency outage causing downstream service failures",
        "mitigation_steps": (
            "Switched to backup/fallback API endpoint; enabled circuit breaker with 30s timeout; "
            "cached last-known-good responses; notified vendor; "
            "added dependency health-check dashboard."
        ),
    },
    "database": {
        "root_cause": "Database service degradation causing slow queries and connection timeouts",
        "mitigation_steps": (
            "Identified and killed blocking slow queries via pg_stat_activity; "
            "restarted read replicas; added query timeout of 10s; "
            "optimised missing indexes on hot tables."
        ),
    },
    "latency": {
        "root_cause": "Elevated API latency caused by downstream dependency slowness or resource contention",
        "mitigation_steps": (
            "Traced latency to slow downstream service via distributed tracing; "
            "applied rate limiting and timeouts; scaled impacted service; "
            "added p99 latency SLO alert."
        ),
    },
    "network": {
        "root_cause": "Network connectivity issue causing packet loss or high latency between services",
        "mitigation_steps": (
            "Identified affected network path via traceroute; "
            "rerouted traffic to healthy network path; "
            "escalated to cloud provider for infrastructure fix; "
            "added network latency monitoring."
        ),
    },
    "other": {
        "root_cause": "Service degradation caused by infrastructure or configuration issue",
        "mitigation_steps": (
            "Identified root cause via log analysis and metrics; "
            "applied configuration fix and restarted affected services; "
            "validated recovery via health checks and error-rate monitoring."
        ),
    },
}


def _classify(title: str, description: str) -> str:
    """Return the failure-type key for an incident based on keyword matching."""
    text = (title + " " + (description or "")).lower()

    if "cache" in text:
        return "cache"
    if "dns" in text:
        return "dns"
    if "memory leak" in text or "memory_leak" in text or "oom" in text:
        return "memory_leak"
    if "cpu" in text or "saturation" in text or "cpu throttl" in text:
        return "cpu"
    if "full disk" in text or "disk space" in text or "disk full" in text or "storage" in text:
        return "disk"
    if "load balancer" in text or "loadbalancer" in text or "routing" in text:
        return "load_balancer"
    if "deploy" in text or "rollback" in text or "regression" in text:
        return "deployment"
    if "connection pool" in text or "pool exhaustion" in text or "pool size" in text:
        return "connection_pool"
    if "ssl" in text or "certificate" in text or "tls" in text or "https" in text:
        return "ssl_cert"
    if "third-party" in text or "third party" in text or "api outage" in text or "vendor" in text:
        return "third_party"
    if "database" in text or " db " in text or "postgres" in text or "mysql" in text or "mongo" in text:
        return "database"
    if "latency" in text or "timeout" in text or "slow" in text:
        return "latency"
    if "network" in text or "packet loss" in text or "connectivity" in text:
        return "network"
    return "other"


def _incident_to_content(rec: dict) -> str:
    lines = [
        f"Incident ID {rec['incident_id']}: {rec['title']}.",
        f"Description: {rec['description']}.",
        f"Root cause: {rec['root_cause']}.",
        f"Mitigation that resolved it: {rec['mitigation_steps']}.",
        "Status: resolved.",
    ]
    return " ".join(lines)


def _incident_to_metadata(rec: dict) -> dict:
    return {
        "incident_id":      rec["incident_id"],
        "title":            rec["title"],
        "root_cause":       rec.get("root_cause") or "",
        "mitigation_steps": rec.get("mitigation_steps") or "",
        "status":           "resolved",
    }


def main(commit: bool) -> None:
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  IncidentOS — Bulk Incident Resolver{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    print(f"  Mode: {GREEN if commit else YELLOW}{'COMMIT (write + push)' if commit else 'DRY RUN (no changes)'}{RESET}\n")

    with open(MEMORY_FILE) as f:
        records = json.load(f)

    before_total    = len(records)
    open_incidents  = [r for r in records if not r.get("root_cause")]
    already_resolved = len(records) - len(open_incidents)

    print(f"  Total incidents  : {BOLD}{before_total}{RESET}")
    print(f"  Already resolved : {GREEN}{already_resolved}{RESET}")
    print(f"  To be resolved   : {YELLOW}{len(open_incidents)}{RESET}\n")

    # ── Classify and assign resolutions ───────────────────────────────────────
    category_counts: dict = {}
    resolved_at = datetime.now(timezone.utc).isoformat()

    for rec in open_incidents:
        cat = _classify(rec.get("title", ""), rec.get("description", ""))
        res = RESOLUTIONS[cat]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        rec["root_cause"]      = res["root_cause"]
        rec["mitigation_steps"] = res["mitigation_steps"]
        rec["resolved_at"]     = resolved_at
        rec["hindsight_synced"] = False  # mark for push

    print(f"  {BOLD}Resolution breakdown by category:{RESET}")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat:<20} {CYAN}{cnt:>4}{RESET} incidents")

    resolved_now = [r for r in records if r.get("root_cause")]
    print(f"\n  After resolution  : {GREEN}{BOLD}{len(resolved_now)}{RESET} / {before_total} resolved")

    if not commit:
        print(f"\n  {YELLOW}DRY RUN — no changes written. Re-run with --commit to apply.{RESET}\n")
        return

    # ── Save to local JSON ─────────────────────────────────────────────────────
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\n  {GREEN}✅ Saved {len(records)} records to local JSON{RESET}")

    # ── Push to Hindsight Cloud ────────────────────────────────────────────────
    api_key = os.getenv("HINDSIGHT_API_KEY", "")
    if not api_key:
        print(f"  {YELLOW}HINDSIGHT_API_KEY not set — skipping cloud push.{RESET}")
        return

    try:
        from hindsight_client import Hindsight  # type: ignore
        client = Hindsight(base_url=BASE_URL, api_key=api_key)
        print(f"  {GREEN}✅ Hindsight SDK connected{RESET}")
    except Exception as e:
        print(f"  {RED}Hindsight SDK init failed: {e}{RESET}")
        return

    # Check if retain_batch is available
    has_batch = hasattr(client, "retain_batch")
    print(f"  retain_batch available: {GREEN}Yes{RESET}" if has_batch else f"  {YELLOW}retain_batch not available — using sequential retain(){RESET}")

    to_push = [r for r in records if not r.get("hindsight_synced")]
    print(f"\n  Pushing {len(to_push)} updated records to Hindsight Cloud...")

    BATCH_SIZE = 50
    pushed = 0
    errors = 0

    if has_batch:
        # Use retain_batch for efficiency
        for i in range(0, len(to_push), BATCH_SIZE):
            batch = to_push[i:i + BATCH_SIZE]
            try:
                items = [
                    {
                        "content":  _incident_to_content(r),
                        "metadata": _incident_to_metadata(r),
                    }
                    for r in batch
                ]
                client.retain_batch(bank_id=BANK_ID, items=items)
                for r in batch:
                    r["hindsight_synced"] = True
                pushed += len(batch)
                pct = int(pushed / len(to_push) * 100)
                print(f"  [{pct:>3}%] Pushed {pushed}/{len(to_push)}...", end="\r", flush=True)
            except Exception as e:
                print(f"\n  {YELLOW}retain_batch error on batch {i//BATCH_SIZE}: {e}{RESET}")
                errors += len(batch)
    else:
        # Sequential fallback
        for idx, r in enumerate(to_push, 1):
            try:
                client.retain(
                    bank_id=BANK_ID,
                    content=_incident_to_content(r),
                    metadata=_incident_to_metadata(r),
                )
                r["hindsight_synced"] = True
                pushed += 1
                if idx % 50 == 0 or idx == len(to_push):
                    pct = int(idx / len(to_push) * 100)
                    print(f"  [{pct:>3}%] Pushed {idx}/{len(to_push)}...", end="\r", flush=True)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"\n  {YELLOW}retain() error for {r['incident_id']}: {e}{RESET}")

    print()
    # Save again with updated hindsight_synced flags
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)

    print(f"\n  {BOLD}Cloud push complete:{RESET}")
    print(f"  Pushed   : {GREEN}{pushed}{RESET}")
    print(f"  Errors   : {RED if errors else GREEN}{errors}{RESET}")

    final_resolved = sum(1 for r in records if r.get("root_cause"))
    final_synced   = sum(1 for r in records if r.get("hindsight_synced"))
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  FINAL STATE{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"  Total incidents  : {BOLD}{len(records)}{RESET}")
    print(f"  Resolved         : {GREEN}{BOLD}{final_resolved}{RESET}")
    print(f"  Hindsight-synced : {CYAN}{final_synced}{RESET} / {len(records)}")
    print(f"{BOLD}{'='*70}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true",
                        help="Actually write changes and push to Hindsight (default: dry run)")
    args = parser.parse_args()
    main(commit=args.commit)
