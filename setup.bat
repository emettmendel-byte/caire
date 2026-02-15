@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set "ROOT=%CD%"

REM Try to enable ANSI (Win 10+)
>nul 2>&1 powershell -Command "& { $h = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Console' -Name 'VirtualTerminalLevel' -ErrorAction SilentlyContinue; if (-not $h) { Set-ItemProperty -Path 'HKCU:\Console' -Name 'VirtualTerminalLevel' -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue } }"

set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BOLD=[1m"
set "RESET=[0m"
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"

echo.
echo %ESC%[1m🚀 CAIRE Setup%ESC%[0m — Getting you ready to run the app (idempotent)
echo.

REM -----------------------------------------------------------------------------
REM 1. Dependencies
REM -----------------------------------------------------------------------------
echo %ESC%[1m1. Checking dependencies...%ESC%[0m
where python >nul 2>&1 || (
  echo %ESC%[91m✗ Python not found. Install Python 3.10+ from https://www.python.org%ESC%[0m
  exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python -c "import sys; print(sys.version_info.minor)" 2^>nul') do set PY_MIN=%%v
if "%PY_MIN%" LSS "10" (
  echo %ESC%[91m✗ Python 3.10+ required (you have 3.%PY_MIN%).%ESC%[0m
  exit /b 1
)
echo %ESC%[92m✓ Python 3.%PY_MIN%%ESC%[0m

where pip >nul 2>&1 || (
  echo %ESC%[91m✗ pip not found. Reinstall Python with pip option.%ESC%[0m
  exit /b 1
)
echo %ESC%[92m✓ pip%ESC%[0m

where node >nul 2>&1 || (
  echo %ESC%[91m✗ Node.js not found. Install Node 18+ from https://nodejs.org%ESC%[0m
  exit /b 1
)
for /f "tokens=*" %%n in ('node -v 2^>nul') do set "NODE_VER=%%n"
echo %ESC%[92m✓ Node !NODE_VER!%ESC%[0m

where npm >nul 2>&1 || (
  echo %ESC%[91m✗ npm not found. Install Node 18+ (includes npm).%ESC%[0m
  exit /b 1
)
echo %ESC%[92m✓ npm%ESC%[0m
echo.

REM -----------------------------------------------------------------------------
REM 2. Python virtual environment
REM -----------------------------------------------------------------------------
echo %ESC%[1m2. Python virtual environment...%ESC%[0m
set "VENV_DIR=%ROOT%\.venv"
if exist "%VENV_DIR%\Scripts\activate.bat" (
  echo %ESC%[92m✓ Virtual env already exists at .venv%ESC%[0m
) else (
  python -m venv "%VENV_DIR%"
  echo %ESC%[92m✓ Created .venv%ESC%[0m
)
call "%VENV_DIR%\Scripts\activate.bat"
echo %ESC%[92m✓ Activated .venv%ESC%[0m
echo.

REM -----------------------------------------------------------------------------
REM 3. Python dependencies
REM -----------------------------------------------------------------------------
echo %ESC%[1m3. Installing Python dependencies...%ESC%[0m
pip install -q -r "%ROOT%\requirements.txt"
echo %ESC%[92m✓ Installed (requirements.txt)%ESC%[0m
echo.

REM -----------------------------------------------------------------------------
REM 4. Node dependencies
REM -----------------------------------------------------------------------------
echo %ESC%[1m4. Installing Node dependencies (frontend)...%ESC%[0m
if exist "%ROOT%\frontend\node_modules" (
  echo %ESC%[92m✓ node_modules already present; skipping npm install%ESC%[0m
) else (
  cd /d "%ROOT%\frontend"
  call npm install
  cd /d "%ROOT%"
  echo %ESC%[92m✓ Installed (npm install)%ESC%[0m
)
echo.

REM -----------------------------------------------------------------------------
REM 5. Directories
REM -----------------------------------------------------------------------------
echo %ESC%[1m5. Creating directories...%ESC%[0m
for %%d in (logs models guidelines) do (
  if not exist "%ROOT%\%%d" mkdir "%ROOT%\%%d"
  echo %ESC%[92m✓ %%d/%ESC%[0m
)
echo.

REM -----------------------------------------------------------------------------
REM 6. .env from .env.example
REM -----------------------------------------------------------------------------
echo %ESC%[1m6. Environment file (.env)...%ESC%[0m
if exist "%ROOT%\.env" (
  echo %ESC%[92m✓ .env already exists; leaving it unchanged%ESC%[0m
) else (
  copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
  echo %ESC%[92m✓ Created .env from .env.example%ESC%[0m
  echo.
  echo %ESC%[93m  Add your API keys to .env (e.g. OPENAI_API_KEY, GOOGLE_API_KEY).%ESC%[0m
  echo %ESC%[93m  Leave CAIRE_API_KEY empty for local dev.%ESC%[0m
  set /p "OPEN_ENV=  Open .env now? [y/N]: "
  if /i "!OPEN_ENV!"=="y" start "" notepad "%ROOT%\.env"
)
echo.

REM -----------------------------------------------------------------------------
REM 7 & 8. Database
REM -----------------------------------------------------------------------------
echo %ESC%[1m7. Initializing SQLite database...%ESC%[0m
set "PYTHONPATH=%ROOT%"
python -c "from backend.database import Base, engine, migrate_guideline_documents_if_needed, migrate_decision_trees_if_needed; Base.metadata.create_all(bind=engine); migrate_guideline_documents_if_needed(); migrate_decision_trees_if_needed()"
if errorlevel 1 (
  echo %ESC%[91m✗ Database init failed.%ESC%[0m
  exit /b 1
)
echo %ESC%[92m✓ Database schema and migrations applied (caire.db)%ESC%[0m
echo.

REM -----------------------------------------------------------------------------
REM 9. Optional: load sample tree
REM -----------------------------------------------------------------------------
echo %ESC%[1m9. Sample decision tree...%ESC%[0m
if exist "%ROOT%\models\sample_triage_v1.json" (
  set /p "SEED=  Load sample tree into the database? [Y/n]: "
  if /i not "!SEED!"=="n" (
    python "%ROOT%\scripts\seed_sample_tree.py"
    if errorlevel 1 (echo %ESC%[93m⚠ Seed failed (non-fatal)%ESC%[0m) else (echo %ESC%[92m✓ Sample tree loaded%ESC%[0m)
  ) else (
    echo %ESC%[93m⚠ Skipped. You can load it later from the app (Trees - Load sample tree).%ESC%[0m
  )
) else (
  echo %ESC%[93m⚠ models\sample_triage_v1.json not found; skipping.%ESC%[0m
)
echo.

REM -----------------------------------------------------------------------------
REM 10. Start backend and frontend
REM -----------------------------------------------------------------------------
echo %ESC%[1m10. Starting backend and frontend (development)...%ESC%[0m
set "PORT_BACKEND=8000"
if defined PORT set "PORT_BACKEND=%PORT%"

start "CAIRE Backend" cmd /k "cd /d "%ROOT%" && set PYTHONPATH=%ROOT% && .venv\Scripts\activate && uvicorn backend.main:app --reload --host 127.0.0.1 --port %PORT_BACKEND%"
timeout /t 2 /nobreak >nul
start "CAIRE Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm run dev -- --port 3000"

echo.
echo %ESC%[92m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%ESC%[0m
echo %ESC%[92m  🎉 Setup complete! Servers are starting in new windows.%ESC%[0m
echo %ESC%[92m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%ESC%[0m
echo.
echo   📱 Frontend:    http://localhost:3000
echo   🔧 Backend API: http://localhost:8000
echo   📚 API docs:    http://localhost:8000/docs
echo.
echo   Close the two server windows to stop. Run setup.bat again anytime (idempotent).
echo.
pause
