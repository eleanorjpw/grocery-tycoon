"""
WebSocket transport for room-code multiplayer through the Cloudflare relay.

Mirrors the API of net.py (NetServer/NetClient) so game.py can swap transports
with almost no change:

  RelayServer.poll() -> [(cid, msg), ...]   broadcast(obj)   send_to(cid, obj)
  RelayClient.poll() -> [msg, ...]          send(obj)        .connected

Two underlying sockets:
  * desktop  -> the `websocket-client` library, in a background thread
  * browser  -> the JS `WebSocket` via pygbag's `platform.window.GTNet` shim
                (no threads; the game loop polls it)
"""
import json
import sys

from settings import RELAY_URL

IS_WEB = (sys.platform == "emscripten")

SEP = "\x01"   # message separator used by the browser JS shim (never in JSON)


def _sanitize(s, n=12):
    return "".join(c for c in str(s) if c.isalnum())[:n] or "Player"


# --------------------------------------------------------- desktop socket ----
class _WSDesktop:
    def __init__(self, url):
        import threading
        import queue
        self._queue = queue
        self.inbox = queue.Queue()
        self.connected = False
        self.error = False
        self.running = True
        self._ws = None
        threading.Thread(target=self._run, args=(url,), daemon=True).start()

    def _run(self, url):
        import websocket
        try:
            self._ws = websocket.create_connection(url, timeout=8)
            self._ws.settimeout(0.2)
            self.connected = True
        except Exception:
            self.error = True
            self.connected = False
            return
        while self.running:
            try:
                data = self._ws.recv()
            except Exception as e:
                if e.__class__.__name__ == "WebSocketTimeoutException":
                    continue
                break
            if not data:
                break
            try:
                self.inbox.put(json.loads(data))
            except Exception:
                pass
        self.connected = False

    def send(self, obj):
        try:
            if self._ws:
                self._ws.send(json.dumps(obj))
        except Exception:
            self.connected = False

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except self._queue.Empty:
                break
        return out

    def close(self):
        self.running = False
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass


# ----------------------------------------------------------- browser socket --
class _WSWeb:
    def __init__(self, url):
        import platform
        self._p = platform
        self.error = False
        try:
            platform.window.GTNet.connect(url)
        except Exception:
            self.error = True

    @property
    def connected(self):
        try:
            return int(self._p.window.GTNet.status()) == 1
        except Exception:
            return False

    def send(self, obj):
        try:
            self._p.window.GTNet.send(json.dumps(obj))
        except Exception:
            pass

    def poll(self):
        try:
            raw = self._p.window.GTNet.poll()
        except Exception:
            return []
        raw = "" if raw is None else str(raw)
        out = []
        if raw:
            for part in raw.split(SEP):
                if part:
                    try:
                        out.append(json.loads(part))
                    except Exception:
                        pass
        return out

    def close(self):
        try:
            self._p.window.GTNet.close()
        except Exception:
            pass


def _make_ws(url):
    return _WSWeb(url) if IS_WEB else _WSDesktop(url)


def _url(code, role, name):
    return f"{RELAY_URL}?room={_sanitize(code)}&role={role}&name={_sanitize(name)}"


# --------------------------------------------------------------- host --------
class RelayServer:
    """Authoritative host's view of the relay (acts like NetServer)."""
    def __init__(self, code, name="Host"):
        self.code = _sanitize(code)
        self.ws = _make_ws(_url(self.code, "host", name))
        self.error = None

    def poll(self):
        out = []
        for env in self.ws.poll():
            t = env.get("t")
            if t == "_error":
                self.error = env.get("e", "error")
                continue
            if t in ("_hostok", "_hostgone"):
                continue
            cid, m = env.get("cid"), env.get("m")
            if cid is not None and isinstance(m, dict):
                out.append((cid, m))
        return out

    def broadcast(self, obj):
        self.ws.send({"to": "all", "m": obj})

    def send_to(self, cid, obj):
        self.ws.send({"to": cid, "m": obj})

    @property
    def connected(self):
        return self.ws.connected

    def close(self):
        self.ws.close()


# -------------------------------------------------------------- client -------
class RelayClient:
    """A joining player's connection to the relay (acts like NetClient)."""
    def __init__(self, code, name="Player"):
        self.code = _sanitize(code)
        self.ws = _make_ws(_url(self.code, "client", name))
        self.cid = None
        self.no_host = False
        self.lost = False

    def poll(self):
        out = []
        for m in self.ws.poll():
            t = m.get("t")
            if t == "_joined":
                self.cid = m.get("cid")
                continue
            if t == "_nohost":
                self.no_host = True
                continue
            if t == "_hostgone":
                self.lost = True
                continue
            out.append(m)
        return out

    def send(self, obj):
        self.ws.send(obj)

    @property
    def connected(self):
        return self.ws.connected and not self.lost

    def close(self):
        self.ws.close()
