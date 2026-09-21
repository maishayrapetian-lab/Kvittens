#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f .streamlit/secrets.toml ]; then echo "Filen finns inte än. Dubbelklicka på kontrollera.command först."; read -n 1 -s -r; exit 1; fi
open -e .streamlit/secrets.toml
