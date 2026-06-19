#!/bin/bash
# Build a standalone app of Grocery Tycoon for THIS operating system, so friends
# don't need Python installed -- they just double-click the result.
#
# Note: you can only build for the OS you run this on (a Mac build runs on Macs,
# a Windows build runs on Windows). Run it on each platform you want to support.
set -e
cd "$(dirname "$0")"

PY="./.venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "Installing PyInstaller..."
"$PY" -m pip install --quiet --upgrade pyinstaller

echo "Building..."
"$PY" -m PyInstaller --noconfirm --clean \
  --name "GroceryTycoon" \
  --windowed \
  --onedir \
  main.py

echo
echo "Done. Find the app under: dist/GroceryTycoon/"
echo "On macOS that's 'dist/GroceryTycoon/GroceryTycoon.app' -- zip it and send it."
echo "On Windows it's 'dist/GroceryTycoon/GroceryTycoon.exe'."
