"""
Async client for the cloud-save backend (saves/ Worker).

Non-blocking, polled API so the game loop never stalls on the network:

    h = api.request("/login", {"username": u, "password": p})
    ... each frame ...
    r = api.poll(h)
    if r is None:        # still in flight
        ...
    elif r[0] == "err":  # network/transport failure
        show(r[1])
    else:                # ("ok", json_obj) -- HTTP responded (may carry "error")
        obj = r[1]

Desktop uses urllib in a background thread; the browser build uses a tiny JS
`fetch` shim (window.GTSave) injected by build_web.sh.
"""
import json
import sys

from settings import SAVES_URL

IS_WEB = (sys.platform == "emscripten")


class SaveAPI:
    def __init__(self, base=SAVES_URL):
        self.base = base
        self._results = {}
        self._n = 0

    def request(self, path, payload):
        url = self.base + path
        if IS_WEB:
            import platform
            rid = platform.window.GTSave.request(url, json.dumps(payload))
            return ("web", rid)
        import threading
        self._n += 1
        h = self._n
        self._results[h] = None
        threading.Thread(target=self._do, args=(h, url, payload),
                         daemon=True).start()
        return ("desk", h)

    def _do(self, h, url, payload):
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "GroceryTycoon/1.0 (+desktop)"},
                method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                self._results[h] = ("ok", json.loads(r.read()))
        except urllib.error.HTTPError as e:
            try:
                self._results[h] = ("ok", json.loads(e.read()))
            except Exception:
                self._results[h] = ("err", f"server error {e.code}")
        except Exception as e:
            self._results[h] = ("err", "couldn't reach the server")

    def poll(self, handle):
        kind, h = handle
        if kind == "web":
            import platform
            raw = platform.window.GTSave.get(h)
            raw = "" if raw is None else str(raw)
            if not raw:
                return None
            if raw.startswith("OK"):
                try:
                    return ("ok", json.loads(raw[2:]))
                except Exception:
                    return ("err", "bad response")
            return ("err", raw[3:] if raw.startswith("ERR") else "network error")
        r = self._results.get(h)
        if r is None:
            return None
        self._results.pop(h, None)
        return r
