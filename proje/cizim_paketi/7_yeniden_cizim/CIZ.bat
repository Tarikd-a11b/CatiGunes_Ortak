@echo off
cd /d "%~dp0"
start "" "%LOCALAPPDATA%\Programs\Labelme\Labelme.exe" goruntuler --labels labels.txt --validate-label exact
