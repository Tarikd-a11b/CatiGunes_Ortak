@echo off
cd /d "%~dp0"
start "" "%LOCALAPPDATA%\Programs\Labelme\Labelme.exe" goruntuler --output cizimler_2 --labels labels.txt --validate-label exact
