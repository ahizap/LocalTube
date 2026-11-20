@echo off
setlocal
set "ROOT=%~dp0"

echo ======================================================
echo                  Starting LocalTube
echo ======================================================

:: Check if virtual environment exists; if not, trigger installation automatically
if not exist "%ROOT%backend\venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running installer first...
    call "%ROOT%install.bat"
    if not exist "%ROOT%backend\venv\Scripts\activate.bat" (
        echo [ERROR] Setup failed. Please check the errors above.
        pause
        exit /b 1
    )
)

:: Check if frontend is built
if exist "%ROOT%frontend\dist\index.html" (
    echo [OK] Pre-built frontend detected. Starting unified server...
    start http://localhost:8080
    cd /d "%ROOT%backend"
    call venv\Scripts\activate.bat
    python ..\run_app.py
) else (
    echo [INFO] Pre-built frontend not found. Starting development mode...
    echo Starting Backend Server on port 8080...
    start "LocalTube Backend" cmd /k "cd /d %ROOT%backend && call venv\Scripts\activate.bat && uvicorn main:app --port 8080 --reload"

    echo Starting Frontend Dev Server...
    start "LocalTube Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"
    
    timeout /t 3 >nul
    start http://localhost:5173
    echo Both servers are running.
)
