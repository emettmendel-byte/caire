# CAIRE — Clinical AI for Rule-based Execution

A **guideline-to-decision-tree compiler** for general medical triage. CAIRE turns clinical guidelines (e.g. PDFs or text) into structured decision trees that can be reviewed, edited, and executed.

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CAIRE project                            │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│  frontend/  │  backend/   │  shared/    │  guidelines/  models/  │
│  (React)    │  (FastAPI)  │  (schemas)  │  (PDFs/docs)  (JSON)   │
├─────────────┴─────────────┴─────────────┴───────────────────────┤
│  React + Vite     FastAPI + SQLite     Pydantic decision tree   │
│  Authoring UI     Compiler + CRUD      types (shared contract)  │
└─────────────────────────────────────────────────────────────────┘
```

- **Backend** (`/backend`): FastAPI service with:
  - **Guideline ingestion**: upload PDFs, extract text, store in SQLite.
  - **Tree generation**: compile guideline content into a decision tree (stub logic; extend with your own parsing/NLP).
  - **CRUD**: create, read, update, delete decision trees; optional storage in `/models` as versioned JSON.

- **Frontend** (`/frontend`): React app (Vite + TypeScript) for viewing and editing decision trees. Lists trees from the API and shows a simple tree view.

- **Shared** (`/shared`): Pydantic schemas for the decision tree (nodes, edges, types). Single source of truth for the API contract; frontend mirrors types in TypeScript.

- **Database**: SQLite (file-based, no separate server). DB file lives at project root as `caire.db` by default; override with `CAIRE_DB_PATH`.

- **Guidelines** (`/guidelines`): Sample or uploaded guideline documents (e.g. PDFs).

- **Models** (`/models`): Versioned decision tree JSON files. Backend can load trees from here if not in the DB.

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)

### Backend

```bash
cd /path/to/caire
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Create the DB and start the API:

```bash
uvicorn backend.main:app --reload
```

API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs  

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (Vite proxies `/api` to the backend).

### Optional: Docker Compose

From the project root:

```bash
docker compose up --build
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173  

See `docker-compose.yml` for service definitions.

## Quick test

1. Start backend and frontend as above.
2. Seed a tree via API (or drop a JSON into `/models` with the same schema):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/trees/ \
     -H "Content-Type: application/json" \
     -d @models/sample_triage_v1.json
   ```
3. Open the frontend and select the tree from the list.

## Complete example: Emergency department triage

An end-to-end example demonstrates ingestion → compilation → testing for a simplified ED triage guideline (ESI-like levels 1–5).

### 1. What’s included

- **Guideline**: `guidelines/emergency-triage-simplified.md` — chief complaints, vital signs, red flags, triage levels.
- **Prompts**: `backend/prompts/emergency_triage/` — system prompt, few-shot example, urgency instructions.
- **Ingestion script**: `scripts/ingest_example.py` — loads the guideline, runs ingestion + LLM compiler, writes the tree to `models/emergency-triage-v1.json`.
- **Test fixtures**: `tests/fixtures/emergency_triage_cases.json` — 12 cases (ESI 1–5, hypoxia, low BP, chest pain, edge cases, missing data).
- **Demo script**: `scripts/demo.py` — loads the compiled tree, runs all fixture cases, prints a results table and writes `models/emergency-triage-demo-report.txt`.

### 2. How to run the demo

From the project root with the venv activated:

```bash
# Ingest guideline and compile to tree (requires LLM API keys)
python scripts/ingest_example.py

# Run fixture test cases and print report
python scripts/demo.py
```

**Requirements**: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set for ingestion (compiler uses teacher model). Database is created automatically if missing.

### 3. Expected output

**ingest_example.py**

- Step 1: Ingested guideline ID and character count.
- Step 2: Tree name, root node, node count.
- Step 3: Saved path `models/emergency-triage-v1.json`.

**demo.py**

- A table of test case ID, Pass (Yes/No), Actual outcome, Time (ms).
- Summary line: `X/Y passed`.
- Report file: `models/emergency-triage-demo-report.txt` with failed cases and actual path/outcome.

Example:

```
Tree: Emergency Department General Triage (id=emergency-triage-v1)
Running 12 test cases...

Case ID                 Pass   Actual outcome                     Time (ms)
-----------------------------------------------------------------------------
esi1-cardiac-arrest     No     ESI Level 2 – Emergent             2.3
...
Summary: 8/12 passed
Report written to models/emergency-triage-demo-report.txt
```

Pass counts depend on how well the LLM-generated tree matches the expected outcomes in the fixtures; variable names and logic may need alignment (see `docs/lessons-learned.md`).

