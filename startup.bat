@echo off
REM Startup script for Banking Data Pipeline - Windows

setlocal enabledelayedexpansion

echo ==================================
echo 🏦 Banking Data Pipeline Startup
echo ==================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    exit /b 1
)

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    exit /b 1
)

REM Setup Python virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

echo 📥 Installing dependencies...
pip install -q -r requirements.txt

echo.
echo 🚀 Starting Docker containers...
docker-compose up -d

echo.
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak

echo.
echo ✅ Starting infrastructure setup...
python orchestrator.py --startup

echo.
echo ==================================
echo ✅ Pipeline startup complete!
echo ==================================
echo.
echo Next steps:
echo 1. Run data generator ^(in another terminal^):
echo    python data-generator\faker_generator.py
echo.
echo 2. Run Kafka consumer ^(in another terminal^):
echo    python consumer\kafka_consumer.py
echo.
echo 3. Monitor pipeline ^(in another terminal^):
echo    python monitoring.py
echo.
echo ==================================
pause
