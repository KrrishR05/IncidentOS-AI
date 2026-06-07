# IncidentOS AI 🚨

An AI-powered incident management system that learns from every resolved incident.
Built with **FastAPI**, **Groq (llama-3.3-70b-versatile)**, **Hindsight Cloud memory**, and **sentence-transformers**.

---

## What it does

| Feature | Detail |
|---|---|
| **Semantic memory** | Every incident is embedded and stored. Hindsight Cloud is the primary memory layer; local JSON is the offline fallback. |
| **AI analysis** | When a new incident arrives, the LLM opens with "Based on X similar past incidents, root cause: ..." — no generic output. |
| **Confidence scoring** | 0 resolved matches = 20%. 1 = 60%. 2+ = 85%+. |
| **Specific runbooks** | Numbered steps with exact commands, config keys, and thresholds — no vague advice. |
| **Deduplication** | Exact title+description matches are rejected; only one record is created. |
| **Persistence** | Memory survives server restarts. Hindsight Cloud stores all records permanently. |

---

## Quick Start

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd IncidentOS-AI
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Install dependencies

**Linux / macOS (CPU-only, fastest install):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**Windows (CPU-only):**
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
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`

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
- `incident_id` — unique 8-char ID
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

## Utility Scripts

| Script | Purpose |
|---|---|
| `sync_from_hindsight.py` | Pull all records from Hindsight Cloud into local memory using paginated `list_memories()` |
| `check_hindsight.py` | Audit local memory and verify Hindsight Cloud connection |
| `debug_hindsight.py` | Step-by-step diagnostic for Hindsight recall issues |

```bash
# Sync all Hindsight records locally
python sync_from_hindsight.py

# Full replace (clean slate)
python sync_from_hindsight.py --replace

# Check what's in memory
python check_hindsight.py
```

---

## Architecture

```
Client
  │
  ▼
FastAPI (main.py)
  ├── POST /incident/new  ──► memory.store_incident()
  │                            memory.find_similar_incidents()  ◄─ Hindsight recall()
  │                            agent.analyze_incident()         ◄─ Groq LLM
  │                            agent.suggest_actions()
  │
  └── POST /incident/resolve ─► memory.resolve_incident()
                                  Hindsight retain() (updated with root_cause)

Memory Layer (memory.py)
  Primary:   Hindsight Cloud (retain / recall / list_memories)
  Secondary: incident_memory.json (local JSON fallback + embedding cache)

LLM (agent.py)
  Model:  llama-3.3-70b-versatile (via Groq)
  Prompts: prompts.py — SRE persona, confidence scores, no filler phrases
```

---

## Demo Test Sequence

```bash
# 1. Check memory is loaded
curl http://localhost:8000/incidents/all | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]}  Resolved: {d[\"resolved\"]}')"

# 2. Submit incident with no history (confidence should be <40%)
curl -X POST http://localhost:8000/incident/new -H "Content-Type: application/json" \
  -d '{"title":"SSL cert expired","description":"Payment gateway returning 503, SSL handshake failing"}'

# 3. Submit incident with strong history (confidence should be 85%+)
curl -X POST http://localhost:8000/incident/new -H "Content-Type: application/json" \
  -d '{"title":"Database connections rising","description":"DB connections spiking, API latency climbing"}'
```

---

## License

MIT