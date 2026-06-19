# 🛒 Grocery Tycoon

A 32-bit, Stardew-Valley-style grocery store management game built with Python +
pygame. You inherit a **run-down corner store** — filthy floors, broken shelves,
flickering lights — and have to fix it up into the best grocery in town.

All the pixel art is **generated procedurally in code** (no image files), so the
whole game is just Python.

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

## Multiplayer (play with friends across devices)

From the title screen:

- **Host Multiplayer** — runs your store and shows your address (`IP:50007`).
  Hit **Copy Address** to put it on your clipboard and send it to friends, then
  click **START GAME** when everyone's in the lobby.
- **Join Multiplayer** — type the host's address (or hit **Paste** / Cmd+V if a
  friend sent it to you) and connect. The last address you used is remembered
  for next time. You spawn into their store with a name tag and can help out.

Everyone can walk around and **stock shelves, mop, repair, and run registers**,
and (since you chose full co-op) anyone can open the **management menu** to
order stock, hire staff, and buy renovations from the **shared budget**. The
host's game is authoritative — the day clock and money all live on the host.

### ⚠️ First: your friends need the game on their own device
Multiplayer is peer-to-peer — each person runs *their own copy* of the game and
connects to your hosted store. Your friends can't press **Join** until the game
is on their computer. Get it to them one of three ways:

1. **Send them the folder (easiest).** Run `./make_share.sh` — it makes a
   `GroceryTycoon.zip` on your Desktop. Send it (AirDrop, email, Drive…). They
   unzip and double-click **`Play Grocery Tycoon.command`** (Mac) or
   **`Play Grocery Tycoon.bat`** (Windows). First launch auto-installs what it
   needs. They just need **Python 3** (free, usually already on Macs).
2. **Send them a standalone app (no Python needed).** Run `./build_standalone.sh`
   to produce `dist/GroceryTycoon.app` (on Mac) / `GroceryTycoon.exe` (on
   Windows); zip and send it. Note you can only build for the OS you're on, so
   build on a Mac for Mac friends and on Windows for Windows friends.
3. **Share the source** (e.g. a GitHub repo) and have them run `python3 main.py`.

There's a friend-facing guide, **`FOR_FRIENDS.md`**, included in the zip with
step-by-step instructions.

### Same WiFi / LAN
Easiest case. The host clicks *Host Multiplayer* and reads off the
`192.168.x.x` address shown in the lobby; friends on the same network pick
*Join Multiplayer* and type it in. Done.

### Across the internet
A pygame game has no matchmaking server, so a far-away friend needs a path to
the host. Two common options:

1. **A mesh VPN (easiest, recommended)** — both install a free tool like
   [Tailscale](https://tailscale.com) or [ZeroTier](https://zerotier.com). They
   put both machines on one private network; the friend then joins using the
   host's Tailscale/ZeroTier IP (e.g. `100.x.x.x`) exactly like LAN. No router
   changes.
2. **Port-forwarding** — the host forwards TCP port **50007** on their router to
   their machine, and friends connect to the host's public IP. More fiddly and
   exposes the port, so option 1 is preferred.

The port is configurable via `NET_PORT` in `settings.py`.

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
| `net.py` | TCP host/client networking (newline-delimited JSON) |
| `street.py` | The street map + buyable shops (the "See the World" upgrade) |
| `entities.py` | Player, Customers, Staff + BFS pathfinding |
| `world.py` | Tile map and fixtures (shelves, checkouts, stockroom) |
| `art.py` | Procedural 32-bit pixel-art sprites |
| `settings.py` | Tunables: palette, products, staff, upgrades, balance, port |
| `smoke_test.py` | Headless test that runs the single-player sim for several days |
| `net_test.py` | Headless test that runs a host + client over the loopback |
| `make_share.sh` | Builds a zip of the game to send to friends |
| `build_standalone.sh` | Builds a no-Python-needed standalone app (per OS) |
| `FOR_FRIENDS.md` | Friend-facing "how to join" guide |

Tip: almost everything is tunable in `settings.py` — prices, wages, upgrade
costs, store hours and the colour palette.
