# IncidentOS AI 🚨

An AI-powered incident management system that learns from every resolved incident.
Built with **FastAPI**, **Groq (llama-3.3-70b-versatile)**, **Hindsight Cloud memory**, and **sentence-transformers**.

---

## What it does

| Feature | Detail |
|---|---|
| **Semantic memory** | Every incident is embedded (384-dim, `all-MiniLM-L6-v2`) and stored. Hindsight Cloud is the primary memory layer; local JSON is the offline fallback. |
| **AI analysis** | When a new incident arrives, the LLM opens with "Based on X similar past incidents, root cause: …" — no generic output. |
| **Confidence scoring** | 0 resolved matches = 20%. 1 = 60%. 2+ = 85%+. |
| **Specific runbooks** | Numbered steps with exact commands, config keys, and thresholds — no vague advice. |
| **Deduplication** | Exact title+description matches are rejected; only one record is created per incident. |
| **Persistence** | Memory survives server restarts. Hindsight Cloud stores all records permanently with full metadata. |
| **Bulk resolution** | `bulk_resolve.py` classifies all open incidents by failure type and resolves them in one shot via `retain_batch()`. |
| **Cloud sync** | `sync_from_hindsight.py` pulls everything from Hindsight using paginated `list_memories()` — supports both 8-char hex IDs and `INC0XXXXX` dataset IDs. |

---

## Quick Start

### 1. Clone and create virtual environment

```bash
git clone https://github.com/KrrishR05/IncidentOS-AI.git
cd IncidentOS-AI
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Install dependencies

**Linux / macOS / Windows (CPU-only):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**With GPU support:**
```bash
pip install -r requirements.txt   # torch auto-detects CUDA
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
HINDSIGHT_API_KEY=hsk_your_hindsight_api_key_here
```

Get your keys:
- **Groq**: https://console.groq.com
- **Hindsight**: https://hindsight.vectorize.io

### 4. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Server starts at `http://localhost:8000`. On startup it automatically syncs all records from Hindsight Cloud.

---

## API Endpoints

### `POST /incident/new`
Submit a new incident for AI analysis.

```bash
curl -X POST http://localhost:8000/incident/new \
  -H "Content-Type: application/json" \
  -d '{"title":"DB connection exhaustion","description":"API latency spiked, database connections maxed out"}'
```

**Response includes:**
- `incident_id` — unique ID (8-char hex for new incidents, `INC0XXXXX` for dataset incidents)
- `ai_analysis` — SRE-style analysis with confidence score and runbook
- `similar_past_incidents` — top 3 semantically similar past incidents
- `suggested_actions` — 4 specific, prioritised runbook steps

---

### `POST /incident/resolve`
Mark an incident as resolved with root cause and mitigation.

```bash
curl -X POST http://localhost:8000/incident/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "4e6a6f1b",
    "root_cause": "connection pool exhaustion",
    "mitigation_steps": "increased pool size, added timeout config, restarted pods"
  }'
```

---

### `GET /incidents/all`
Returns all incidents in memory with total/resolved/open counts.

```bash
curl http://localhost:8000/incidents/all | python3 -m json.tool
```

---

### `GET /incident/{id}`
Fetch a single incident by ID.

```bash
curl http://localhost:8000/incident/4e6a6f1b
```

---

### `GET /status`
Health check for backend, Groq LLM, and Hindsight Cloud connectivity.

```bash
curl http://localhost:8000/status
```

---

### `POST /sync`
Trigger a manual cloud sync (pulls latest from Hindsight, merges into local JSON).

```bash
curl -X POST http://localhost:8000/sync
```

---

### `POST /deduplicate`
Run semantic deduplication pass over local memory (merges near-identical incidents).

```bash
curl -X POST http://localhost:8000/deduplicate
```

---

## Utility Scripts

| Script | Purpose |
|---|---|
| `sync_from_hindsight.py` | Pull all records from Hindsight Cloud into local memory using paginated `list_memories()` |
| `check_hindsight.py` | Audit local memory: shows all incidents, resolved/open counts, embedding stats, and a live recall ping |
| `debug_hindsight.py` | Step-by-step Hindsight diagnostic — inspects raw recall response structure, metadata fields, and retain() support |
| `bulk_resolve.py` | Classify all open incidents by failure category and resolve them in bulk; pushes to Hindsight via `retain_batch()` |

