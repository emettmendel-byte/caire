#!/usr/bin/env python3
"""
Ingest the sample ED triage guideline and compile it to a decision tree.

Usage (from project root):
  python scripts/ingest_example.py

Requires: CAIRE backend dependencies, database initialized.
"""
import asyncio
import json
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUIDELINE_PATH = ROOT / "guidelines" / "emergency-triage-simplified.md"
MODEL_PATH = ROOT / "models" / "emergency-triage-v1.json"
GUIDELINE_ID = "emergency-triage"


def main() -> None:
    if not GUIDELINE_PATH.exists():
        print(f"Error: Guideline not found at {GUIDELINE_PATH}")
        sys.exit(1)

    from backend.database import Base, engine
    from backend.models_db import GuidelineDocumentModel, DecisionTreeModel
    Base.metadata.create_all(bind=engine)

    from backend.services.ingestion_service import process_guideline
    from backend.services.compiler_service import compile_guideline_to_tree, CompilerOptions

    print("Step 1: Ingesting guideline...")
    doc = process_guideline(str(GUIDELINE_PATH), domain="emergency_triage", guideline_id=GUIDELINE_ID)
    print(f"  Ingested: {doc.id}, {len(doc.raw_text)} chars")

    print("Step 2: Compiling to decision tree (LLM)...")
    options = CompilerOptions(target_domain="emergency_triage", max_tree_depth=20)
    tree = asyncio.run(compile_guideline_to_tree(GUIDELINE_ID, options))
    print(f"  Tree: {tree.name}, root={tree.root_node_id}, nodes={len(tree.nodes)}")

    # Normalize id for the saved file
    tree_id = "emergency-triage-v1"
    payload = tree.model_dump(mode="json")
    payload["id"] = tree_id

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Step 3: Saved to {MODEL_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
