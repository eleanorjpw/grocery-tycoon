# 🛒 Grocery Tycoon — How to join your friend's store

You got sent this folder so you can **join a friend's shop** and run it together.
The game runs on *your* computer and connects to your friend (the "host") over
the network. Here's the whole process.

## 1. Run the game on your computer

You need **Python 3** installed (it's free).

- **macOS:** double-click **`Play Grocery Tycoon.command`**.
  - If macOS says *"unidentified developer"*, right-click it → **Open** → **Open**.
  - If you don't have Python yet, the Mac usually has it; if not, get it from
    <https://www.python.org/downloads/>.
- **Windows:** double-click **`Play Grocery Tycoon.bat`**.
  - If you don't have Python, install it from
    <https://www.python.org/downloads/> and tick **"Add Python to PATH"**.
- **Any system, from a terminal:** `python3 main.py`

The first launch installs the graphics library (pygame) automatically and may
take a minute. After that it's instant.

## 2. Press "Join Multiplayer"

When the title screen appears, click **Join Multiplayer**, type the address your
friend gives you (or click **Paste** if they sent it to you), and click
**Connect**.

## 3. Make sure you can actually reach the host

- **Same WiFi / same house?** Your friend clicks *Host Multiplayer* and reads you
  the `192.168.x.x` address shown in their lobby. Type that in. Done.
- **Different houses / over the internet?** A home computer isn't reachable from
  the internet by default. The easy fix: **both** of you install
  [Tailscale](https://tailscale.com) (free), sign in to the *same* Tailscale
  account or share the network, and then you join using the host's Tailscale IP
  (looks like `100.x.x.x`). It behaves just like being on the same WiFi.

That's it — once connected you'll spawn into the store and can stock shelves,
mop, run registers, and help manage the business.

See `README.md` for the full game guide.
