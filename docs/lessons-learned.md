# Lessons learned: Emergency triage example

Insights from the first end-to-end implementation of the CAIRE ED triage demo (guideline → ingestion → compilation → test fixtures → demo script).

## 1. Guideline structure

- **Structured sections** (chief complaint, vitals, red flags, levels) give the LLM a clear map and improve consistency of the generated tree.
- **Explicit thresholds** in the guideline (e.g. SpO2 &lt;92%, SBP &lt;90) are more likely to appear as condition nodes; vague wording leads to generic or missing branches.
- **Short, scoped documents** work better than long guidelines; truncation at 12k chars can drop important logic. Keeping the example “simplified” improved output quality.

## 2. Prompt engineering

- **Domain-specific system prompts** (`backend/prompts/emergency_triage/system.txt`) that stress triage order (life-threatening first, then vitals, then complaint) reduce logic order errors.
- **Few-shot examples** in the same schema (nodes dict, condition/action, variables) help the model produce valid JSON and sensible variable names.
- **Urgency mapping** (Level 1→emergency, Level 2→urgent, etc.) in a separate instructions file keeps the main prompt shorter and makes it easy to tune without touching code.

## 3. LLM-generated tree

- **Variable naming**: The model may use different names than the fixture (e.g. `chief_complaint` vs `chief_complaint_category`). Either align fixtures to the compiled tree after first run or document expected variables in the guideline/prompt.
- **Node coverage**: Not every ESI level may get a dedicated leaf; the tree might merge levels (e.g. 4 and 5) or add branches we did not specify. Manual review of `models/emergency-triage-v1.json` is recommended after each compile.
- **Validation**: The compiler runs structure and condition validation; fixing “missing variable” or “invalid threshold type” in the prompt or guideline reduces failed compiles.

## 4. Test fixtures and demo

- **expected_path**: Leaving it empty and only asserting `expected_outcome` (substring) is more robust when the tree structure varies between runs.
- **expected_outcome**: Use a short substring (e.g. “urgent”, “routine”) rather than full recommendation text, since wording can differ.
- **Edge cases**: “Missing data” and “conflicting indicators” cases help verify that the tree doesn’t assume all inputs are present and that escalation rules behave as intended.
- **Fixture variable alignment**: After the first successful ingest, inspect `tree.variables` and node conditions, then update `tests/fixtures/emergency_triage_cases.json` so `input_values` keys match. Re-run `scripts/demo.py` to confirm pass rate.

## 5. Errors and improvements

- **Typical issues**:
  - Condition variable not in `variables` list → compiler adds inferred variables; if types differ (e.g. boolean vs categorical), condition validation may flag it.
  - Root or first branch not “life-threatening” → refine system prompt to state “evaluate life-threatening red flags first.”
  - Outcome text doesn’t contain expected substring → relax expected_outcome in fixtures or add more specific recommendation wording in the prompt.
- **Improvements to try**:
  - Add a post-compile step that renames variables to a canonical set (e.g. from guideline) so fixtures stay stable.
  - Store “golden” tree JSON for a known-good compile and diff against new compiles to spot regressions.
  - Use the frontend Testing panel to add/run test cases interactively and then export them into `tests/fixtures/`.

## 6. Manual review checklist

When reviewing the LLM-generated tree:

- [ ] Root node reflects “first decision” (e.g. life-threatening vs not).
- [ ] All referenced variables appear in `variables` with correct type.
- [ ] Urgency levels on action nodes match intent (emergency/urgent/routine).
- [ ] No unreachable nodes (every node is reachable from root via children).
- [ ] Edge cases (missing vitals, conflicting indicators) route to a sensible outcome.
- [ ] Run `scripts/demo.py` and inspect failed cases in `models/emergency-triage-demo-report.txt`; fix tree or fixtures as needed.

This document can be updated as the example is iterated and reused for other triage domains.
