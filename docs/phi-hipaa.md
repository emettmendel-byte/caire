# PHI and HIPAA — Phase 1 Notice

## Phase 1: Do not use with real PHI

**CAIRE Phase 1 is not intended for production use with real Protected Health Information (PHI).**

- Do **not** upload guidelines or tree content that contain real patient data, real identifiers, or real clinical narratives that could be linked to individuals.
- Do **not** rely on Phase 1 for HIPAA compliance. There is no Business Associate Agreement (BAA), no encryption at rest of the database, and no formal access or audit controls beyond optional API key and rate limiting.
- Use only synthetic or fully de-identified data for testing and demos.

## Implemented in Phase 1

- Optional API key authentication and rate limiting to reduce abuse.
- Input validation via Pydantic and FastAPI on all API payloads.
- Structured logging; optional logging of LLM content (disabled by default in production).
- SQLite database stored in a configurable path; ensure filesystem permissions restrict access.

## Planned for future phases (HIPAA / production)

- **Encryption at rest** for the database and any stored guideline/tree content. (TODO in codebase.)
- **BAA** with LLM providers if PHI is sent to them; or use self-hosted / on-prem models.
- **Access controls** and audit logging: who accessed which tree, when.
- **Minimum necessary**: limit data in prompts and logs to what is strictly needed.
- **Secure disposal** of data and logs when no longer needed.

## Where to look in the codebase

- `backend/main.py`: PHI warning comment and TODO for encryption.
- `.env.example`: Notes on not logging LLM content in production.
- This document: `docs/phi-hipaa.md`.

If you deploy CAIRE in an environment where PHI might be introduced, consult your compliance and security teams and plan for the measures above before going live.
