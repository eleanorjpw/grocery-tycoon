// Grocery Tycoon multiplayer relay.
//
// A room-based WebSocket relay so browser (and desktop) players can co-op
// without anyone hosting a direct connection. One player connects as the
// authoritative "host" (runs the game sim); everyone else connects as a
// "client". The relay just routes messages:
//   client -> host :  {cid, m}        (m = the client's game message)
//   host   -> all  :  send {to:"all", m} ; relay forwards m to every client
//   host   -> one  :  send {to:cid,   m} ; relay forwards m to that client
// Connect URL:  wss://<worker>/ws?room=CODE&role=host|client

import { DurableObject } from "cloudflare:workers";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/ws") {
      const room = (url.searchParams.get("room") || "").toUpperCase().slice(0, 12);
      if (!room) return new Response("missing room", { status: 400 });
      const stub = env.ROOMS.get(env.ROOMS.idFromName(room));
      return stub.fetch(request);
    }
    return new Response("Grocery Tycoon relay is up.", {
      status: 200,
      headers: { "content-type": "text/plain" },
    });
  },
};

export class Room extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.host = null;
    this.clients = new Map(); // cid -> ws
    this.nextCid = 1;
  }

  async fetch(request) {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected websocket", { status: 426 });
    }
    const role = new URL(request.url).searchParams.get("role") || "client";
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.accept(server, role);
    return new Response(null, { status: 101, webSocket: client });
  }

  accept(ws, role) {
    ws.accept();
    if (role === "host") {
      if (this.host) {
        try { ws.send(JSON.stringify({ t: "_error", e: "room_taken" })); ws.close(); } catch (e) {}
        return;
      }
      this.host = ws;
      try { ws.send(JSON.stringify({ t: "_hostok" })); } catch (e) {}
      // catch the host up on anyone who joined before it connected
      for (const cid of this.clients.keys()) {
        this.toHost({ cid, m: { t: "_connect" } });
      }
      ws.addEventListener("message", (ev) => this.fromHost(ev));
      const drop = () => { this.host = null; this.broadcastClients({ t: "_hostgone" }); };
      ws.addEventListener("close", drop);
      ws.addEventListener("error", drop);
    } else {
      const cid = this.nextCid++;
      this.clients.set(cid, ws);
      this.toHost({ cid, m: { t: "_connect" } });
      try { ws.send(JSON.stringify({ t: "_joined", cid })); } catch (e) {}
      if (!this.host) { try { ws.send(JSON.stringify({ t: "_nohost" })); } catch (e) {} }
      ws.addEventListener("message", (ev) => this.fromClient(cid, ev));
      const drop = () => { this.clients.delete(cid); this.toHost({ cid, m: { t: "_disconnect" } }); };
      ws.addEventListener("close", drop);
      ws.addEventListener("error", drop);
    }
  }

  fromHost(ev) {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    const m = msg.m;
    if (msg.to === "all") {
      for (const ws of this.clients.values()) { try { ws.send(JSON.stringify(m)); } catch (e) {} }
    } else {
      const ws = this.clients.get(msg.to);
      if (ws) { try { ws.send(JSON.stringify(m)); } catch (e) {} }
    }
  }

  fromClient(cid, ev) {
    let m;
    try { m = JSON.parse(ev.data); } catch (e) { return; }
    this.toHost({ cid, m });
  }

  toHost(obj) {
    if (this.host) { try { this.host.send(JSON.stringify(obj)); } catch (e) {} }
  }

  broadcastClients(m) {
    for (const ws of this.clients.values()) { try { ws.send(JSON.stringify(m)); } catch (e) {} }
  }
}
