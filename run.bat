@echo off
echo ========================================
echo MTG Proxy Card Cutter
echo ========================================
echo.

:: Check if setup has been run
if not exist "backend\venv" (
    echo ERROR: Setup not complete. Please run setup.bat first.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo ERROR: Setup not complete. Please run setup.bat first.
    pause
    exit /b 1
)

echo Starting backend server...
start "MTG Proxy Cutter - Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && python main.py"

:: Wait for backend to start
timeout /t 3 /nobreak > nul

echo Starting frontend server...
start "MTG Proxy Cutter - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Both servers are starting!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Close the command windows to stop the servers.
echo.

:: Wait a moment then open browser
timeout /t 3 /nobreak > nul
start http://localhost:5173

pause
