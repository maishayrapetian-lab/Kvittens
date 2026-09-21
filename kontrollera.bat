@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set "PY=python"
where python >nul 2>nul || set "PY=py"
if exist "env\Scripts\python.exe" set "PY=env\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" kontrollera.py
set "KOD=%ERRORLEVEL%"
echo.
if "%KOD%"=="3" echo Paket saknas: dubbelklicka pa installera.bat och kor sedan den har filen igen.
if "%KOD%"=="2" start "" notepad ".streamlit\secrets.toml"
if "%KOD%"=="9009" echo Python hittades inte: dubbelklicka pa installera.bat
pause
