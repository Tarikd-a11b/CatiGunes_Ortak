@echo off
rem CatiGunes web uygulamasini kurar. Once Docker Desktop ve Python kurulu olmali.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1" %*
echo.
pause
