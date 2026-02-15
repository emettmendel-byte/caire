#!/usr/bin/env bash
# Export all decision trees from SQLite to JSON files for version control.
# Usage: ./scripts/export_trees.sh [output_dir]
# Default output: ./models/export
# Requires Python and CAIRE on PYTHONPATH. Uses backend.database and models_db.

set -e
OUT_DIR="${1:-./models/export}"
mkdir -p "$OUT_DIR"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export OUT_DIR="$OUT_DIR"
python - <<'PY'
import json
import os
from pathlib import Path
from backend.database import SessionLocal
from backend.models_db import DecisionTreeModel

out_dir = os.environ.get("OUT_DIR", "models/export")
db = SessionLocal()
try:
    rows = db.query(DecisionTreeModel).all()
    for r in rows:
        if not r.tree_json:
            continue
        path = Path(out_dir) / f"{r.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(r.tree_json, indent=2), encoding="utf-8")
        print(path)
finally:
    db.close()
PY
echo "Exported to $OUT_DIR"
