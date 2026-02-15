#!/usr/bin/env python3
"""
Load the sample decision tree from models/sample_triage_v1.json into the database.
Idempotent: safe to run multiple times (upserts).

Usage (from project root):
  python scripts/seed_sample_tree.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_PATH = ROOT / "models" / "sample_triage_v1.json"


def main() -> int:
    if not SAMPLE_PATH.exists():
        print(f"Sample file not found: {SAMPLE_PATH}", file=sys.stderr)
        return 1
    from backend.database import SessionLocal
    from backend.models_db import DecisionTreeModel

    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    tree_id = data.get("id", "sample-triage")
    db = SessionLocal()
    try:
        row = db.query(DecisionTreeModel).filter(DecisionTreeModel.id == tree_id).first()
        if row:
            row.tree_json = data
            row.version = data.get("version", row.version)
            row.name = data.get("name", row.name)
            row.description = data.get("description")
            db.commit()
            db.refresh(row)
        else:
            row = DecisionTreeModel(
                id=tree_id,
                version=data.get("version", "1.0.0"),
                name=data.get("name", "Sample General Triage"),
                description=data.get("description"),
                status="draft",
                tree_json=data,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        print(f"Seeded tree: {row.name} (id={row.id}, version={row.version})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
