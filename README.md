# 🛒 Grocery Tycoon

A 32-bit, Stardew-Valley-style grocery store management game built with Python +
pygame. You inherit a **run-down corner store** — filthy floors, broken shelves,
flickering lights — and have to fix it up into the best grocery in town.

All the pixel art is **generated procedurally in code** (no image files), so the
whole game is just Python.

## 🎮 Play instantly in your browser

**▶️ https://grocery-tycoon.pages.dev** — no download, no Python, just click and play.

A WebAssembly build hosted on Cloudflare Pages. **Co-op works right in the
browser too** — one person clicks *Host Co-op Game* to get a room code, friends
open the same link, click *Join with Room Code*, type it in, and you're running
the store together. No download, no IP addresses (see Multiplayer below).

## 📨 Send it to friends (one link)

Share this link — it downloads the whole game as a zip:

**➡️ https://github.com/eleanorjpw/grocery-tycoon/archive/refs/heads/main.zip**

Or send the repo page so they can read along: **https://github.com/eleanorjpw/grocery-tycoon**

Your friend unzips it, then double-clicks **`Play Grocery Tycoon.command`** (Mac)
or **`Play Grocery Tycoon.bat`** (Windows) and presses **Join**. First launch
auto-installs what it needs (they just need [Python 3](https://www.python.org/downloads/)).
Full step-by-step for them is in [`FOR_FRIENDS.md`](FOR_FRIENDS.md).

## Run it

**Easiest:** double-click `Play Grocery Tycoon.command` in Finder.

**From a terminal:**
```bash
cd grocery-tycoon
python3 -m venv .venv
./.venv/bin/python -m pip install pygame
./.venv/bin/python main.py
```

## Controls

| Action | Keys |
|---|---|
| Move | `W A S D` or Arrow keys |
| Interact (stock / repair / clean / buy shop) | `Space` or `E` |
| Open management menu | `Tab` (or `M`) |
| Pause / resume | `P` (or the Pause button) |
| Close menu / quit | `Esc` |

- **Face a shelf** and interact to restock it from the stockroom, or **repair**
  it if it's broken (costs **$80**).
- **Face a stockroom crate** (the boxes in the back) to open the ordering menu —
  the crates *are* your stockroom: deliveries land there and the boxes visibly
  fill up or empty out based on how much backstock you're holding.
- **Stand on grime** and interact to mop it up.
- **Stand behind a register** to ring up the checkout line yourself (until you
  hire a cashier).
- **Buy more shelves** in the Renovations menu ($160 each) to grow your store
  along the back wall.
- Each working shelf shows a little **icon sign** above it so you can tell at a
  glance what it sells.

> ⚠️ **Don't run out of stock!** If every shelf, the stockroom, *and* incoming
> deliveries are all empty, you have nothing to sell and the store closes for
> good. Keep something on order. (Prices are tuned to modern mid-2020s grocery
> costs, and there's **no daily rent** — your main costs are restock orders,
> wages and utilities.)

## Troubleshooting

- **Black screen where the store should be (HUD shows, store doesn't)** — this
  is a macOS Retina/HiDPI quirk. The game now opens with `pygame.SCALED`, which
  fixes it. Just make sure you're on the current `game.py` and relaunch.
- **Window is too tall for the screen** — `pygame.SCALED` lets the OS scale the
  window to fit; you can also drag/resize it.

## How to play

You walk the floor in real time while the store clock runs from **8 AM to 8 PM**.
Shoppers come in, grab items off stocked shelves, and queue at the checkout.
At closing time you get a **day summary** (revenue vs. wages, rent, utilities,
spoilage and theft), then open the next day.

Use the **management menu** (`Tab`) to:

- **Order Stock** — buy cases of 12. Deliveries arrive *the next morning*, so
  you have to forecast demand. Perishables spoil fast without refrigeration.
- **Staff** — hire Cashiers, Stockers, Cleaners and Security. Wages are paid
  nightly and overworked staff with low morale may quit.
- **Renovations** — one-time upgrades (bright lighting, new floors,
  refrigeration, security cameras, storefront signage, **See the World**) and
  **buying extra shelves** ($160 each).
- **Finances** — see the books and take a loan if cash runs low.

The **Order Stock** menu flags what's empty: a red dot + **OUT!** means that
product's shelves are bare, a yellow **low** means they're nearly empty, and the
header warns how many products are out — so you can see at a glance what to buy.

You can **pause** anytime with `P` or the Pause button (single-player and host).

## See the World — buying other shops

Buy the **See the World** renovation ($3,000) and you can **walk out your front
door** onto the street. Stroll the sidewalk, walk up to another shop's door, and
press `E` to **buy it** — each shop you own pays you a **daily passive income**
(Cozy Cafe, Flower Shop, Bookstore, Electronics). Walk up to **YOUR STORE** and
press `E` to head back inside. In co-op, friends can come out to the street with
you and the shops you own stay in sync for everyone.

## Multiplayer (room-code co-op, no download for friends)

Co-op uses **room codes** through a tiny **Cloudflare relay**, so it works the
same in the **browser** and the **desktop app**, with no IP addresses, no
port-forwarding, and no Tailscale.

From the title screen:

- **Host Co-op Game** — you become the authoritative host and get a short
  **room code** (e.g. `MILK`). Hit **Copy Code** to share it, then **START GAME**.
- **Join with Room Code** — type the host's code (or **Paste**) and hit **Join**.
  You spawn into their store with a name tag.

The easiest way to play with a friend who has nothing installed:
1. You open **https://grocery-tycoon.pages.dev** and click **Host Co-op Game**.
2. Send them the room code.
3. They open the **same link**, click **Join with Room Code**, type it, and play.

Everyone can walk around and **stock shelves, mop, repair, and run registers**,
and anyone can open the **management menu** to order stock, hire staff, and buy
renovations from the **shared budget**. One player's game is authoritative — the
day clock and money live there; everyone else's inputs and snapshots flow
through the relay.

### How it works
- `relay/` is a Cloudflare **Worker + Durable Object** that just forwards
  messages between everyone in a room (deploy with `cd relay && npx wrangler deploy`).
- `relay_net.py` is the game-side transport: desktop uses the `websocket-client`
  library; the browser build uses a tiny JS `WebSocket` shim (`gtnet.js`,
  injected by `build_web.sh`).
- The relay URL is `RELAY_URL` in `settings.py`.

Browsers can't host or use raw TCP sockets, which is why co-op needs the relay
(a shared server in the middle) rather than peer-to-peer. The legacy direct-IP
code (`net.py`, `NET_PORT`) is left in the repo but no longer used by the UI.

### Still want to hand friends the desktop app?
The downloadable version plays co-op through the same room codes. Get it to them
with `./make_share.sh` (a zip), `./build_standalone.sh` (a no-Python app), or the
GitHub link. There's a friend guide in **`FOR_FRIENDS.md`**.

## Cloud saves (your account)

Keep multiple named stores on your account and load them from any device or the
browser:

- On the title screen click **Cloud Saves / Account** → create an account
  (username + password) or sign in.
- **+ New Game** names a save slot; while playing, hit **P** (pause) → **Save**.
- Your slots show up under **Cloud Saves** with **Load** / **Delete**.

Saves live in a Cloudflare **D1** database behind the `saves/` Worker
(`SAVES_URL` in `settings.py`). Passwords are salted-SHA-256 hashed — casual-grade
security for a game, so don't reuse an important password. Deploy/update the
backend with `cd saves && npx wrangler deploy`.

## The real-world challenges (researched, then built in)

The mechanics are modelled on the actual headaches of running a grocery store:

- **Spoilage / perishables** — produce, dairy, meat and bakery items rot daily
  unless you install **refrigeration** (which then raises your energy bill — a
  real trade-off).
- **Shrinkage** — shoplifters cost you stock and money. **Security** staff and
  **cameras** cut the losses.
- **Thin margins** — retail markups are small; utilities and wages eat your
  profit every single night, and running completely out of stock ends the game.
- **Staffing & turnover** — labor is your biggest controllable cost, and grocery
  retail has brutal turnover, so staff can quit on you.
- **Supply-chain disruptions** — random delivery delays and wholesale price
  spikes.
- **Equipment failure / power outages** — outages kill the lights and fridges
  and slow your registers.
- **Health inspections** — let the place get filthy and you'll get fined.
- **Demand forecasting & reputation** — empty shelves, long lines and a dirty
  store wreck your reputation, which drives how many shoppers show up.

Sources that informed the design:
[IT Retail – operating challenges](https://www.itretail.com/blog/operating-a-grocery-store-challenges),
[IT Retail – causes of shrinkage](https://www.itretail.com/blog/what-causes-shrinkage-in-grocery-stores),
[Grocery Dive – economic pressures](https://www.grocerydive.com/news/grocers-operations-economic-challenges-fmi/757847/),
[LogicERP – 15 challenges](https://www.logicerp.com/blog/15-challenges-of-operating-a-grocery-store-and-how-to-overcome-them-with-logic-erp/).

## Project layout

| File | What it is |
|---|---|
| `main.py` | Entry point (self-bootstraps the venv + pygame on first run) |
| `game.py` | Engine: game loop, simulation, economy, events, HUD, menus, multiplayer |
| `relay_net.py` | Room-code multiplayer transport (desktop + browser WebSocket) |
| `relay/` | Cloudflare Worker + Durable Object that relays co-op messages |
| `net.py` | Legacy direct-IP networking (no longer used by the UI) |
| `street.py` | The street map + buyable shops (the "See the World" upgrade) |
| `entities.py` | Player, Customers, Staff + BFS pathfinding |
| `world.py` | Tile map and fixtures (shelves, checkouts, stockroom) |
| `art.py` | Procedural 32-bit pixel-art sprites |
| `settings.py` | Tunables: palette, products, staff, upgrades, balance, port |
| `smoke_test.py` | Headless test that runs the single-player sim for several days |
| `net_test.py` | Headless test that runs a host + client over the loopback |
| `make_share.sh` | Builds a zip of the game to send to friends |
| `build_standalone.sh` | Builds a no-Python-needed standalone app (per OS) |
| `web_main.py` | Async entry point for the browser (WASM) build |
| `build_web.sh` | Compiles to WebAssembly with pygbag into `web/` |
| `serve_web.py` | Local preview server for the WASM build |
| `deploy_web.sh` | Deploys `web/` to Cloudflare Pages |
| `web_runtime/` | Vendored pygame WASM wheel (keeps web builds reproducible) |
| `FOR_FRIENDS.md` | Friend-facing "how to join" guide |

### Updating the browser version on Cloudflare

```bash
npx wrangler login     # one-time, authorize in your browser
./build_web.sh         # compile to WASM into web/
./deploy_web.sh        # publish to https://grocery-tycoon.pages.dev
```

To update the relay: `cd relay && npx wrangler deploy`.

Tip: almost everything is tunable in `settings.py` — prices, wages, upgrade
costs, store hours and the colour palette.
