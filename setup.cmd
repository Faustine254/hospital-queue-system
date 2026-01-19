@echo off
:: ========================================
:: Hospital Queue System - Windows Setup
:: ========================================
:: This script will set up the environment and install all dependencies

echo.
echo ========================================
echo   Hospital Queue System Setup
echo ========================================
echo.

:: Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please download and install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo Python found successfully!
echo.

:: Check if we're in the correct directory
echo [2/6] Checking project files...
if not exist "app.py" (
    echo ERROR: app.py not found in current directory
    echo Please make sure you are running this script from the hospital_queue folder
    echo Current directory: %CD%
    pause
    exit /b 1
)

if not exist "templates" (
    echo ERROR: templates folder not found
    echo Please make sure all project files are in the current directory
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found
    echo Please make sure all project files are in the current directory
    pause
    exit /b 1
)

echo All project files found successfully!
echo.

:: Create virtual environment
echo [3/6] Creating virtual environment...
if exist "hospital_env" (
    echo Virtual environment already exists, skipping creation...
) else (
    echo Creating new virtual environment...
    python -m venv hospital_env
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
)
echo.

:: Activate virtual environment
echo [4/6] Activating virtual environment...
call hospital_env\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated!
echo.

:: Upgrade pip
echo [5/6] Upgrading pip...
python -m pip install --upgrade pip
echo.

:: Install dependencies
echo [6/6] Installing dependencies...
echo This may take a few minutes...
echo.

:: Install packages one by one with error handling
echo Installing Flask framework...
pip install Flask==2.3.3 Werkzeug==2.3.7 Jinja2==3.1.2 MarkupSafe==2.1.3 itsdangerous==2.1.2 click==8.1.7

echo Installing audio packages...
pip install gTTS==2.3.2 pygame==2.5.2 requests==2.31.0

echo Installing PDF generation packages...
pip install reportlab==4.0.4 Pillow==10.0.1

echo Installing QR code generation...
pip install "qrcode[pil]==7.4.2"

echo Installing utility packages...
pip install python-dateutil==2.8.2 urllib3==2.0.4 certifi==2023.7.22 charset-normalizer==3.2.0 idna==3.4 six==1.16.0

if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Some packages may have failed to install
    echo Trying to install from requirements.txt as fallback...
    pip install -r requirements.txt
)

echo.
echo ========================================
echo         SETUP COMPLETE!
echo ========================================
echo.
echo The Hospital Queue System has been set up successfully!
echo.
echo Next steps:
echo   1. Run 'run.cmd' to start the application
echo   2. Open your browser to: http://localhost:5000
echo.
echo Available pages:
echo   - Patient tickets: http://localhost:5000/get_ticket
echo   - Display screen:  http://localhost:5000/display
echo   - Staff panel:     http://localhost:5000/staff
echo.

:: Create a shortcut batch file for easier running
echo @echo off > run_hospital.cmd
echo cd /d "%CD%" >> run_hospital.cmd
echo call hospital_env\Scripts\activate.bat >> run_hospital.cmd
echo python app.py >> run_hospital.cmd
echo pause >> run_hospital.cmd

echo A shortcut file 'run_hospital.cmd' has been created!
echo.
echo Press any key to exit...
pause >nul