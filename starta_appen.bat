@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set "PY=python"
where python >nul 2>nul || set "PY=py"
if exist "env\Scripts\python.exe" set "PY=env\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import streamlit" 2>nul
if errorlevel 1 goto saknas
echo Startar Kvittens. Webblasaren oppnas strax.
echo Stang det har fonstret nar du vill avsluta appen.
echo.
"%PY%" -m streamlit run app.py --server.address localhost
pause
exit /b 0
:saknas
echo Paketen ar inte installerade an. Dubbelklicka pa installera.bat och prova sedan igen.
pause
exit /b 1
