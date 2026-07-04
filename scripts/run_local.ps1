# CareerForge AI - Local Environment Startup Script for Windows PowerShell
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "        Bootstrapping CareerForge AI         " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Virtual Environment Setup
if (-not (Test-Path "venv")) {
    Write-Host "[1/5] Creating Python virtual environment (venv)..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error creating virtual environment. Ensure Python is in your PATH." -ForegroundColor Red
        Exit
    }
} else {
    Write-Host "[1/5] Virtual environment already exists. Skipping creation." -ForegroundColor Green
}

# 2. Activate Virtual Env & Install Requirements
Write-Host "[2/5] Activating virtual environment and installing packages..." -ForegroundColor Yellow
. .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error installing Python packages." -ForegroundColor Red
    Exit
}

# 3. Bootstrap SQLite Database
Write-Host "[3/5] Bootstrapping SQLite database with seed catalogs..." -ForegroundColor Yellow
python scripts/bootstrap_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error bootstrapping database." -ForegroundColor Red
    Exit
}

# 4. Run System Integration Checks
Write-Host "[4/5] Running end-to-end integration tests..." -ForegroundColor Yellow
python scripts/test_integration.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Integration tests failed. Review outputs before launching." -ForegroundColor Red
    Exit
}

# 5. Launch FastAPI Web Application
Write-Host "[5/5] Launching FastAPI platform dashboard on http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate application." -ForegroundColor Yellow
python -m uvicorn backend.app.main:app --port 8000
