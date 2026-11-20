@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo             LocalTube Windows Installer
echo ======================================================
echo.

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check the box "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python detected.

:: 2. Check Node.js & npm (for building the frontend)
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Node.js / npm not found!
    echo If frontend/dist is already built, LocalTube will still work.
    echo Otherwise, please install Node.js from https://nodejs.org/
) else (
    echo [OK] Node.js and npm detected.
)

:: 3. Check FFmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "%~dp0bin\ffmpeg.exe" (
        echo [OK] Bundled FFmpeg found in bin\ folder.
    ) else (
        echo [WARNING] FFmpeg was not detected in system PATH or bin\ folder.
        echo Video thumbnails and previews require FFmpeg.
        echo You can download it from https://www.gyan.dev/ffmpeg/builds/ and place ffmpeg.exe in a "bin" folder here.
    )
) else (
    echo [OK] FFmpeg detected.
)

echo.
echo --- Setting up Python Virtual Environment ---
cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment in backend\venv...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment and installing backend requirements...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install backend requirements.
    pause
    exit /b 1
)
call deactivate
echo [OK] Backend ready.

:: 4. Build Frontend if npm exists
if exist "%~dp0frontend" (
    where npm >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo.
        echo --- Setting up and Building Frontend ---
        cd /d "%~dp0frontend"
        if not exist "node_modules" (
            echo Installing Node.js dependencies...
            call npm install
        )
        echo Building static frontend distribution...
        call npm run build
        echo [OK] Frontend built successfully.
    )
)

cd /d "%~dp0"
echo.
echo ======================================================
echo   Installation completed successfully!
echo   You can now launch LocalTube by running run.bat
echo ======================================================
pause
