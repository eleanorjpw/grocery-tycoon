#!/bin/bash
# Build a zip of the game you can send to friends so they can run it and JOIN.
# Usage: ./make_share.sh   ->   creates ~/Desktop/GroceryTycoon.zip
set -e
cd "$(dirname "$0")"

OUT="${1:-$HOME/Desktop/GroceryTycoon.zip}"
TMP="$(mktemp -d)/GroceryTycoon"
mkdir -p "$TMP"

# copy only what a friend needs (skip venv, caches, builds, saved IP)
for f in *.py *.md "Play Grocery Tycoon.command" "Play Grocery Tycoon.bat"; do
  [ -e "$f" ] && cp "$f" "$TMP/"
done

chmod +x "$TMP/Play Grocery Tycoon.command" 2>/dev/null || true

rm -f "$OUT"
( cd "$(dirname "$TMP")" && zip -r -q "$OUT" "GroceryTycoon" )
rm -rf "$(dirname "$TMP")"

echo "Created: $OUT"
echo "Send that zip to your friends. They unzip it and double-click"
echo "  'Play Grocery Tycoon.command' (Mac) or 'Play Grocery Tycoon.bat' (Windows),"
echo "then press JOIN. See FOR_FRIENDS.md inside the zip."
