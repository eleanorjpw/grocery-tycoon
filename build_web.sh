#!/bin/bash
# Compile Grocery Tycoon to WebAssembly (runs in a browser) with pygbag,
# and put the result in ./web  (ready to deploy to Cloudflare Pages).
set -e
cd "$(dirname "$0")"

PY="./.venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "Installing pygbag (pinned to match the vendored runtime wheel)..."
"$PY" -m pip install --quiet "pygbag==0.9.3"

# Stage only the files the web build needs (no net.py, no tests, no venv).
STAGE="$(mktemp -d)/grocerytycoon"
mkdir -p "$STAGE"
cp settings.py art.py world.py entities.py street.py game.py "$STAGE/"
cp web_main.py "$STAGE/main.py"

echo "Building WASM bundle..."
"$PY" -m pygbag --build "$STAGE/main.py"

rm -rf web
mkdir -p web
cp -r "$STAGE/build/web/." web/
rm -rf "$(dirname "$STAGE")"

# pygbag fetches the runtime from its CDN, but the pygame wheel must be hosted
# alongside the app. We vendor it so the deploy is reproducible.
cp -r web_runtime/cdn web/

# WASM needs cross-origin isolation; "credentialless" keeps it while still
# allowing the runtime to load from the pygame-web CDN. Cloudflare reads this.
cat > web/_headers <<'HDR'
/*
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: credentialless
HDR

echo
echo "Built to ./web  (open web/index.html via a local server, or deploy it)."
echo "Local preview:  $PY -m http.server -d web 8000   then visit localhost:8000"
