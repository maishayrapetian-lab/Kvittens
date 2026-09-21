#!/bin/bash
cd "$(dirname "$0")"
PY=python3
[ -x "env/bin/python" ] && PY=env/bin/python
[ -x "venv/bin/python" ] && PY=venv/bin/python
[ -x ".venv/bin/python" ] && PY=.venv/bin/python
"$PY" kontrollera.py
KOD=$?
[ "$KOD" = "3" ] && echo "Paket saknas: dubbelklicka på installera.command"
[ "$KOD" = "2" ] && open -e .streamlit/secrets.toml
read -n 1 -s -r -p "Tryck på en tangent för att stänga."
