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
cp settings.py art.py world.py entities.py street.py game.py relay_net.py "$STAGE/"
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

# Browser WebSocket shim the game polls from Python (relay_net._WSWeb).
cat > web/gtnet.js <<'JS'
window.GTNet = {
  ws:null, inbox:[], open:false, err:false,
  connect:function(url){ try{ var self=this; this.inbox=[]; this.open=false; this.err=false;
    this.ws=new WebSocket(url);
    this.ws.onopen=function(){self.open=true;};
    this.ws.onmessage=function(e){self.inbox.push(e.data);};
    this.ws.onclose=function(){self.open=false;};
    this.ws.onerror=function(){self.err=true;};
  }catch(e){this.err=true;} },
  send:function(s){ try{ if(this.ws&&this.ws.readyState===1) this.ws.send(s);}catch(e){} },
  poll:function(){ if(!this.inbox.length) return ""; var m=this.inbox.join(String.fromCharCode(1)); this.inbox=[]; return m; },
  status:function(){ return this.err?2:(this.open?1:0); },
  close:function(){ try{ if(this.ws) this.ws.close(); }catch(e){} this.open=false; }
};
JS
# load the shim before the game starts
python3 - web/index.html <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
tag = '<script src="gtnet.js"></script>'
if tag not in s:
    if "</head>" in s:
        s = s.replace("</head>", tag + "\n</head>", 1)
    else:
        s = s.replace("<body", tag + "\n<body", 1)
    open(p, "w").write(s)
PY

echo
echo "Built to ./web  (open web/index.html via a local server, or deploy it)."
echo "Local preview:  $PY -m http.server -d web 8000   then visit localhost:8000"
