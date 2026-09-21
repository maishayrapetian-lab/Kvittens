@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
echo === Installerar Kvittens ===
echo.
set "BASPY="
where py >nul 2>nul && set "BASPY=py -3"
if not defined BASPY where python >nul 2>nul && set "BASPY=python"
if not defined BASPY goto ingenpython
set "PY=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if exist "%PY%" goto paket
echo Skapar projektets egen Python-miljo...
%BASPY% -m venv .venv
if not exist "%PY%" goto miljofel
:paket
echo Installerar paket. Forsta gangen tar det nagra minuter...
echo.
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto paketfel
echo.
echo KLART. Dubbelklicka nu pa kontrollera.bat
pause
exit /b 0
:ingenpython
echo Python hittades inte pa datorn.
echo Installera Python 3.12 fran https://www.python.org/downloads/
echo Kryssa i "Add python.exe to PATH" i installationen. Kor sedan den har filen igen.
pause
exit /b 1
:miljofel
echo Kunde inte skapa Python-miljon. Skicka en bild pa det har fonstret till Claude.
pause
exit /b 1
:paketfel
echo.
echo Installationen misslyckades. Skicka en bild pa det har fonstret till Claude.
pause
exit /b 1
