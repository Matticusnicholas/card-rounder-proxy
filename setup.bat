@echo off
echo ========================================
echo MTG Proxy Card Cutter - Setup
echo ========================================
echo.

echo [1/4] Creating Python virtual environment...
cd backend
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment. Make sure Python is installed.
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

cd ..

echo [4/4] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install Node dependencies. Make sure Node.js is installed.
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Run 'run.bat' to start the application.
echo.
pause
