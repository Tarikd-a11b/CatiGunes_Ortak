@echo off
rem Cati GES haritasini baslatir. Once Docker Desktop acik olmali.
cd /d "%~dp0"
docker start catigunes_db >nul
echo Harita: http://localhost:8000
.venv\Scripts\python -m uvicorn api.main:app --port 8000
