// Grocery Tycoon account + cloud-save backend (Cloudflare Worker + D1).
//
// Casual-grade accounts: a username + password (salted SHA-256 hash). Each
// account has any number of named save slots holding a JSON game state.
// Endpoints (all POST JSON): /register /login /list /save /load /delete

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

async function sha(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function cleanUser(u) {
  return String(u || "").trim().toLowerCase().replace(/[^a-z0-9_]/g, "").slice(0, 20);
}
function cleanName(n) {
  return String(n || "").trim().replace(/[^A-Za-z0-9 _\-]/g, "").slice(0, 24) || "save";
}

async function ensure(db) {
  await db.prepare(
    "CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, pwhash TEXT, salt TEXT, created INTEGER)"
  ).run();
  await db.prepare(
    "CREATE TABLE IF NOT EXISTS saves (username TEXT, name TEXT, data TEXT, updated INTEGER, PRIMARY KEY(username, name))"
  ).run();
}

async function auth(db, u, p) {
  const row = await db.prepare("SELECT pwhash, salt FROM accounts WHERE username=?")
    .bind(u).first();
  if (!row) return false;
  return (await sha(row.salt + ":" + p)) === row.pwhash;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const path = new URL(request.url).pathname;
    if (request.method !== "POST") return json({ error: "POST only" }, 405);

    let body = {};
    try { body = await request.json(); } catch (e) { return json({ error: "bad json" }, 400); }
    const db = env.DB;
    try { await ensure(db); } catch (e) { return json({ error: "db init: " + e.message }, 500); }

    const u = cleanUser(body.username);
    const p = String(body.password || "");

    if (path === "/register") {
      if (u.length < 3) return json({ error: "username needs 3+ letters/numbers" }, 400);
      if (p.length < 4) return json({ error: "password needs 4+ characters" }, 400);
      const ex = await db.prepare("SELECT username FROM accounts WHERE username=?").bind(u).first();
      if (ex) return json({ error: "that username is taken" }, 409);
      const salt = crypto.randomUUID();
      const pwhash = await sha(salt + ":" + p);
      await db.prepare("INSERT INTO accounts (username,pwhash,salt,created) VALUES (?,?,?,?)")
        .bind(u, pwhash, salt, Date.now()).run();
      return json({ ok: true, username: u });
    }

    // everything else requires valid credentials
    if (!(await auth(db, u, p))) return json({ error: "wrong username or password" }, 401);

    if (path === "/login") {
      return json({ ok: true, username: u });
    }
    if (path === "/list") {
      const r = await db.prepare(
        "SELECT name, updated FROM saves WHERE username=? ORDER BY updated DESC"
      ).bind(u).all();
      return json({ ok: true, saves: r.results || [] });
    }
    if (path === "/save") {
      const name = cleanName(body.name);
      const data = String(body.data || "");
      if (data.length > 300000) return json({ error: "save too large" }, 413);
      await db.prepare(
        "INSERT INTO saves (username,name,data,updated) VALUES (?,?,?,?) " +
        "ON CONFLICT(username,name) DO UPDATE SET data=excluded.data, updated=excluded.updated"
      ).bind(u, name, data, Date.now()).run();
      return json({ ok: true, name });
    }
    if (path === "/load") {
      const name = cleanName(body.name);
      const row = await db.prepare("SELECT data FROM saves WHERE username=? AND name=?")
        .bind(u, name).first();
      if (!row) return json({ error: "no such save" }, 404);
      return json({ ok: true, name, data: row.data });
    }
    if (path === "/delete") {
      const name = cleanName(body.name);
      await db.prepare("DELETE FROM saves WHERE username=? AND name=?").bind(u, name).run();
      return json({ ok: true });
    }
    return json({ error: "unknown endpoint" }, 404);
  },
};
