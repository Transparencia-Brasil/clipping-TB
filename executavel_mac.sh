#!/bin/bash
set -e

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR_SCRIPT"

if [ ! -d ".venv" ]; then
    echo "Ambiente virtual não encontrado. Criando..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

streamlit run app.py