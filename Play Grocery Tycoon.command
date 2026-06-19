#!/bin/bash
# Double-click this in Finder to play. First run sets itself up automatically.
cd "$(dirname "$0")" || exit 1

# Prefer the local venv if it already exists; otherwise let main.py bootstrap.
if [ -x ".venv/bin/python" ]; then
  exec ./.venv/bin/python main.py
elif command -v python3 >/dev/null 2>&1; then
  exec python3 main.py
else
  echo "Python 3 is required. Install it from https://www.python.org/downloads/"
  echo "Press any key to close..."; read -r -n 1
  exit 1
fi
