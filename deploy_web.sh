#!/bin/bash
# Deploy the in-browser (WASM) build to Cloudflare Pages.
#
# One-time setup:  npx wrangler login   (authorize in your browser)
# Then:            ./build_web.sh && ./deploy_web.sh
#
# Live URL: https://grocery-tycoon.pages.dev
set -e
cd "$(dirname "$0")"

if [ ! -f web/index.html ]; then
  echo "No web/ build found -- running ./build_web.sh first..."
  ./build_web.sh
fi

npx -y wrangler@latest pages deploy web \
  --project-name grocery-tycoon --branch main --commit-dirty=true
