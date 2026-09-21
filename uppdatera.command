#!/bin/bash
cd "$(dirname "$0")"
python3 uppdatera.py
echo
read -n 1 -s -r -p "Tryck på en tangent för att stänga."