### 4. Adapting for other triage domains

- **New guideline**: Add a markdown (or PDF) under `guidelines/`, then in `scripts/ingest_example.py` change `GUIDELINE_PATH`, `GUIDELINE_ID`, and the `domain` passed to `process_guideline` and `CompilerOptions`.
- **Domain-specific prompts**: Create `backend/prompts/<domain>/` with `system.txt` and optional `few_shot_example.json`. The compiler loads these when `domain` matches (e.g. `emergency_triage`).
- **New fixtures**: Add or edit JSON in `tests/fixtures/` with `id`, `tree_id`, `input_values`, `expected_path`, `expected_outcome`. Keep `tree_id` and variable names consistent with the compiled tree.
- **Run tests via API**: After ingestion, the tree is also stored in the DB. Use the frontend “Tests” panel or `POST /api/trees/{tree_id}/test` to run tests.

## Production readiness (Phase 1)

- **Configuration**: Copy `.env.example` to `.env` and set `CAIRE_API_KEY`, LLM keys, and log level. See [Environment management](#environment-management) below.
- **Documentation**: [User guide](docs/user-guide.md) (upload, edit, test cases, prompts, troubleshooting). [Developer guide](docs/developer-guide.md) (architecture, extending formats, LLM, validation, testing).
- **API docs**: OpenAPI at `/docs` and `/redoc`; auth and rate limits described there.
- **Monitoring**: `GET /api/health` (DB + LLM config), `GET /api/metrics` (counts, LLM cost, test pass rate), `GET /api/metrics/dashboard` (simple HTML dashboard).
- **Logging**: Structured logs to `logs/caire.log`; compilation and validation steps and optional LLM call logging (see `CAIRE_LOG_LLM_CONTENT` in `.env.example`).
- **Security**: Phase 1 must **not** be used with real PHI. See [docs/phi-hipaa.md](docs/phi-hipaa.md). Optional API key and rate limiting; input validation on all endpoints via Pydantic.

## Environment management

- **Development**: No `CAIRE_API_KEY`; optional `CAIRE_LOG_LEVEL=DEBUG`; run with `--reload`.
- **Production**: Set `CAIRE_API_KEY`, use `CAIRE_LOG_LEVEL=INFO` or `WARNING`, mount `logs/` and database on persistent volumes.
- Copy `.env.example` to `.env` and fill in required variables (see file comments).

## Backup and versioning

- **Database**: `./scripts/backup_db.sh [destination_dir]` copies the SQLite DB to a timestamped file (default `./backups`).
- **Trees as JSON**: `./scripts/export_trees.sh [output_dir]` exports all trees from the DB to JSON files (default `./models/export`) for version control.
- **Large guideline PDFs**: Consider [Git LFS](https://git-lfs.github.com/) for storing large files in the repo instead of committing binaries.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

**CI**: `.github/workflows/test.yml` runs tests on push/PR; `.github/workflows/lint.yml` runs Ruff. See [Developer guide](docs/developer-guide.md#testing-strategy).

## Project layout

```
caire/
├── backend/              # FastAPI app
│   ├── main.py           # App entry, CORS, lifespan
│   ├── database.py       # SQLite + Session
│   ├── models_db.py      # SQLAlchemy models
│   ├── compiler.py       # Guideline → tree (stub)
│   ├── prompts/          # LLM prompts (+ emergency_triage/)
│   ├── services/         # Compiler, ingestion, LLM, test execution
│   └── routes/           # /api/trees, /api/guidelines, /api/test-results
├── frontend/             # React + Vite
│   └── src/
│       ├── api/          # API client
│       ├── components/   # TreeList, TreeEditor, Testing
│       └── types/        # Decision tree TS types
├── shared/
│   └── schemas/          # Pydantic decision tree schema
├── scripts/              # ingest_example.py, demo.py
├── tests/                # Pytest + fixtures/
├── guidelines/           # Sample/uploaded guideline files
├── models/               # Versioned tree JSON + demo report
├── docs/                 # lessons-learned.md
├── pyproject.toml
├── docker-compose.yml
└── README.md
```

## Extending the compiler

The real “compiler” logic lives in `backend/compiler.py`. Right now it returns a minimal placeholder tree. To turn real guidelines into trees you can:

- Use `extract_text_from_pdf()` (PyPDF2) and parse the text (regex, NLP, or LLM) to identify questions, conditions, and outcomes.
- Add more ingestion paths (e.g. Word, structured YAML) and map them to the same `DecisionTree` schema in `shared/schemas/decision_tree.py`.

## License

Solo / educational use; adjust as needed for your context.
