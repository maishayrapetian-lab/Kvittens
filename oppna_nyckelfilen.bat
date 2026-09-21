@echo off
cd /d "%~dp0"
if not exist ".streamlit" mkdir ".streamlit"
if not exist ".streamlit\secrets.toml" echo Filen finns inte an. Dubbelklicka pa kontrollera.bat forst. & pause & exit /b 1
start "" notepad ".streamlit\secrets.toml"
