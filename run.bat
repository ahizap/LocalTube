@echo off
:: Get the directory where this script lives
set "ROOT=%~dp0"

echo Starting Backend Server...
start "Backend" cmd /k "cd /d %ROOT%backend && call venv\Scripts\activate.bat && uvicorn main:app --port 8080 --reload"

echo Starting Frontend Dev Server...
start "Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo Both servers are starting in separate windows.
