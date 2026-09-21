#!/bin/bash
cd "$(dirname "$0")"
PY=python3
[ -x "env/bin/python" ] && PY=env/bin/python
[ -x "venv/bin/python" ] && PY=venv/bin/python
[ -x ".venv/bin/python" ] && PY=.venv/bin/python
echo "Läser av testbilderna. Det tar ett par minuter..."
"$PY" utvardera.py
echo
echo "Resultatet finns också i filen utvardering_resultat.txt"
read -n 1 -s -r -p "Tryck på en tangent för att stänga."
