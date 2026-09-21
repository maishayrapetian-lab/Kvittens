@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set "PY=python"
where python >nul 2>nul || set "PY=py"
if exist "env\Scripts\python.exe" set "PY=env\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo Laser av testbilderna. Det tar ett par minuter...
echo.
"%PY%" utvardera.py
echo.
echo Resultatet finns ocksa i filen utvardering_resultat.txt
pause
