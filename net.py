"""
Tiny TCP networking for Grocery Tycoon multiplayer.

Protocol: newline-delimited JSON objects over a plain TCP socket. The host runs
a NetServer (authoritative game). Each friend runs a NetClient that connects to
the host's IP. Works on a LAN out of the box; across the internet it works too
if the host is reachable (port-forward or a tunnel like Tailscale/ZeroTier).
"""
import json
import queue
import socket
import threading

from settings import NET_PORT

PORT = NET_PORT


def _encode(obj):
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


class _LineReader:
    """Accumulates raw bytes and yields complete JSON messages."""
    def __init__(self):
        self.buf = b""

    def feed(self, data):
        self.buf += data
        out = []
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line.decode("utf-8")))
                except ValueError:
                    pass
        return out


def local_ip():
    """Best-effort LAN IP of this machine (for showing the host address)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# ------------------------------------------------------------------ server ----
class NetServer:
    """Accepts client connections and queues their messages for the host loop."""
    def __init__(self, port=PORT):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(8)
        self.sock.settimeout(0.2)
        self.clients = {}          # cid -> {"sock", "reader"}
        self.inbox = queue.Queue()  # (cid, message)
        self.next_cid = 1
        self.running = True
        self.lock = threading.Lock()
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, _addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            cid = self.next_cid
            self.next_cid += 1
            conn.settimeout(0.2)
            with self.lock:
                self.clients[cid] = {"sock": conn, "reader": _LineReader()}
            self.inbox.put((cid, {"t": "_connect"}))
            threading.Thread(target=self._client_loop, args=(cid, conn),
                             daemon=True).start()

    def _client_loop(self, cid, conn):
        while self.running:
            try:
                data = conn.recv(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            with self.lock:
                info = self.clients.get(cid)
            if not info:
                break
            for msg in info["reader"].feed(data):
                self.inbox.put((cid, msg))
        self.inbox.put((cid, {"t": "_disconnect"}))
        with self.lock:
            self.clients.pop(cid, None)
        try:
            conn.close()
        except OSError:
            pass

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return out

    def broadcast(self, obj):
        data = _encode(obj)
        with self.lock:
            items = list(self.clients.items())
        dead = []
        for cid, info in items:
            try:
                info["sock"].sendall(data)
            except OSError:
                dead.append(cid)
        if dead:
            with self.lock:
                for cid in dead:
                    self.clients.pop(cid, None)

    def send_to(self, cid, obj):
        with self.lock:
            info = self.clients.get(cid)
        if info:
            try:
                info["sock"].sendall(_encode(obj))
            except OSError:
                pass

    def client_count(self):
        with self.lock:
            return len(self.clients)

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
        with self.lock:
            for info in self.clients.values():
                try:
                    info["sock"].close()
                except OSError:
                    pass
            self.clients.clear()


# ------------------------------------------------------------------ client ----
class NetClient:
    """Connects to a host and queues incoming messages for the client loop."""
    def __init__(self, host, port=PORT, name="Player", timeout=6.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.sock.settimeout(0.2)
        self.reader = _LineReader()
        self.inbox = queue.Queue()
        self.running = True
        self.connected = True
        self.name = name
        threading.Thread(target=self._loop, daemon=True).start()
        self.send({"t": "hello", "name": name})

    def _loop(self):
        while self.running:
            try:
                data = self.sock.recv(16384)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            for msg in self.reader.feed(data):
                self.inbox.put(msg)
        self.connected = False

    def send(self, obj):
        try:
            self.sock.sendall(_encode(obj))
        except OSError:
            self.connected = False

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return out

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
