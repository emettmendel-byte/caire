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

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Project layout

```
caire/
├── backend/           # FastAPI app
│   ├── main.py        # App entry, CORS, lifespan
│   ├── database.py    # SQLite + Session
│   ├── models_db.py   # SQLAlchemy models
│   ├── compiler.py    # Guideline → tree (stub)
│   └── routes/        # /api/trees, /api/guidelines
├── frontend/          # React + Vite
│   └── src/
│       ├── api/       # API client
│       ├── components/# TreeList, TreeView
│       └── types/     # Decision tree TS types
├── shared/
│   └── schemas/       # Pydantic decision tree schema
├── tests/             # Pytest (unit + API)
├── guidelines/        # Sample/uploaded guideline files
├── models/            # Versioned tree JSON files
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
