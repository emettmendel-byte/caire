# CAIRE Developer Guide

This guide covers architecture, extending guideline formats, the LLM router, validation rules, and testing.

---

## 1. Architecture overview

### High-level flow

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Guideline       │     │  Ingestion       │     │  Compiler        │
│  (PDF / MD)      │ ──► │  Service         │ ──► │  Service (LLM)   │
└──────────────────┘     │  segment, store  │     │  parse → tree    │
                         └──────────────────┘     └────────┬─────────┘
                                    │                       │
                                    ▼                       ▼
                         ┌──────────────────┐     ┌──────────────────┐
                         │  SQLite          │     │  Validation      │
                         │  guideline_docs  │     │  structure +     │
                         └──────────────────┘     │  conditions      │
                                    │              └────────┬─────────┘
                                    │                       │
                                    ▼                       ▼
                         ┌──────────────────────────────────────────┐
                         │  decision_trees (tree_json), test_cases,  │
                         │  test_results                             │
                         └──────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────┐     ┌──────────────────┐
                         │  REST API        │ ◄── │  Frontend        │
                         │  /api/trees,     │     │  TreeEditor,     │
                         │  /guidelines,    │     │  Testing         │
                         │  /test-results   │     └──────────────────┘
                         └──────────────────┘
```

### Main components

| Component | Path | Role |
|-----------|------|------|
| **Backend API** | `backend/main.py`, `backend/routes/` | FastAPI app; trees, guidelines, compile, test endpoints. |
| **Ingestion** | `backend/services/ingestion_service.py` | PDF/MD → raw text, segment, store in `guideline_documents`. |
| **Compiler** | `backend/services/compiler_service.py` | Guideline → DMN tree via LLM; validation; persist to `decision_trees`. |
| **LLM** | `backend/services/llm_service.py` | Teacher/student router; `parse_guideline_to_tree`, `refine_node`, `extract_decision_variables`. |
| **Test execution** | `backend/services/test_service.py` | Run test cases against a tree; trace path; compare outcome. |
| **Models** | `backend/models/decision_tree.py`, `backend/models_db.py` | DMN tree, nodes, variables, TestCase; SQLite ORM. |
| **Frontend** | `frontend/src/` | React app: TreeEditor, Testing, NodeEditModal, VariableManager. |

### Data flow

- **Guidelines**: Uploaded file → `process_guideline()` → text extraction + segmentation → `GuidelineDocumentModel`.
- **Trees**: `compile_guideline_to_tree(guideline_id)` loads guideline text → LLM → `DecisionTree` (nodes dict, variables) → validation → `DecisionTreeModel.tree_json`.
- **Tests**: `TestCase` (input_values, expected_path, expected_outcome) → `run_test_case(tree, tc)` → `TestResult`; results stored in `TestResultModel`.

---

## 2. How to add support for new guideline formats

1. **Add a reader in ingestion**
   - In `backend/services/ingestion_service.py`, add a function (e.g. `ingest_docx(file_path: str) -> str`) that returns raw text.
   - In `process_guideline()`, extend the `suffix` handling to call your reader and set `raw_text`.
2. **Optional: custom segmentation**
   - If the format has structure (e.g. Word headings), implement a segmenter that returns `list[GuidelineSection]` and call it from `process_guideline()` instead of or in addition to `segment_guideline(raw_text)`.
3. **Dependencies**
   - Add the library (e.g. `python-docx`) to `pyproject.toml` under `dependencies` or `[project.optional-dependencies]`, and document in README.

---

## 3. How to extend the LLM router

- **Router** — `backend/services/llm_service.py` defines `LLMRouter` with `call_teacher_model` and `call_student_model`. Provider (OpenAI/Anthropic) is selected via env (e.g. `CAIRE_LLM_PROVIDER`, `CAIRE_LLM_TEACHER_MODEL`).
- **Add a provider**
  - Implement the `LLMProvider` protocol (`async def call(prompt, system_prompt, model) -> tuple[str, LLMUsage]`).
  - Register it in `LLMRouter._get_teacher()` / `_get_student()` based on env.
- **Use a different model for a task**
  - For example, in `parse_guideline_to_tree` the router is used as-is; you can pass a custom `router` or add a parameter to force a model name for that call.
- **Prompt loading**
  - `_load_prompt(name)` loads from `backend/prompts/`.
  - `_load_domain_prompt(domain, name)` loads from `backend/prompts/<domain>/` (e.g. `emergency_triage/system.txt`). Use this for domain-specific system prompts and few-shot examples.

---

## 4. How to add new validation rules

- **Structure** — In `backend/services/compiler_service.py`, `validate_tree_structure(tree)` returns `list[ValidationError]`. Add checks (e.g. “root must have at least one child”, “max children per node”) and append to `errors`.
- **Conditions** — `validate_conditions(tree)` checks that condition variables exist in `tree.variables` and that threshold types match. Add rules (e.g. “numeric variable must use numeric threshold”) in the same way.
- **Custom validators**
  - Add a new function `validate_<name>(tree) -> list[ValidationError]` and call it from `compile_guideline_to_tree` after the existing validators; optionally gate on `CompilerOptions` (e.g. `strictness_level`).
- **API**
  - `POST /api/trees/validate` already runs structure + condition validation on a submitted tree JSON; extend the route to call your validator and include results in the response.

---

## 5. Testing strategy

- **Unit tests** — `tests/` with pytest. Test services in isolation (e.g. `run_test_case` with a minimal tree, validation functions with fixed inputs).
- **API tests** — Use `httpx.ASGITransport` and `app` to hit endpoints; seed DB or use fixtures.
- **Fixtures** — `tests/fixtures/` holds JSON (e.g. `emergency_triage_cases.json`). Use for demo and for regression tests.
- **Demo script** — `scripts/demo.py` runs fixtures against a tree in `models/` and writes a report; useful for manual and CI runs.
- **Frontend** — Run `npm run build` and, if available, component/integration tests.

See `.github/workflows/test.yml` for the CI test command.

---

## 6. Diagram (ASCII)

```
[User] ──► [Frontend] ──► [FastAPI] ──► [Ingestion / Compiler / Test Service]
                │                │
                │                ├── [SQLite]
                │                ├── [LLM API]
                │                └── [logs/]
                └──► [Vite dev server]
```

For deployment and monitoring, see [README](../README.md) and the monitoring/deployment sections in the repo.
