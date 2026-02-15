# CAIRE User Guide

This guide explains how to use CAIRE to upload guidelines, review and edit decision trees, run test cases, and refine prompts.

---

## 1. How to upload a guideline

### Via the API

1. **Start the backend** (see [README](../README.md) Setup).
2. **Upload a file** (PDF or Markdown):

   ```bash
   curl -X POST "http://localhost:8000/api/guidelines/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/guideline.pdf" \
     -F "domain=emergency_triage"
   ```

   Or with an API key (if enabled):

   ```bash
   curl -X POST "http://localhost:8000/api/guidelines/upload" \
     -H "X-API-Key: your-api-key" \
     -F "file=@guideline.pdf" \
     -F "domain=emergency_triage"
   ```

3. The response includes the guideline **id**. Use this id when triggering compilation.

### Via scripts

- Place the file in the `guidelines/` folder, then run:
  ```bash
  python scripts/ingest_example.py
  ```
  (Edit the script to point to your file and domain.)

### Supported formats

- **PDF** — Text is extracted with PyPDF2. Layout and tables may not be preserved.
- **Markdown (`.md`)** — Recommended for best results; use clear headings and bullet lists.

### Best practices

- Keep guidelines under ~12,000 characters when possible; the compiler truncates longer text.
- Use explicit thresholds (e.g. "SpO2 < 92%") so the LLM can create precise condition nodes.
- Define sections (e.g. Chief complaint, Vital signs, Red flags) to improve structure extraction.

---

## 2. How to review and edit generated trees

### In the frontend

1. Open the app (e.g. http://localhost:5173).
2. Select a tree from the list.
3. Switch to **Edit mode** (toolbar).
4. **Drag nodes** to rearrange layout (positions are saved in tree metadata).
5. **Select a node** and click **Edit node** to open the node form:
   - Label, type (condition / action / score)
   - Condition: variable, operator, threshold
   - Action: recommendation text, urgency level
   - Metadata: source section, evidence grade
6. Use **Suggest improvements** to refine a node with the LLM.
7. **Add child** to create a new node under the selected (or root) node.
8. **Delete node** to remove a node (and fix any broken references).
9. Use **Undo** / **Redo** as needed, then **Save** or **Revert**.

### Versioning

- **Save** updates the current tree in the database.
- Check **Save as new version** to bump the version number (e.g. 1.0.0 → 1.0.1) before saving.
- Version is shown in the toolbar; use it to track what is in production vs draft.

### Variables

- Click **Variables** to open the Variable Manager.
- Add, edit, or delete variables (name, type, units, terminology mappings, source).
- Deleting a variable that is used in conditions will warn you; fix or reassign conditions before removing.

### Validation

- Click **Run validation** to run structure and condition checks.
- The Validation panel lists errors and warnings; click an item to highlight the node in the tree.
- Fix validation issues before saving or exporting.

---

## 3. How to create and run test cases

### In the frontend

1. Open a tree and click **Tests** (view or edit mode).
2. **New test case** — Fill in:
   - Input values (one per variable; use the variable names from the tree).
   - Expected path (optional; comma-separated node IDs).
   - Expected outcome (optional; substring of the final recommendation).
3. Click **Run this test** to run the current form without saving.
4. Click **Save test case** to add the case to the list.
5. **Run all tests** to execute every saved case and see pass/fail and coverage.
6. In the results panel you can **Export JSON/CSV** and click node IDs to **highlight** them in the tree.

### Via the API

- **List test cases:** `GET /api/trees/{tree_id}/test-cases`
- **Create:** `POST /api/trees/{tree_id}/test-cases` with body `{ "input_values": {...}, "expected_path": [], "expected_outcome": "..." }`
- **Run all:** `POST /api/trees/{tree_id}/test`
- **Get latest results:** `GET /api/test-results/{tree_id}`
- **Generate cases (LLM):** `POST /api/trees/{tree_id}/test-cases/generate?count=10`

### Fixtures and demo

- Place JSON test cases in `tests/fixtures/` and run `python scripts/demo.py` to run them against a tree in `models/`. See [README – Complete example](../README.md#complete-example-emergency-department-triage).

---

## 4. Best practices for prompt refinement

- **Domain prompts** — For a given domain (e.g. `emergency_triage`), add or edit files in `backend/prompts/<domain>/`:
  - `system.txt` — Instructions and schema for the LLM.
  - `few_shot_example.json` — Example tree in the same JSON shape.
  - `urgency_instructions.txt` — How to map clinical levels to urgency_level.
- **Order of logic** — In the system prompt, state clearly: “Evaluate life-threatening red flags first, then vital signs, then chief complaint.”
- **Variable names** — Use snake_case and list them in the `variables` array; reference only these in conditions.
- **Validation** — After changing prompts, run the compiler and validation, then run test cases to catch regressions.
- See [Lessons learned](lessons-learned.md) for more detail.

---

## 5. Troubleshooting common issues

| Issue | What to do |
|-------|------------|
| **Upload fails** | Check file size and format (PDF/MD). Ensure backend is running and `guidelines/` (or configured path) is writable. |
| **Compilation fails** | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Check logs in `logs/` for LLM errors. Ensure guideline text is not empty after ingestion. |
| **Tree not showing** | Ensure the tree is in the database or in `models/` with the correct id. Use API `GET /api/trees` to list. |
| **Validation errors** | Fix “missing variable” by adding the variable to the tree or to the prompt’s variables list. Fix “invalid threshold” by using the correct type (e.g. boolean for yes/no). |
| **Tests fail** | Align fixture `input_values` keys with the tree’s variables. Use short substrings for `expected_outcome`. Check `models/emergency-triage-demo-report.txt` or the Tests panel for actual path/outcome. |
| **Frontend can’t reach API** | In dev, use Vite proxy (e.g. `/api` → `http://localhost:8000`). In Docker, set `VITE_API_HOST` to the backend URL. |
| **Rate limit / 429** | Reduce request frequency or increase rate limits in configuration. Check `X-RateLimit-*` headers if enabled. |

For more on architecture and extending CAIRE, see the [Developer guide](developer-guide.md).
