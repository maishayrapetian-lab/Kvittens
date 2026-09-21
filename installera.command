#!/bin/bash
cd "$(dirname "$0")"
echo "=== Installerar Kvittens ==="
if ! command -v python3 >/dev/null; then echo "Python hittades inte. Installera Python 3.12 från https://www.python.org/downloads/"; read -n 1 -s -r -p "Tryck på en tangent."; exit 1; fi
[ -x ".venv/bin/python" ] || [ -x "venv/bin/python" ] || python3 -m venv .venv
PY=.venv/bin/python; [ -x "venv/bin/python" ] && PY=venv/bin/python
"$PY" -m pip install --upgrade pip && "$PY" -m pip install --upgrade -r requirements.txt && echo && echo "KLART. Dubbelklicka nu på kontrollera.command" || echo "Installationen misslyckades. Skicka en bild på det här fönstret till Claude."
read -n 1 -s -r -p "Tryck på en tangent för att stänga."
