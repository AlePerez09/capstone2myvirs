#!/usr/bin/env bash
# MyVIRS Team A one-step setup for Mac and Linux (and Git Bash on Windows).
# Creates a virtual environment in .venv, installs everything in
# requirements.txt (spaCy's English model included), and runs the tests.
# Usage: ./setup.sh
set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
    echo "Python 3 not found. Install Python 3.10-3.13 from python.org first."
    exit 1
fi

echo "== Creating .venv with $($PY --version)"
"$PY" -m venv .venv
if [ -f .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi

echo "== Installing packages (a few minutes the first time)"
"$VPY" -m pip install --upgrade pip -q
"$VPY" -m pip install -r requirements.txt

echo "== Running the tests"
"$VPY" -m pytest tests -q

echo
echo "Setup done. Activate the environment before running anything:"
if [ -f .venv/Scripts/activate ]; then
    echo "    source .venv/Scripts/activate"
else
    echo "    source .venv/bin/activate"
fi
echo "Then try: python priority_ranking.py --text-file data/samples/photosynthesis.txt --subject-aware"
