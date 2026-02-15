#!/usr/bin/env bash
# CAIRE bootstrap script (idempotent). Run from project root: ./setup.sh

set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
warn() { echo -e "${YELLOW}⚠${RESET} $*"; }

echo ""
echo -e "${BOLD}🚀 CAIRE Setup${RESET} — Getting you ready to run the app (idempotent)"
echo ""

# -----------------------------------------------------------------------------
# 1. Dependencies
# -----------------------------------------------------------------------------
echo -e "${BOLD}1. Checking dependencies...${RESET}"
command -v python3 >/dev/null 2>&1 || fail "Python 3 not found. Install Python 3.10+ (https://www.python.org)."
PY_VER=$(python3 -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")')
PY_MAJ=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MIN=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [[ "$PY_MAJ" -lt 3 ]] || [[ "$PY_MIN" -lt 10 ]]; then
  fail "Python 3.10+ required; you have $PY_VER."
fi
ok "Python $PY_VER"

command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1 || fail "pip not found. Install pip for Python 3."
ok "pip"

command -v node >/dev/null 2>&1 || fail "Node.js not found. Install Node 18+ (https://nodejs.org)."
NODE_VER=$(node -v | sed 's/^v//')
NODE_MAJ=$(node -e "console.log(parseInt(process.version.slice(1).split('.')[0], 10))")
[[ "$NODE_MAJ" -ge 18 ]] || fail "Node 18+ required; you have $NODE_VER."
ok "Node $NODE_VER"

command -v npm >/dev/null 2>&1 || fail "npm not found. Install Node 18+ (includes npm)."
ok "npm"
echo ""

# -----------------------------------------------------------------------------
# 2. Python virtual environment
# -----------------------------------------------------------------------------
echo -e "${BOLD}2. Python virtual environment...${RESET}"
VENV_DIR="$ROOT/.venv"
if [[ -d "$VENV_DIR" ]]; then
  ok "Virtual env already exists at .venv"
else
  python3 -m venv "$VENV_DIR"
  ok "Created .venv"
fi
# Activate for this script (idempotent: safe to source again)
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
ok "Activated .venv"
echo ""

# -----------------------------------------------------------------------------
# 3. Python dependencies
# -----------------------------------------------------------------------------
echo -e "${BOLD}3. Installing Python dependencies...${RESET}"
pip install -q -r "$ROOT/requirements.txt"
ok "Installed (requirements.txt)"
echo ""

# -----------------------------------------------------------------------------
# 4. Node dependencies
# -----------------------------------------------------------------------------
echo -e "${BOLD}4. Installing Node dependencies (frontend)...${RESET}"
if [[ -d "$ROOT/frontend/node_modules" ]]; then
  ok "node_modules already present; skipping npm install (run manually to update)"
else
  (cd "$ROOT/frontend" && npm install)
  ok "Installed (npm install)"
fi
echo ""

# -----------------------------------------------------------------------------
# 5. Directories
# -----------------------------------------------------------------------------
echo -e "${BOLD}5. Creating directories...${RESET}"
for dir in logs models guidelines; do
  mkdir -p "$ROOT/$dir"
  ok "$dir/"
done
echo ""

# -----------------------------------------------------------------------------
# 6. .env from .env.example
# -----------------------------------------------------------------------------
echo -e "${BOLD}6. Environment file (.env)...${RESET}"
if [[ -f "$ROOT/.env" ]]; then
  ok ".env already exists; leaving it unchanged"
else
  cp "$ROOT/.env.example" "$ROOT/.env"
  ok "Created .env from .env.example"
  echo ""
  echo -e "${YELLOW}  Add your API keys to .env for compilation (e.g. OPENAI_API_KEY, GOOGLE_API_KEY).${RESET}"
  echo -e "${YELLOW}  Leave CAIRE_API_KEY empty for local dev (no auth).${RESET}"
  if [[ -t 0 ]]; then
    read -r -p "  Open .env now to edit? [y/N] " ans
    case "$ans" in
      y|Y) "${EDITOR:-nano}" "$ROOT/.env" 2>/dev/null || true ;;
    esac
  fi
fi
echo ""

# -----------------------------------------------------------------------------
# 7 & 8. Database: schema + migrations
# -----------------------------------------------------------------------------
echo -e "${BOLD}7. Initializing SQLite database...${RESET}"
export PYTHONPATH="$ROOT"
python3 -c "
from backend.database import Base, engine, migrate_guideline_documents_if_needed, migrate_decision_trees_if_needed
Base.metadata.create_all(bind=engine)
migrate_guideline_documents_if_needed()
migrate_decision_trees_if_needed()
"
ok "Database schema and migrations applied (caire.db)"
echo ""

# -----------------------------------------------------------------------------
# 9. Optional: load sample tree
# -----------------------------------------------------------------------------
echo -e "${BOLD}9. Sample decision tree...${RESET}"
if [[ -f "$ROOT/models/sample_triage_v1.json" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "  Load sample tree into the database? [Y/n] " ans
    case "$ans" in
      n|N) warn "Skipped. You can load it later from the app (Trees → Load sample tree)." ;;
      *)  python3 "$ROOT/scripts/seed_sample_tree.py" && ok "Sample tree loaded" || warn "Seed failed (non-fatal)" ;;
    esac
  else
    python3 "$ROOT/scripts/seed_sample_tree.py" && ok "Sample tree loaded" || warn "Seed failed (non-fatal)"
  fi
else
  warn "models/sample_triage_v1.json not found; skipping sample tree."
fi
echo ""

# -----------------------------------------------------------------------------
# 10. Start backend and frontend
# -----------------------------------------------------------------------------
echo -e "${BOLD}10. Starting backend and frontend (development)...${RESET}"
PORT_BACKEND="${PORT:-8000}"
# Start backend in background (from project root, with venv active)
uvicorn backend.main:app --reload --host 127.0.0.1 --port "$PORT_BACKEND" &
UVICORN_PID=$!
# Give backend a moment to bind
sleep 2
# Start frontend in background (port 3000 as requested)
(cd "$ROOT/frontend" && npm run dev -- --port 3000) &
VITE_PID=$!
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  🎉 Setup complete! Servers are starting.${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  📱 Frontend:    http://localhost:3000"
echo "  🔧 Backend API: http://localhost:8000"
echo "  📚 API docs:    http://localhost:8000/docs"
echo ""
echo "  Stop servers: kill $UVICORN_PID $VITE_PID  (or close this terminal)"
echo "  Run again:    ./setup.sh  (idempotent — will not re-prompt if .env exists)"
echo ""

# Wait on both; trap so we kill children on Ctrl+C
trap 'kill $UVICORN_PID $VITE_PID 2>/dev/null; exit 0' INT TERM
wait