```bash
# Merge new records from Hindsight into local memory
python sync_from_hindsight.py

# Full replace (wipes local JSON, rebuilds entirely from Hindsight)
python sync_from_hindsight.py --replace

# Audit what's in local memory + live cloud check
python check_hindsight.py

# Deep Hindsight recall diagnostic
python debug_hindsight.py

# Dry-run: show what bulk_resolve would do
python bulk_resolve.py

# Actually resolve all open incidents and push to Hindsight
python bulk_resolve.py --commit
```

---

## Architecture

```
HTTP Client
  │
  ▼
FastAPI (main.py)
  ├── POST /incident/new     ──► memory.store_incident()
  │                               memory.find_similar_incidents()  ◄─ Hindsight recall()
  │                               agent.analyze_incident()         ◄─ Groq LLM (llama-3.3-70b)
  │                               agent.suggest_actions()
  │
  ├── POST /incident/resolve ──► memory.resolve_incident()
  │                               Hindsight retain() (updated metadata: root_cause, status)
  │
  ├── GET  /incident/{id}    ──► memory.get_incident_by_id()
  ├── POST /sync             ──► memory.sync_from_hindsight_cloud()
  └── POST /deduplicate      ──► memory.deduplicate_incidents()

Memory Layer (memory.py)
  Primary:   Hindsight Cloud  — retain() / recall() / list_memories() / retain_batch()
  Secondary: incident_memory.json — local JSON fallback, embedding cache, truth store
  Embeddings: sentence-transformers/all-MiniLM-L6-v2  (384-dim)
  Dedup:      Exact ID match  +  semantic cosine similarity (threshold 0.97)

LLM (agent.py)
  Model:   llama-3.3-70b-versatile (via Groq API)
  Persona: SRE on-call engineer — no filler phrases, confidence-scored output
  Prompts: prompts.py
```

---

## Sync Strategy

`sync_from_hindsight_cloud()` in `memory.py` runs on server startup and on `POST /sync`:

1. **`list_memories()`** — paginated bulk fetch of all Hindsight items (up to 4500+)
2. **Recall sweep** — 30 broad queries to surface metadata-rich records missed by the list
3. **ID extraction** — supports both `[0-9a-f]{8}` hex IDs and `INC\d+` dataset IDs via regex
4. **Merge** — prefers resolved status over open; never overwrites a resolved record with an open one
5. **Dedup** — exact ID match collapses duplicates; semantic pass merges near-identical titles

> **Critical fix (v2):** `sync_from_hindsight.py` previously generated a random `uuid4()` for every
> NLP fact Hindsight extracted, creating ~2000 garbage duplicates per sync run. This is now fixed —
> items with no parseable incident ID are skipped entirely.

---

## Bulk Resolution

`bulk_resolve.py` classifies open incidents into 13 failure categories:

| Category | Incidents |
|---|---|
| Load balancer misconfiguration | 257 |
| Third-party API outage | 138 |
| Cache cluster failure | 138 |
| Database connection pool exhaustion | 81 |
| Failed deployment / regression | 73 |
| DNS resolution failure | 69 |
| CPU saturation | 65 |
| Memory leak (OOM) | 63 |
| Expired SSL/TLS certificate | 57 |
| Disk space exhaustion | 32 |
| Database degradation | 11 |
| Latency / timeout | 1 |

Each category gets a realistic `root_cause` + `mitigation_steps`. All resolved records are pushed to Hindsight using `retain_batch()` in batches of 50.

**Current state: 1,019 / 1,019 incidents resolved (100%), all Hindsight-synced.**

---

## Demo Test Sequence

```bash
# 1. Check memory is loaded
curl http://localhost:8000/incidents/all | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]}  Resolved: {d[\"resolved\"]}')"

# 2. Submit incident with strong history (confidence 85%+)
curl -X POST http://localhost:8000/incident/new \
  -H "Content-Type: application/json" \
  -d '{"title":"Database connections rising","description":"DB connections spiking, API latency climbing"}'

# 3. Resolve the incident
curl -X POST http://localhost:8000/incident/resolve \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"<id from step 2>","root_cause":"connection pool exhaustion","mitigation_steps":"increased pool size"}'

# 4. Manually trigger a cloud sync
curl -X POST http://localhost:8000/sync

# 5. Check health
curl http://localhost:8000/status
```

---

## License

MIT