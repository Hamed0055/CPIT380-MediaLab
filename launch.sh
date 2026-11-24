#!/bin/sh
set -eu

cd -- "$(dirname -- "$0")"
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m streamlit run main.py "$@"
fi
exec python3 -m streamlit run main.py "$@"
