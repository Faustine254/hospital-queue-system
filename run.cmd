@echo off
:: ========================================
:: Hospital Queue System - Windows Runner
:: ========================================
:: This script will start the Hospital Queue System

echo.
echo ========================================
echo   Hospital Queue System Launcher
echo ========================================
echo.

:: Check if setup has been run
if not exist "hospital_env" (
    echo ERROR: Virtual environment not found!
    echo Please run 'setup.cmd' first to install dependencies.
    echo.
    pause
    exit /b 1
)

if not exist "app.py" (
    echo ERROR: app.py not found in current directory!
    echo Please make sure you are running this script from the hospital_queue folder
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
echo [1/3] Activating virtual environment...
call hospital_env\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment
    echo Please run 'setup.cmd' to fix the installation
    echo.
    pause
    exit /b 1
)
echo Virtual environment activated!
echo.

:: Check if Python packages are installed
echo [2/3] Checking dependencies...
python -c "import flask" 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Flask not found! Dependencies may not be installed correctly.
    echo Please run 'setup.cmd' to install dependencies.
    echo.
    pause
    exit /b 1
)

python -c "import sqlite3, gtts, pygame, reportlab, qrcode" 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: Some dependencies might be missing.
    echo The application may still work, but some features might not function properly.
    echo If you encounter errors, please run 'setup.cmd' again.
    echo.
)

echo Dependencies check completed!
echo.

:: Start the application
echo [3/3] Starting Hospital Queue System...
echo.
echo ========================================
echo     APPLICATION STARTING...
echo ========================================
echo.
echo The Hospital Queue System is starting up!
echo.
echo Once started, you can access:
echo   • Patient Portal:  http://localhost:5000/get_ticket
echo   • Display Screen:  http://localhost:5000/display  
echo   • Staff Panel:     http://localhost:5000/staff
echo.
echo Press Ctrl+C to stop the server when done.
echo.
echo ========================================

:: Change to the script directory to ensure relative paths work
cd /d "%~dp0"

:: Run the Flask application
python app.py

:: If the application exits, show this message
echo.
echo ========================================
echo   Application has stopped running
echo ========================================
echo.
echo If you encountered any errors:
echo   1. Check that all files are in the correct location
echo   2. Run 'setup.cmd' again if dependencies are missing  
echo   3. Make sure no other application is using port 5000
echo.
echo To restart the application, run this script again.
echo.
echo Press any key to exit...
pause >nul