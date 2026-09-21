#!/bin/bash
cd "$(dirname "$0")"
PY=python3
[ -x "env/bin/python" ] && PY=env/bin/python
[ -x "venv/bin/python" ] && PY=venv/bin/python
[ -x ".venv/bin/python" ] && PY=.venv/bin/python
if ! "$PY" -c "import streamlit" 2>/dev/null; then echo "Paketen är inte installerade än. Dubbelklicka på installera.command"; read -n 1 -s -r; exit 1; fi
echo "Startar Kvittens. Stäng det här fönstret för att avsluta appen."
"$PY" -m streamlit run app.py --server.address localhost
