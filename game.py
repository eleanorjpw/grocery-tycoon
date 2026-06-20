"""
Grocery Tycoon -- engine, simulation, UI, and multiplayer.

You inherit a run-down corner store. Clean it, repair and stock the shelves,
hire staff, and survive the real headaches of the grocery business: spoilage,
shrinkage, power outages, supply delays and health inspectors.

Play solo, or HOST a store and let friends JOIN across devices to run it
together (move around, stock/clean/repair, ring up registers, and co-manage
the books).
"""
import json
import math
import os
import random
import sys
import types
import pygame

try:
    import subprocess          # not available in the browser (WASM) build
except Exception:
    subprocess = None

import art
from settings import (
    TILE, SCALE, GRID_W, GRID_H, PLAYFIELD_W, PLAYFIELD_H, HUD_H,
    VIEW_W, VIEW_H, FPS, OPEN_HOUR, CLOSE_HOUR, SECONDS_PER_HOUR,
    START_MONEY, PAL, PRODUCTS, PRODUCT_BY_KEY, CASE_SIZE, STAFF_TYPES,
    UPGRADES, START_CLEANLINESS, START_REPUTATION,
    UTILITIES_BASE, UTILITIES_FRIDGE, SHELF_CAPACITY, SHELF_PRICE, REPAIR_COST,
)
from world import World, Shelf
from entities import Customer, Staff
from street import Street

try:
    import net                 # legacy direct-IP networking (desktop only)
except Exception:
    net = None

try:
    import relay_net           # room-code multiplayer via the Cloudflare relay
except Exception:
    relay_net = None

try:
    import saves_api           # cloud accounts + saves
except Exception:
    saves_api = None

from settings import RELAY_URL, OPEN_HOUR

# True when running in a browser via pygbag/WASM (no sockets, no subprocess).
IS_WEB = (sys.platform == "emscripten")

_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no ambiguous 0/O/1/I/L


def gen_room_code(seed, n=4):
    """Deterministic-but-varied 4-char room code (avoids Math.random in web)."""
    code = []
    x = int(seed) & 0xFFFFFFFF
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        code.append(_CODE_CHARS[x % len(_CODE_CHARS)])
    return "".join(code)


def C(name):
    return PAL[name]


def money_str(v):
    s = f"${abs(v):,.0f}"
    return f"-{s}" if v < 0 else s


PLAYER_SHIRTS = ["shirt_red", "shirt_blue", "shirt_grn", "purple",
                 "orange", "shirt_ylw"]
SPAWN_TILES = [(9, 11), (8, 11), (10, 11), (7, 11), (11, 11), (6, 11), (12, 11)]

_LAST_IP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".last_ip")


def copy_clip(text):
    """Best-effort copy to the system clipboard (so the host can paste & share)."""
    if subprocess is None:
        return False
    try:
        if sys.platform == "darwin":
            cmd = ["pbcopy"]
        elif sys.platform.startswith("win"):
            cmd = ["clip"]
        else:
            cmd = ["xclip", "-selection", "clipboard"]
        subprocess.run(cmd, input=text.encode(), timeout=2)
        return True
    except Exception:
        return False


def paste_clip():
    if subprocess is None:
        return ""
    try:
        if sys.platform == "darwin":
            cmd = ["pbpaste"]
        else:
            cmd = ["xclip", "-selection", "clipboard", "-o"]
        out = subprocess.run(cmd, capture_output=True, timeout=2)
        return out.stdout.decode().strip()
    except Exception:
        return ""


def load_last_ip():
    try:
        with open(_LAST_IP_FILE) as f:
            return f.read().strip() or "127.0.0.1"
    except OSError:
        return "127.0.0.1"


def save_last_ip(ip):
    try:
        with open(_LAST_IP_FILE, "w") as f:
            f.write(ip.strip())
    except OSError:
        pass


# ----------------------------------------------------------------- Player ----
class Player:
    SPEED = 78.0
    HB = 9          # hitbox size (px), centred in the 16px sprite

    def __init__(self, col, row, pid=0, name="You", color_idx=0):
        self.x = float(col * TILE)
        self.y = float(row * TILE)
        self.facing = "down"
        self.action_timer = 0.0
        self.pid = pid
        self.name = name
        self.color_idx = color_idx
        self.idx = 0          # movement intent (-1/0/1)
        self.idy = 0
        self.scene = "store"  # "store" | "street"

    @property
    def cx(self):
        return self.x + TILE / 2

    @property
    def cy(self):
        return self.y + TILE / 2

    def _blocked(self, world, nx, ny):
        pad = (TILE - self.HB) / 2
        for ox in (pad, TILE - pad - 1):
            for oy in (pad, TILE - pad - 1):
                c = int((nx + ox) // TILE)
                r = int((ny + oy) // TILE)
                if not world.walkable(c, r):
                    return True
        return False

    def update(self, world, dt):
        if self.action_timer > 0:
            self.action_timer -= dt
        dx, dy = float(self.idx), float(self.idy)
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        if dx or dy:
            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            else:
                self.facing = "down" if dy > 0 else "up"
        nx = self.x + dx * self.SPEED * dt
        if not self._blocked(world, nx, self.y):
            self.x = nx
        ny = self.y + dy * self.SPEED * dt
        if not self._blocked(world, self.x, ny):
            self.y = ny
        self.x = max(0, min((GRID_W - 1) * TILE, self.x))
        self.y = max(0, min((GRID_H - 1) * TILE, self.y))

    def front_tile(self):
        d = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        dc, dr = d[self.facing]
        return (int(self.cx // TILE) + dc, int(self.cy // TILE) + dr)

    def tile(self):
        return (int(self.cx // TILE), int(self.cy // TILE))


def _ghost(x, y, facing, offset=(0, 0)):
    return types.SimpleNamespace(x=x, y=y, facing=facing, offset=offset)


# ------------------------------------------------------------------ Game -----
(PHASE_TITLE, PHASE_LOBBY, PHASE_INTRO, PHASE_PLAY,
 PHASE_SUMMARY, PHASE_OVER) = range(6)
_PHASE_NAMES = {PHASE_LOBBY: "lobby", PHASE_PLAY: "play",
                PHASE_SUMMARY: "summary", PHASE_OVER: "over"}
_NAME_PHASE = {v: k for k, v in _PHASE_NAMES.items()}


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Grocery Tycoon")
        # pygame.SCALED renders at the logical size and lets SDL scale it to the
        # display -- essential on macOS Retina, where a plain window otherwise
        # draws into only part of the physical window (the rest stays black).
        if IS_WEB:
            # the browser canvas handles scaling; SCALED/vsync aren't supported
            self.screen = pygame.display.set_mode((VIEW_W, VIEW_H))
        else:
            try:
                self.screen = pygame.display.set_mode(
                    (VIEW_W, VIEW_H), pygame.SCALED, vsync=1)
            except pygame.error:
                try:
                    self.screen = pygame.display.set_mode(
                        (VIEW_W, VIEW_H), pygame.SCALED)
                except pygame.error:
                    self.screen = pygame.display.set_mode((VIEW_W, VIEW_H))
        self.play = pygame.Surface((PLAYFIELD_W, PLAYFIELD_H))
        self.clock = pygame.time.Clock()
        self.font_s = pygame.font.SysFont("menlo,consolas,monospace", 13)
        self.font_m = pygame.font.SysFont("menlo,consolas,monospace", 17)
        self.font_l = pygame.font.SysFont("menlo,consolas,monospace", 26, bold=True)
        self.font_xl = pygame.font.SysFont("menlo,consolas,monospace", 40, bold=True)

        self.sprites = art.build_sprites()
        self.icons = {p[0]: art.product_icon(p[0], PRODUCT_BY_KEY[p[0]]["color"])
                      for p in PRODUCTS}
        from street import SHOPS as _SHOPS
        self.front_sprs = {c: art.storefront(c)
                           for c in {s[4] for s in _SHOPS} | {"ui_gold"}}
        self._shelf_cache = {}
        self._build_people_sprites()

        # networking / mode
        self.mode = "local"        # "local" | "host" | "client"
        self.server = None
        self.client = None
        self.local_pid = 0
        self.title_mode = "main"   # "main" | "join"
        # join input now holds a room code (alnum); drop any legacy IP value
        self.ip_text = "".join(c for c in load_last_ip() if c.isalnum())[:6].upper()
        if self.ip_text.startswith("127"):
            self.ip_text = ""
        self.room_code = ""
        self._net_started = 0
        self._cli_up = False
        self.status_msg = ""
        self._snap_accum = 0.0
        self._last_intent = None

        # cloud accounts + saves
        self.api = saves_api.SaveAPI() if saves_api else None
        self.account = None          # signed-in username
        self.account_pw = ""
        self.current_save = None     # active slot name
        self.save_list = []
        self.req = None              # (handle, kind) of in-flight request
        self.field = "user"          # active text field on the account screen
        self.user_text = ""
        self.pass_text = ""
        self.newname_text = ""
        self.saves_msg = ""

        self.reset_world()
        self.phase = PHASE_TITLE

    # -------------------------------------------------------- setup -------
    def _build_people_sprites(self):
        self.player_sprs = [art.person_set(c, "hair_brn", apron=True)
                            for c in PLAYER_SHIRTS]
        self.cust_spr = []
        combos = [("shirt_blue", "hair_brn"), ("shirt_grn", "black"),
                  ("purple", "hair_brn"), ("orange", "black"),
                  ("cream", "wood_dk"), ("shirt_ylw", "hair_brn")]
        for shirt, hair in combos:
            self.cust_spr.append(art.person_set(shirt, hair, apron=False))
        self.staff_spr = {role: art.person_set(d["color"], "hair_brn", apron=True)
                          for role, d in STAFF_TYPES.items()}

    def reset_world(self):
        """Fresh store + economy. Used by single-player and host."""
        self.world = World()
        self.street = Street()
        self.paused = False
        self.players = {0: Player(*SPAWN_TILES[0], pid=0, name="You", color_idx=0)}
        self.local_pid = 0
        self.customers = []
        self.staff = []
        self.money = START_MONEY
        self.day = 1
        self.game_clock = float(OPEN_HOUR)
        self.reputation = START_REPUTATION
        self.cleanliness = START_CLEANLINESS
        self.upgrades = set()
        self.debt = 0.0
        self.backstock = {p[0]: 24 for p in PRODUCTS}
        self.pending = {p[0]: 0 for p in PRODUCTS}
        self.popups = []
        self.toasts = []
        self.menu_open = False
        self.menu_tab = 0
        self.click_pos = None
        self.mouse_pos = (0, 0)
        self.spawn_timer = 3.0
        self.dirt_timer = 6.0
        self.day_closed = False
        self._reset_daily()
        self.day_revenue = 0.0
        self.day_orders = 0.0
        self.day_shrink = 0.0
        self.day_lost = 0
        self.summary = {}
        self.death_reason = None

    @property
    def me(self):
        return self.players.get(self.local_pid)

    # ----------------------------------------------------- save / restore -
    def to_state(self):
        return {
            "v": 1,
            "money": round(self.money, 2), "day": self.day,
            "clock": round(self.game_clock, 3),
            "rep": round(self.reputation, 2), "clean": round(self.cleanliness, 2),
            "debt": round(self.debt, 2),
            "upgrades": sorted(self.upgrades),
            "backstock": self.backstock, "pending": self.pending,
            "shelves": [{"c": s.col, "r": s.row, "k": s.product,
                         "st": s.stock, "bk": s.broken}
                        for s in self.world.shelves],
            "dirty": [[c, r] for (c, r) in self.world.dirty],
            "shops": [s.id for s in self.street.shops if s.owned],
            "staff": [s.role for s in self.staff],
            "drev": round(self.day_revenue, 2), "dord": round(self.day_orders, 2),
            "dshr": round(self.day_shrink, 2), "dlost": self.day_lost,
        }

    def from_state(self, d):
        self.reset_world()
        self.mode = "local"
        self.money = float(d.get("money", START_MONEY))
        self.day = int(d.get("day", 1))
        self.game_clock = float(d.get("clock", OPEN_HOUR))
        self.reputation = float(d.get("rep", START_REPUTATION))
        self.cleanliness = float(d.get("clean", START_CLEANLINESS))
        self.debt = float(d.get("debt", 0.0))
        self.upgrades = set(d.get("upgrades", []))
        self.backstock = {p[0]: 0 for p in PRODUCTS}
        for k, v in d.get("backstock", {}).items():
            if k in self.backstock:
                self.backstock[k] = int(v)
        self.pending = {p[0]: 0 for p in PRODUCTS}
        for k, v in d.get("pending", {}).items():
            if k in self.pending:
                self.pending[k] = int(v)
        shs = []
        for sd in d.get("shelves", []):
            if sd.get("k") not in PRODUCT_BY_KEY:
                continue
            sh = Shelf(sd["c"], sd["r"], sd["k"])
            sh.stock = int(sd.get("st", 0))
            sh.broken = bool(sd.get("bk", False))
            sh.access = self.world._nearest_walkable_neighbor(sd["c"], sd["r"])
            shs.append(sh)
        if shs:
            self.world.shelves = shs
        self.world.dirty = {(c, r): 1 for c, r in d.get("dirty", [])}
        owned = set(d.get("shops", []))
        for shop in self.street.shops:
            shop.owned = shop.id in owned
        self.staff = []
        for role in d.get("staff", []):
            if role not in STAFF_TYPES:
                continue
            s = Staff(role, 2, 2)
            if role == "cashier":
                free = [ch for ch in self.world.checkouts if ch.cashier is None]
                if free:
                    free[0].cashier = s
                    s.checkout = free[0]
            self.staff.append(s)
        self.day_revenue = float(d.get("drev", 0.0))
        self.day_orders = float(d.get("dord", 0.0))
        self.day_shrink = float(d.get("dshr", 0.0))
        self.day_lost = int(d.get("dlost", 0))
        self.menu_open = self.paused = False
        self.phase = PHASE_PLAY

    def _reset_daily(self):
        self.power_out = False
        self.shoplift_wave = False
        self.spawn_boost = 1.0
        self.cost_mult = 1.0
        self.extra_cost = 0.0
        self.supply_delay = False
        self.event_label = "A calm morning. The store is yours."

    # -------------------------------------------------- callbacks (entities)
    def shoplift_chance(self):
        ch = 0.10
        if any(s.role == "guard" for s in self.staff):
            ch *= 0.4
        if "cameras" in self.upgrades:
            ch *= 0.5
        if self.shoplift_wave:
            ch *= 2.5
        return min(0.5, ch)

    def on_sale(self, cust):
        val = cust.basket_value()
        self.money += val
        self.day_revenue += val
        self.reputation = min(100, self.reputation + 0.15)
        self.popup(cust.w.x, cust.w.y - 4, "coin", money_str(val))
        if random.random() < 0.25:
            self._add_dirt_near(cust.w.col, cust.w.row)

    def on_customer_rage(self, cust):
        self.reputation = max(0, self.reputation - 3)
        self.day_lost += 1
        for key, _ in cust.basket:
            self.backstock[key] = self.backstock.get(key, 0) + 1
        self.toast("A shopper left the line angry!", "ui_bad")

    def on_shoplift(self, cust):
        guard = any(s.role == "guard" for s in self.staff)
        caught_p = (0.55 if guard else 0.0) + (0.3 if "cameras" in self.upgrades else 0.0)
        if random.random() < caught_p:
            for key, _ in cust.basket:
                self.backstock[key] = self.backstock.get(key, 0) + 1
            self.reputation = min(100, self.reputation + 0.5)
            self.popup(cust.w.x, cust.w.y - 4, "spark", "Caught!")
        else:
            self.day_shrink += cust.basket_value()
            self.popup(cust.w.x, cust.w.y - 4, "text", "Shoplifted!", "ui_bad")

    def on_empty_shelf(self):
        self.reputation = max(0, self.reputation - 0.3)

    def popup(self, x, y, kind, text="", color="ui_gold"):
        self.popups.append({"x": x, "y": y, "kind": kind, "text": text,
                            "color": color, "t": 1.1})

    def toast(self, msg, color="ui_text"):
        self.toasts.append({"msg": msg, "color": color, "t": 3.6})

    def _add_dirt_near(self, c, r):
        for _ in range(6):
            cc = c + random.randint(-2, 2)
            rr = r + random.randint(-2, 2)
            if self.world.walkable(cc, rr) and (cc, rr) not in self.world.dirty:
                self.world.dirty[(cc, rr)] = random.randint(1, 2)
                self.cleanliness = max(0, self.cleanliness - 1.2)
                return

    # ----------------------------------------------------- interaction ----
    def interact_local(self):
        """Triggered by the local player's key press."""
        p = self.me
        if p is None:
            return
        # the stockroom crates open the ordering menu (handled locally as UI)
        if p.scene == "store" and p.front_tile() in self.world.crates:
            self.menu_open = True
            self.menu_tab = 0
            self.toast("Stockroom: order more stock here.", "ui_dim")
            return
        if self.mode == "client":
            self.client.send({"t": "act", "a": "interact"})
            return
        self.interact(p)

    def interact(self, player):
        if player.scene == "street":
            self._street_interact(player)
            return
        if player.action_timer > 0:
            return
        ft = player.front_tile()
        pt = player.tile()
        fix = self.world.fixture_at(*ft)
        if isinstance(fix, Shelf):
            if fix.broken:
                if self.money >= REPAIR_COST:
                    self.money -= REPAIR_COST
                    fix.broken = False
                    fix.stock = 0
                    player.action_timer = 0.3
                    self.popup(ft[0]*TILE, ft[1]*TILE, "spark", "Repaired")
                    self.toast(f"Repaired the {fix.category} shelf "
                               f"(-{money_str(REPAIR_COST)})", "ui_good")
                else:
                    self.toast(f"Not enough cash to repair "
                               f"({money_str(REPAIR_COST)}).", "ui_bad")
                return
            self._restock_shelf(fix, player)
            return
        for t in (pt, ft):
            if t in self.world.dirty:
                del self.world.dirty[t]
                self.cleanliness = min(100, self.cleanliness + 2.5)
                player.action_timer = 0.25
                self.popup(t[0]*TILE, t[1]*TILE, "spark", "")
                return
        self.toast("Face a shelf to stock/repair, stand on grime to clean, "
                   "or face a crate to order.", "ui_dim")

    def _street_interact(self, player):
        ft = player.front_tile()
        st = self.street
        if ft == st.store_door:
            player.scene = "store"
            player.x, player.y = 9 * TILE, 11 * TILE
            player.facing, player.idx, player.idy = "up", 0, 0
            if player is self.me:
                self.toast("Back to work!", "ui_dim")
            return
        for shop in st.shops:
            if ft == shop.door:
                if shop.owned:
                    self.toast(f"You already own the {shop.name}.", "ui_dim")
                elif self.money >= shop.price:
                    self.money -= shop.price
                    shop.owned = True
                    self.toast(f"Bought the {shop.name}! "
                               f"+{money_str(shop.income)}/day income.", "ui_good")
                else:
                    self.toast(f"The {shop.name} costs {money_str(shop.price)} "
                               f"-- not enough cash.", "ui_bad")
                return
        self.toast("Walk up to a shop's door and press E to buy it.", "ui_dim")

    def _restock_shelf(self, sh, player):
        avail = self.backstock.get(sh.product, 0)
        room = sh.capacity - sh.stock
        move = min(CASE_SIZE, avail, room)
        name = PRODUCT_BY_KEY[sh.product]["name"]
        if room <= 0:
            self.toast(f"{name} shelf is already full.", "ui_dim")
        elif move <= 0:
            self.toast(f"No {name} in the stockroom. Order more!", "ui_bad")
        else:
            sh.stock += move
            self.backstock[sh.product] -= move
            player.action_timer = 0.3
            self.popup(sh.col*TILE, sh.row*TILE, "spark", f"+{move}")
            self.toast(f"Stocked {move} {name}.", "ui_good")

    # ----------------------------------------- store actions (mode-routed) -
    def order_case(self, key):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "order", "key": key})
            return
        self._apply_order(key)

    def hire(self, role):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "hire", "role": role})
            return
        self._apply_hire(role)

    def fire(self, role):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "fire", "role": role})
            return
        self._apply_fire(role)

    def buy_upgrade(self, uid):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "upgrade", "uid": uid})
            return
        self._apply_upgrade(uid)

    def buy_shelf(self):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "buyshelf"})
            return
        self._apply_buyshelf()

    def take_loan(self):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "loan"})
            return
        self._apply_loan()

    def advance_day(self):
        if self.mode == "client":
            self.client.send({"t": "cmd", "c": "advance"})
            return
        self._start_new_day()

    # --------------------------------------------- store actions (applied) -
    def _apply_order(self, key):
        price = PRODUCT_BY_KEY[key]["wholesale"] * CASE_SIZE * self.cost_mult
        if self.money < price:
            self.toast("Not enough cash for that order.", "ui_bad")
            return
        self.money -= price
        self.day_orders += price
        self.pending[key] += CASE_SIZE
        self.toast(f"Ordered a case of {PRODUCT_BY_KEY[key]['name']} "
                   f"({money_str(price)}). Arrives tomorrow.", "ui_good")

    def _apply_hire(self, role):
        cost = STAFF_TYPES[role]["wage"]
        if self.money < cost:
            self.toast(f"Can't afford the first day's wage ({money_str(cost)}).",
                       "ui_bad")
            return
        s = Staff(role, 2, 2)
        if role == "cashier":
            free = [ch for ch in self.world.checkouts if ch.cashier is None]
            if not free:
                self.toast("Both checkouts already have a cashier.", "ui_bad")
                return
            free[0].cashier = s
            s.checkout = free[0]
        self.staff.append(s)
        self.toast(f"Hired a {STAFF_TYPES[role]['name']}.", "ui_good")

    def _apply_fire(self, role):
        for s in reversed(self.staff):
            if s.role == role:
                self._remove_staff(s)
                self.toast(f"Let go a {STAFF_TYPES[role]['name']}.", "ui_dim")
                return

    def _remove_staff(self, s):
        if s in self.staff:
            self.staff.remove(s)
        if s.checkout is not None and s.checkout.cashier is s:
            s.checkout.cashier = None

    def _apply_upgrade(self, uid):
        spec = next((u for u in UPGRADES if u[0] == uid), None)
        if spec is None or uid in self.upgrades:
            return
        name, cost = spec[1], spec[2]
        if self.money < cost:
            self.toast("Not enough cash for that renovation.", "ui_bad")
            return
        self.money -= cost
        self.upgrades.add(uid)
        self.toast(f"Installed: {name}!", "ui_good")
        if uid == "lights":
            self.reputation = min(100, self.reputation + 6)
        if uid == "signage":
            self.reputation = min(100, self.reputation + 8)
        if uid == "see_world":
            self.toast("Head out the front door to explore the street!",
                       "ui_accent")

    def _apply_buyshelf(self):
        slot = self.world.next_free_slot()
        if slot is None:
            self.toast("No room left for more shelves.", "ui_bad")
            return
        if self.money < SHELF_PRICE:
            self.toast(f"A new shelf costs {money_str(SHELF_PRICE)}.", "ui_bad")
            return
        self.money -= SHELF_PRICE
        have = {s.product for s in self.world.shelves}
        key = next((p[0] for p in PRODUCTS if p[0] not in have), None) \
            or random.choice(PRODUCTS)[0]
        sh = Shelf(slot[0], slot[1], key)
        sh.stock = 0
        sh.access = self.world._nearest_walkable_neighbor(*slot)
        self.world.shelves.append(sh)
        self.toast(f"Built a new {sh.category} shelf "
                   f"({money_str(SHELF_PRICE)}). Stock it up!", "ui_good")

    def _apply_loan(self):
        self.money += 800
        self.debt += 950
        self.toast("Took a $800 loan (repay $950 over time).", "ui_gold")

    def staff_count(self, role):
        return sum(1 for s in self.staff if s.role == role)

    # --------------------------------------------------------- spawning ---
    def _spawn_interval(self):
        rep_factor = 0.5 + self.reputation / 60.0
        hour_mult = 1.0 + 0.6 * math.sin((self.game_clock - 8) / 12 * math.pi)
        iv = 7.0 / max(0.3, rep_factor * hour_mult * self.spawn_boost)
        return max(1.0, min(8.0, iv))

    def _maybe_spawn(self, dt):
        if self.game_clock >= CLOSE_HOUR - 0.2:
            return
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.customers) < 16:
            self.spawn_timer = self._spawn_interval()
            self.customers.append(
                Customer(self.world, random.randrange(len(self.cust_spr))))

    # ------------------------------------------------------- day cycle ----
    def _advance_clock(self, dt):
        self.game_clock += dt / SECONDS_PER_HOUR
        if self.game_clock >= CLOSE_HOUR and not self.day_closed:
            self.day_closed = True
            self._end_day()

    def _end_day(self):
        fridge = "fridge" in self.upgrades
        spoiled = 0
        for sh in self.world.shelves:
            if sh.perishable and sh.stock > 0:
                rate = 0.6 if self.power_out else (0.10 if fridge else 0.40)
                lose = int(sh.stock * rate)
                sh.stock -= lose
                spoiled += lose
        for key in list(self.backstock):
            if PRODUCT_BY_KEY[key]["perishable"] and self.backstock[key] > 0:
                rate = 0.4 if self.power_out else (0.05 if fridge else 0.20)
                lose = int(self.backstock[key] * rate)
                self.backstock[key] -= lose
                spoiled += lose

        wages = sum(STAFF_TYPES[s.role]["wage"] for s in self.staff)
        utilities = UTILITIES_BASE + (UTILITIES_FRIDGE if fridge else 0)
        loan_pay = min(self.debt, 60.0)
        shop_income = sum(s.income for s in self.street.shops if s.owned)
        self.money += shop_income
        self.money -= wages + utilities + self.extra_cost + loan_pay
        self.debt -= loan_pay

        fill = self._avg_fill() * 100
        target = 0.45 * self.cleanliness + 0.55 * fill
        self.reputation += (target - self.reputation) * 0.30
        self.reputation = max(0, min(100, self.reputation))

        quitters = []
        for s in self.staff:
            s.morale -= random.uniform(2, 8)
            if self.reputation < 25:
                s.morale -= 6
            if s.morale < 25 and random.random() < 0.4:
                quitters.append(s)
        for s in quitters:
            self._remove_staff(s)
            self.toast(f"A {STAFF_TYPES[s.role]['name']} quit! Low morale.",
                       "ui_bad")

        self.summary = {
            "revenue": self.day_revenue, "orders": self.day_orders,
            "wages": wages, "utilities": utilities,
            "extra": self.extra_cost, "spoiled": spoiled,
            "shrink": self.day_shrink, "lost": self.day_lost,
            "loan_pay": loan_pay, "shops": shop_income,
            "net": self.day_revenue + shop_income - wages - utilities
                   - self.extra_cost - self.day_orders,
        }
        if self.money < -500:
            self.death_reason = "bankrupt"
            self.phase = PHASE_OVER
        else:
            self.phase = PHASE_SUMMARY

    def _start_new_day(self):
        self.day += 1
        self.game_clock = float(OPEN_HOUR)
        self.day_closed = False
        self.day_revenue = self.day_orders = self.day_shrink = 0.0
        self.day_lost = 0
        self.customers.clear()
        for ch in self.world.checkouts:
            ch.queue.clear()
        self._reset_daily()
        self._roll_morning_event()
        if not self.supply_delay:
            for key in self.pending:
                self.backstock[key] += self.pending[key]
                self.pending[key] = 0
        self.phase = PHASE_PLAY

    def _roll_morning_event(self):
        pool = [
            ("calm", 4, "A calm morning. Doors open at 8."),
            ("rush", 2, "Word spread -- expect a RUSH today!"),
            ("power", 2, "POWER OUTAGE! Lights and fridges are down."),
            ("theft", 2, "Pickpockets reported nearby. Watch for shoplifters."),
            ("supply", 2, "SUPPLY DELAY -- your delivery is stuck on the road."),
            ("breakdown", 2, "A shelf gave out overnight."),
            ("inspect", 2, "The health inspector is visiting today."),
            ("costs", 2, "Energy prices spiked -- costs are up today."),
            ("rival", 1, "A rival store opened down the block."),
        ]
        if self.day <= 2:
            pool = [p for p in pool if p[0] in ("calm", "rush")]
        ev = random.choices([p[0] for p in pool],
                            weights=[p[1] for p in pool])[0]
        self.event_label = next(p[2] for p in pool if p[0] == ev)
        if ev == "rush":
            self.spawn_boost = 1.9
        elif ev == "power":
            self.power_out = True
        elif ev == "theft":
            self.shoplift_wave = True
        elif ev == "supply":
            self.supply_delay = True
            self.cost_mult = 1.25
        elif ev == "breakdown":
            cands = [s for s in self.world.shelves if not s.broken]
            if cands:
                random.choice(cands).broken = True
        elif ev == "inspect":
            if self.cleanliness < 50:
                self.money -= 200
                self.reputation = max(0, self.reputation - 8)
                self.event_label = "FAILED health inspection! Fined $200."
            else:
                self.reputation = min(100, self.reputation + 4)
                self.event_label = "Passed the health inspection. +reputation!"
        elif ev == "costs":
            self.extra_cost += 90
        elif ev == "rival":
            self.reputation = max(0, self.reputation - 5)
            self.spawn_boost = 0.7
        bad = ev in ("power", "theft", "supply", "breakdown", "costs", "rival")
        self.toast("Today: " + self.event_label, "ui_bad" if bad else "ui_good")

    def _total_stock(self):
        return (sum(s.stock for s in self.world.shelves)
                + sum(self.backstock.values())
                + sum(self.pending.values()))

    def _avg_fill(self):
        live = [s for s in self.world.shelves if not s.broken]
        if not live:
            return 0.0
        return sum(s.stock for s in live) / (len(live) * SHELF_CAPACITY)

    # ------------------------------------------------------ checkout proc -
    def _process_checkouts(self, dt):
        pay_time = 1.1
        rate = 0.5 if self.power_out else 1.0
        player_tiles = {p.tile() for p in self.players.values()
                        if p.scene == "store"}
        for ch in self.world.checkouts:
            served = ch.cashier is not None and ch.cashier.at_station
            if ch.staff_tile in player_tiles:
                served = True
            if served and ch.queue:
                front = ch.queue[0]
                if front.state == "queue":
                    front.pay_progress += dt * rate
                    if front.pay_progress >= pay_time:
                        front.complete_sale(self)

    # ----------------------------------------------------------- update ---
    def _set_local_intent(self):
        p = self.me
        if p is None:
            return
        if self.menu_open:
            p.idx = p.idy = 0
            return
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        p.idx, p.idy = dx, dy

    def _scene_map(self, scene):
        return self.street if scene == "street" else self.world

    def _check_transition(self, p):
        if p.scene == "store":
            if "see_world" in self.upgrades and \
                    p.tile() in ((9, GRID_H - 1), (10, GRID_H - 1)):
                p.scene = "street"
                ex = self.street.entrance
                p.x, p.y = ex[0] * TILE, ex[1] * TILE
                p.facing, p.idx, p.idy = "up", 0, 0
                if p is self.me:
                    self.toast("You step out onto the street. Find shops to buy!",
                               "ui_good")

    def update(self, dt):
        if self.mode == "client" or self.phase != PHASE_PLAY:
            return
        if self.paused:
            return
        if self.menu_open and self.mode == "local":
            return     # single-player also pauses while the menu is open
        self._set_local_intent()
        for p in self.players.values():
            p.update(self._scene_map(p.scene), dt)
            self._check_transition(p)
        self._advance_clock(dt)
        if self.phase != PHASE_PLAY:
            return
        self._maybe_spawn(dt)
        for cust in self.customers:
            cust.update(self, dt)
        self.customers = [c for c in self.customers if not c.done]
        for s in self.staff:
            s.update(self, dt)
        self._process_checkouts(dt)

        # the store dies if there is nothing left to sell anywhere
        if self._total_stock() <= 0:
            self.death_reason = "out_of_stock"
            self.phase = PHASE_OVER
            return

        self.dirt_timer -= dt
        if self.dirt_timer <= 0:
            self.dirt_timer = (4.0 if "floor" not in self.upgrades else 8.0) \
                + random.uniform(0, 3)
            if len(self.world.dirty) < 40 and self.customers:
                self._add_dirt_near(random.choice(self.customers).w.col,
                                    random.choice(self.customers).w.row)
        for p in self.popups:
            p["t"] -= dt
            p["y"] -= dt * 14
        self.popups = [p for p in self.popups if p["t"] > 0]
        for t in self.toasts:
            t["t"] -= dt
        self.toasts = [t for t in self.toasts if t["t"] > 0]

    # ------------------------------------------------------- networking ---
    def _relay_ready(self):
        if relay_net is None or "REPLACE_ME" in RELAY_URL:
            self.status_msg = "Multiplayer relay isn't set up yet."
            return False
        return True

    def start_host(self):
        if not self._relay_ready():
            return
        self.reset_world()
        self.mode = "host"
        self.room_code = gen_room_code(pygame.time.get_ticks() ^ id(self))
        self.server = relay_net.RelayServer(self.room_code, name="Host")
        self._net_started = pygame.time.get_ticks()
        self._cli_up = False
        self.status_msg = "Room created -- share the code below."
        self.phase = PHASE_LOBBY

    def start_join(self, code):
        code = "".join(c for c in code.upper() if c.isalnum())[:6]
        if not code:
            self.status_msg = "Enter the room code first."
            return
        if not self._relay_ready():
            return
        self.reset_world()       # static geometry + caches; sim comes from host
        self.mode = "client"
        self.room_code = code
        self.client = relay_net.RelayClient(code, name="Player")
        self._net_started = pygame.time.get_ticks()
        self._cli_up = False
        self.status_msg = f"Joining room {code}..."
        self.phase = PHASE_LOBBY
        save_last_ip(code)

    def start_single(self):
        self.reset_world()
        self.mode = "local"
        self.phase = PHASE_INTRO

    def leave_to_title(self):
        self._teardown_net()
        self.mode = "local"
        self.reset_world()
        self.phase = PHASE_TITLE
        self.title_mode = "main"

    def _teardown_net(self):
        if self.server:
            self.server.close()
            self.server = None
        if self.client:
            self.client.close()
            self.client = None

    def _spawn_remote_player(self, cid):
        idx = len(self.players)
        tile = SPAWN_TILES[idx % len(SPAWN_TILES)]
        self.players[cid] = Player(*tile, pid=cid, name=f"Player{cid}",
                                   color_idx=cid % len(self.player_sprs))

    def _host_handle(self, cid, msg):
        t = msg.get("t")
        if t == "_connect":
            self._spawn_remote_player(cid)
            self.server.send_to(cid, {"t": "welcome", "pid": cid})
            self.toast("A friend connected!", "ui_good")
        elif t == "_disconnect":
            self.players.pop(cid, None)
            self.toast("A friend left.", "ui_dim")
        elif t == "hello":
            if cid in self.players:
                self.players[cid].name = str(msg.get("name", f"Player{cid}"))[:14]
        elif t == "input":
            p = self.players.get(cid)
            if p:
                p.idx = max(-1, min(1, int(msg.get("dx", 0))))
                p.idy = max(-1, min(1, int(msg.get("dy", 0))))
        elif t == "act":
            p = self.players.get(cid)
            if p and self.phase == PHASE_PLAY:
                self.interact(p)
        elif t == "cmd":
            self._host_handle_cmd(msg)

    def _host_handle_cmd(self, msg):
        c = msg.get("c")
        if c == "order":
            self._apply_order(msg.get("key"))
        elif c == "hire":
            self._apply_hire(msg.get("role"))
        elif c == "fire":
            self._apply_fire(msg.get("role"))
        elif c == "upgrade":
            self._apply_upgrade(msg.get("uid"))
        elif c == "buyshelf":
            self._apply_buyshelf()
        elif c == "loan":
            self._apply_loan()
        elif c == "advance" and self.phase == PHASE_SUMMARY:
            self._start_new_day()

    def _snapshot(self):
        return {
            "t": "snap", "phase": _PHASE_NAMES.get(self.phase, "play"),
            "money": round(self.money, 1), "day": self.day,
            "clock": round(self.game_clock, 3),
            "rep": round(self.reputation, 1), "clean": round(self.cleanliness, 1),
            "power": self.power_out, "event": self.event_label,
            "upg": list(self.upgrades),
            "back": self.backstock, "pend": self.pending,
            "drev": round(self.day_revenue, 1), "dord": round(self.day_orders, 1),
            "dshr": round(self.day_shrink, 1), "dlost": self.day_lost,
            "debt": round(self.debt, 1), "death": self.death_reason,
            "paused": self.paused,
            "shops": [s.id for s in self.street.shops if s.owned],
            "players": [{"id": p.pid, "x": round(p.x, 1), "y": round(p.y, 1),
                         "f": p.facing, "c": p.color_idx, "n": p.name,
                         "sc": p.scene}
                        for p in self.players.values()],
            "cust": [{"x": round(c.w.x, 1), "y": round(c.w.y, 1),
                      "f": c.w.facing, "s": c.skin_idx,
                      "ox": c.w.offset[0], "oy": c.w.offset[1]}
                     for c in self.customers],
            "staff": [{"x": round(s.w.x, 1), "y": round(s.w.y, 1),
                       "f": s.w.facing, "r": s.role} for s in self.staff],
            "shelves": [{"c": sh.col, "r": sh.row, "k": sh.product,
                         "st": sh.stock, "bk": sh.broken}
                        for sh in self.world.shelves],
            "dirty": [[c, r] for (c, r) in self.world.dirty],
            "toasts": [{"m": t["msg"], "c": t["color"]} for t in self.toasts[-4:]],
            "summary": self.summary if self.phase == PHASE_SUMMARY else None,
        }

    def _apply_snapshot(self, m):
        self.phase = _NAME_PHASE.get(m["phase"], PHASE_PLAY)
        self.money = m["money"]
        self.day = m["day"]
        self.game_clock = m["clock"]
        self.reputation = m["rep"]
        self.cleanliness = m["clean"]
        self.power_out = m["power"]
        self.event_label = m["event"]
        self.upgrades = set(m["upg"])
        self.backstock = m["back"]
        self.pending = m["pend"]
        self.day_revenue = m["drev"]
        self.day_orders = m["dord"]
        self.day_shrink = m["dshr"]
        self.day_lost = m["dlost"]
        self.debt = m["debt"]
        self.death_reason = m.get("death")
        self.paused = m.get("paused", False)
        owned = set(m.get("shops", []))
        for shop in self.street.shops:
            shop.owned = shop.id in owned
        newpl = {}
        for pd in m["players"]:
            p = self.players.get(pd["id"]) or Player(0, 0, pid=pd["id"])
            p.x, p.y, p.facing = pd["x"], pd["y"], pd["f"]
            p.color_idx, p.name, p.pid = pd["c"], pd["n"], pd["id"]
            p.scene = pd.get("sc", "store")
            newpl[pd["id"]] = p
        self.players = newpl
        self.customers = [types.SimpleNamespace(
            skin_idx=c["s"], w=_ghost(c["x"], c["y"], c["f"], (c["ox"], c["oy"])))
            for c in m["cust"]]
        self.staff = [types.SimpleNamespace(
            role=s["r"], w=_ghost(s["x"], s["y"], s["f"])) for s in m["staff"]]
        shs = []
        for sd in m["shelves"]:
            sh = Shelf(sd["c"], sd["r"], sd["k"])
            sh.stock, sh.broken = sd["st"], sd["bk"]
            shs.append(sh)
        self.world.shelves = shs
        self.world.dirty = {(c, r): 1 for c, r in m["dirty"]}
        self.toasts = [{"msg": t["m"], "color": t["c"], "t": 1.0}
                       for t in m["toasts"]]
        if m.get("summary"):
            self.summary = m["summary"]

    # ------------------------------------------------------ cloud saves --
    def _creds(self):
        return {"username": self.account or self.user_text,
                "password": self.account_pw or self.pass_text}

    def _begin(self, kind, path, payload):
        if not self.api or self.req:
            return
        self.req = (self.api.request(path, payload), kind)

    def _refresh_saves(self):
        self._begin("list", "/list", self._creds())

    def _poll_request(self):
        if not self.req:
            return
        handle, kind = self.req
        r = self.api.poll(handle)
        if r is None:
            return
        self.req = None
        self._on_response(kind, r)

    def _on_response(self, kind, r):
        if r[0] == "err":
            self.saves_msg = r[1]
            return
        obj = r[1] if isinstance(r[1], dict) else {}
        if obj.get("error"):
            self.saves_msg = obj["error"]
            return
        if kind in ("login", "register"):
            self.account = obj.get("username", self.user_text)
            self.account_pw = self.pass_text
            self.pass_text = ""
            self.saves_msg = f"Signed in as {self.account}."
            self.title_mode = "saves"
            self._refresh_saves()
        elif kind == "list":
            self.save_list = obj.get("saves", [])
        elif kind == "save":
            self.saves_msg = "Saved!"
            self.toast("Game saved to your account.", "ui_good")
        elif kind == "load":
            try:
                self.from_state(json.loads(obj.get("data", "{}")))
                self.current_save = obj.get("name")
                self.toast(f"Loaded '{self.current_save}'.", "ui_good")
            except Exception:
                self.saves_msg = "That save looks corrupted."
        elif kind == "delete":
            self.saves_msg = "Save deleted."
            self._refresh_saves()

    def cloud_save(self):
        if not self.account:
            self.toast("Sign in from the title screen to save.", "ui_bad")
            return
        if not self.current_save:
            self.current_save = "My Store"
        self._begin("save", "/save",
                    {**self._creds(), "name": self.current_save,
                     "data": json.dumps(self.to_state())})
        self.toast("Saving...", "ui_dim")

    def _net_tick(self, dt):
        if self.mode == "host" and self.server:
            if getattr(self.server, "error", None):
                self.toast("Room code is already in use -- try again."
                           if self.server.error == "room_taken"
                           else "Relay error.", "ui_bad")
                self.leave_to_title()
                return
            for cid, msg in self.server.poll():
                self._host_handle(cid, msg)
            self._snap_accum += dt
            if self._snap_accum >= 0.05:      # ~20 Hz
                self._snap_accum = 0.0
                self.server.broadcast(self._snapshot())
            if self.server.connected:
                self._cli_up = True
                if self.status_msg.startswith("Room created"):
                    self.status_msg = "Room is live -- share the code."
            elif self._cli_up:
                self.toast("Lost the relay connection.", "ui_bad")
                self.leave_to_title()
            elif pygame.time.get_ticks() - self._net_started > 9000:
                self.status_msg = "Couldn't reach the relay (check internet)."
        elif self.mode == "client" and self.client:
            if self.phase == PHASE_PLAY and not self.menu_open:
                keys = pygame.key.get_pressed()
                dx = dy = 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    dx -= 1
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    dx += 1
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    dy -= 1
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    dy += 1
            else:
                dx = dy = 0
            if (dx, dy) != self._last_intent:
                self.client.send({"t": "input", "dx": dx, "dy": dy})
                self._last_intent = (dx, dy)
            for msg in self.client.poll():
                t = msg.get("t")
                if t == "welcome":
                    self.local_pid = msg.get("pid", 0)
                    self.status_msg = "Connected!"
                elif t == "snap":
                    self._apply_snapshot(msg)
            if self.client.lost:
                self.toast("The host closed the room.", "ui_bad")
                self.leave_to_title()
            elif self.client.connected:
                if not self._cli_up:
                    self.client.send({"t": "hello", "name": "Player"})
                self._cli_up = True
            elif self._cli_up:
                self.toast("Lost connection to host.", "ui_bad")
                self.leave_to_title()
            elif pygame.time.get_ticks() - self._net_started > 12000:
                self.toast("Couldn't reach that room -- check the code.", "ui_bad")
                self.leave_to_title()

    # ----------------------------------------------------------- render ---
    def _shelf_sprite(self, sh):
        is_fridge = sh.perishable and "fridge" in self.upgrades
        key = (sh.color, sh.level(), sh.broken, is_fridge)
        if key not in self._shelf_cache:
            if sh.broken:
                surf = art.shelf(sh.color, 0, broken=True)
            elif is_fridge:
                surf = art.fridge(sh.color, sh.level())
            else:
                surf = art.shelf(sh.color, sh.level())
            self._shelf_cache[key] = surf
        return self._shelf_cache[key]

    def _floor_sprite(self, c, r):
        if "floor" in self.upgrades:
            return self.sprites["floor_new"]
        if (c, r) in self.world.cracks:
            return self.sprites["floor_crack"]
        return self.sprites["floor"]

    def _crate_sprite(self):
        total = sum(self.backstock.values())
        lvl = 0 if total <= 0 else (1 if total < 60 else (2 if total < 160 else 3))
        return self.sprites[f"crate{lvl}"]

    def _draw_world(self):
        s = self.play
        w = self.world
        s.fill(C("black"))
        for r in range(GRID_H):
            for c in range(GRID_W):
                t = w.grid[r][c]
                if t == "wall":
                    s.blit(self.sprites["wall"], (c*TILE, r*TILE))
                elif t == "door":
                    s.blit(self.sprites["door"], (c*TILE, r*TILE))
                else:
                    s.blit(self._floor_sprite(c, r), (c*TILE, r*TILE))
        for (c, r) in w.dirty:
            s.blit(self.sprites["dirt"], (c*TILE, r*TILE))
        crate = self._crate_sprite()
        for (c, r) in w.crates:
            s.blit(crate, (c*TILE, r*TILE))
        for (c, r) in w.plants:
            s.blit(self.sprites["plant"], (c*TILE, r*TILE))

        draws = []
        for sh in w.shelves:
            draws.append((sh.row*TILE + 15, self._shelf_sprite(sh),
                          sh.col*TILE, sh.row*TILE))
        for ch in w.checkouts:
            draws.append((ch.row*TILE + 14, self.sprites["counter"],
                          ch.col*TILE, ch.row*TILE))
            draws.append((ch.row*TILE + 15, self.sprites["register"],
                          ch.col*TILE, ch.row*TILE))
        for cust in self.customers:
            spr = self.cust_spr[cust.skin_idx][cust.w.facing]
            ox, oy = cust.w.offset
            draws.append((cust.w.y + 15 + oy, spr, cust.w.x + ox, cust.w.y + oy))
        for st in self.staff:
            draws.append((st.w.y + 15, self.staff_spr[st.role][st.w.facing],
                          st.w.x, st.w.y))
        for p in self.players.values():
            if p.scene != "store":
                continue
            spr = self.player_sprs[p.color_idx % len(self.player_sprs)][p.facing]
            draws.append((p.y + 15, spr, p.x, p.y))
        draws.sort(key=lambda d: d[0])
        for _, surf, x, y in draws:
            s.blit(surf, (int(x), int(y)))

        # product icons floating above each (working) shelf
        for sh in w.shelves:
            if sh.broken:
                continue
            ic = self.icons.get(sh.product)
            if ic:
                s.blit(ic, (sh.col * TILE, sh.row * TILE - 7))

        for p in self.popups:
            if p["kind"] == "coin":
                s.blit(self.sprites["coin"], (int(p["x"]), int(p["y"])))
            elif p["kind"] == "spark":
                s.blit(self.sprites["sparkle"], (int(p["x"]), int(p["y"])))

        dim = 150 if self.power_out else (80 if "lights" not in self.upgrades else 0)
        if dim:
            ov = pygame.Surface((PLAYFIELD_W, PLAYFIELD_H))
            ov.fill((10, 8, 24))
            ov.set_alpha(dim)
            s.blit(ov, (0, 0))

    def _draw_world_scaled(self):
        self._draw_world()
        self.screen.blit(
            pygame.transform.scale(self.play, (VIEW_W, PLAYFIELD_H * SCALE)),
            (0, 0))

    def _local_scene(self):
        return self.me.scene if self.me else "store"

    def _draw_playfield_scaled(self):
        """Draw whichever scene the local player is in."""
        if self._local_scene() == "street":
            self._draw_street()
        else:
            self._draw_world()
        self.screen.blit(
            pygame.transform.scale(self.play, (VIEW_W, PLAYFIELD_H * SCALE)),
            (0, 0))

    def _draw_street(self):
        s = self.play
        st = self.street
        s.fill(C("black"))
        shop_cols = {sh.col: sh for sh in st.shops}
        for r in range(GRID_H):
            for c in range(GRID_W):
                t = st.grid[r][c]
                xy = (c * TILE, r * TILE)
                if t == "wall":
                    # storefront band sits on the row just above the doors
                    if r == 3 and c in shop_cols:
                        s.blit(self.front_sprs.get(shop_cols[c].color,
                               self.sprites["storefront"]), xy)
                    elif r == 3 and c == st.store_col:
                        s.blit(self.front_sprs["ui_gold"], xy)
                    else:
                        s.blit(self.sprites["storefront" if r >= 2
                               else "wall"], xy)
                elif t == "door":
                    s.blit(self.sprites["door"], xy)
                elif t == "road":
                    dash = (c % 4 == 1 and r == 10)
                    s.blit(self.sprites["road_dash" if dash else "road"], xy)
                else:
                    s.blit(self.sprites["sidewalk"], xy)
        # players on the street, y-sorted
        ppl = [p for p in self.players.values() if p.scene == "street"]
        for p in sorted(ppl, key=lambda q: q.y):
            spr = self.player_sprs[p.color_idx % len(self.player_sprs)][p.facing]
            s.blit(spr, (int(p.x), int(p.y)))

    def _draw_street_signs(self):
        """Shop names + prices, drawn in screen space over the storefronts."""
        st = self.street
        for shop in st.shops:
            x = int((shop.col * TILE + TILE / 2) * SCALE)
            y = int((2 * TILE) * SCALE)
            self._sign(x, y, shop.name,
                       "OWNED" if shop.owned else money_str(shop.price),
                       "ui_good" if shop.owned else "ui_gold")
        x = int((st.store_col * TILE + TILE / 2) * SCALE)
        self._sign(x, int((2 * TILE) * SCALE), "YOUR STORE", "press E", "white")

    def _sign(self, cx, cy, line1, line2, c2):
        a = self.font_s.render(line1, True, C("white"))
        b = self.font_s.render(line2, True, C(c2))
        w = max(a.get_width(), b.get_width()) + 10
        bg = pygame.Surface((w, 34), pygame.SRCALPHA)
        bg.fill((20, 16, 28, 200))
        pygame.draw.rect(bg, C("ui_border"), bg.get_rect(), 1)
        self.screen.blit(bg, (cx - w // 2, cy - 36))
        self.screen.blit(a, (cx - a.get_width() // 2, cy - 33))
        self.screen.blit(b, (cx - b.get_width() // 2, cy - 18))

    def _draw_nametags(self):
        if self.mode == "local":
            return
        scene = self._local_scene()
        for p in self.players.values():
            if p.scene != scene:
                continue
            x = int((p.x + TILE / 2) * SCALE)
            y = int((p.y - 6) * SCALE)
            tag = p.name + (" (you)" if p.pid == self.local_pid else "")
            img = self.font_s.render(tag, True, C("white"))
            r = img.get_rect(midbottom=(x, y))
            bg = pygame.Surface((r.w + 6, r.h + 2), pygame.SRCALPHA)
            bg.fill((20, 16, 28, 150))
            self.screen.blit(bg, (r.x - 3, r.y - 1))
            self.screen.blit(img, r)

    def _text(self, surf, font, txt, x, y, color="ui_text", center=False,
              right=False):
        img = font.render(txt, True, C(color) if isinstance(color, str) else color)
        rect = img.get_rect()
        if center:
            rect.midtop = (x, y)
        elif right:
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        surf.blit(img, rect)
        return rect

    def _draw_hud(self):
        sc = self.screen
        top = PLAYFIELD_H * SCALE
        pygame.draw.rect(sc, C("ui_panel"), (0, top, VIEW_W, HUD_H * SCALE))
        pygame.draw.rect(sc, C("ui_border"), (0, top, VIEW_W, 3))
        y = top + 10
        self._text(sc, self.font_l, money_str(self.money), 16, y,
                   "ui_gold" if self.money >= 0 else "ui_bad")
        hh = int(self.game_clock)
        mm = int((self.game_clock - hh) * 60)
        ampm = "AM" if hh < 12 else "PM"
        h12 = hh if 1 <= hh <= 12 else (abs(hh - 12) or 12)
        self._text(sc, self.font_m, f"Day {self.day}", 230, y + 2, "ui_text")
        self._text(sc, self.font_m, f"{h12:02d}:{mm:02d} {ampm}", 230, y + 24,
                   "ui_accent")
        self._bar(sc, 360, y + 2, "Reputation", self.reputation, "ui_good")
        self._bar(sc, 360, y + 26, "Cleanliness", self.cleanliness, "glass")
        sx = 640
        roles = " ".join(f"{STAFF_TYPES[r]['name'][:4]}:{self.staff_count(r)}"
                         for r in STAFF_TYPES)
        self._text(sc, self.font_s, roles, sx, y, "ui_dim")
        self._text(sc, self.font_s,
                   f"Stockroom units: {sum(self.backstock.values())}",
                   sx, y + 18, "ui_dim")
        self._text(sc, self.font_s, "[TAB] Manage  [SPACE/E] Interact  "
                   "[WASD] Move", sx, y + 36, "ui_dim")
        if self.power_out:
            self._text(sc, self.font_m, "POWER OUT", VIEW_W - 16, y + 24,
                       "ui_bad", right=True)
        elif self.mode != "local":
            self._text(sc, self.font_m,
                       f"{'HOST' if self.mode == 'host' else 'CO-OP'}: "
                       f"{len(self.players)}P", VIEW_W - 16, y + 24,
                       "ui_accent", right=True)
        # pause button (host/single-player only; co-op clients can't pause)
        if self.mode != "client" and not self.menu_open:
            if self._button((VIEW_W - 128, top + 6, 110, 26),
                            "Resume [P]" if self.paused else "Pause [P]",
                            "ui_gold" if self.paused else "ui_panel2",
                            text_color="black" if self.paused else "ui_text"):
                self.paused = not self.paused

    def _draw_pause_overlay(self):
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 150))
        sc.blit(shade, (0, 0))
        self._text(sc, self.font_xl, "PAUSED", VIEW_W // 2, VIEW_H // 2 - 70,
                   "ui_gold", center=True)
        if self.mode == "client":
            self._text(sc, self.font_m, "The host paused the game.",
                       VIEW_W // 2, VIEW_H // 2 - 14, "ui_text", center=True)
        else:
            self._text(sc, self.font_m, "The store is frozen.", VIEW_W // 2,
                       VIEW_H // 2 - 14, "ui_text", center=True)
            if self._button((VIEW_W // 2 - 110, VIEW_H // 2 + 24, 220, 44),
                            "Resume", "ui_good", text_color="black"):
                self.paused = False
            if self.mode == "local":
                if self.account:
                    slot = self.current_save or "My Store"
                    if self._button((VIEW_W // 2 - 110, VIEW_H // 2 + 76, 220, 44),
                                    f"Save to '{slot}'", "ui_gold",
                                    text_color="black"):
                        self.cloud_save()
                else:
                    self._text(sc, self.font_s,
                               "Sign in on the title screen to save to the cloud.",
                               VIEW_W // 2, VIEW_H // 2 + 86, "ui_dim",
                               center=True)

    def _bar(self, sc, x, y, label, val, color):
        self._text(sc, self.font_s, label, x, y, "ui_dim")
        bx, by, bw, bh = x + 96, y + 2, 150, 12
        pygame.draw.rect(sc, C("ui_panel2"), (bx, by, bw, bh))
        pygame.draw.rect(sc, C(color), (bx, by, int(bw * val / 100), bh))
        pygame.draw.rect(sc, C("ui_border"), (bx, by, bw, bh), 1)

    def _draw_toasts(self):
        sc = self.screen
        for i, t in enumerate(self.toasts[-4:]):
            a = min(1.0, t["t"] / 0.6)
            y = 12 + i * 26
            img = self.font_m.render(t["msg"], True, C(t["color"]))
            img.set_alpha(int(255 * a))
            bg = pygame.Surface((img.get_width() + 16, 24), pygame.SRCALPHA)
            bg.fill((20, 16, 28, int(170 * a)))
            sc.blit(bg, (VIEW_W // 2 - img.get_width() // 2 - 8, y - 3))
            sc.blit(img, (VIEW_W // 2 - img.get_width() // 2, y))
        for p in self.popups:
            if p["kind"] in ("coin", "text") and p["text"]:
                self._text(sc, self.font_s, p["text"], int(p["x"] * SCALE),
                           int(p["y"] * SCALE), p.get("color", "ui_gold"))

    # -------------------------------------------------------- buttons -----
    def _button(self, rect, label, color="ui_panel2", enabled=True,
                text_color="ui_text"):
        sc = self.screen
        hover = pygame.Rect(rect).collidepoint(self.mouse_pos)
        base = color if enabled else "dark"
        pygame.draw.rect(sc, C("ui_accent") if (hover and enabled) else C(base),
                         rect)
        pygame.draw.rect(sc, C("ui_border"), rect, 2)
        self._text(sc, self.font_m, label, rect[0] + rect[2] // 2,
                   rect[1] + rect[3] // 2 - 9,
                   "black" if (hover and enabled) else
                   (text_color if enabled else "ui_dim"), center=True)
        return (enabled and self.click_pos is not None
                and pygame.Rect(rect).collidepoint(self.click_pos))

    def _panel(self, rect, title=None):
        sc = self.screen
        x, y, w, h = rect
        pygame.draw.rect(sc, C("ui_panel"), rect)
        pygame.draw.rect(sc, C("ui_border"), rect, 3)
        if title:
            pygame.draw.rect(sc, C("ui_panel2"), (x, y, w, 38))
            self._text(sc, self.font_l, title, x + w // 2, y + 6, "ui_gold",
                       center=True)

    # ---------------------------------------------------- management menu --
    def _draw_menu(self):
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 180))
        sc.blit(shade, (0, 0))
        m = pygame.Rect(60, 40, VIEW_W - 120, VIEW_H - 110)
        self._panel(m, "STORE MANAGEMENT")
        tabs = ["Order Stock", "Staff", "Renovations", "Finances"]
        tw = (m.width - 40) // len(tabs)
        for i, name in enumerate(tabs):
            r = (m.x + 20 + i * tw, m.y + 46, tw - 8, 32)
            sel = i == self.menu_tab
            if self._button(r, name, "ui_gold" if sel else "ui_panel2",
                            text_color="black" if sel else "ui_text"):
                self.menu_tab = i
        body = pygame.Rect(m.x + 20, m.y + 88, m.width - 40, m.height - 150)
        [self._tab_order, self._tab_staff, self._tab_upgrades,
         self._tab_finance][self.menu_tab](body)
        self._text(sc, self.font_s, "Cash: " + money_str(self.money),
                   m.x + 24, m.bottom - 30, "ui_gold")
        if self.mode != "local":
            self._text(sc, self.font_s,
                       "Co-op: the game keeps running while this is open.",
                       m.x + 200, m.bottom - 30, "ui_dim")
        if self._button((m.right - 200, m.bottom - 38, 180, 30), "Close  [TAB]"):
            self.menu_open = False

    def _tab_order(self, body):
        sc = self.screen
        shelf_totals = {p[0]: sum(s.stock for s in self.world.shelves
                                  if s.product == p[0] and not s.broken)
                        for p in PRODUCTS}
        n_out = sum(1 for v in shelf_totals.values() if v == 0)
        head = ("Order cases of 12 -- deliveries arrive next morning. "
                "*cold* items spoil without a fridge.")
        if n_out:
            head = f"!! {n_out} product(s) OUT on the shelves !!   " + head
        self._text(sc, self.font_s, head, body.x, body.y,
                   "ui_bad" if n_out else "ui_dim")
        cols = 2
        rows = (len(PRODUCTS) + 1) // cols
        cw = body.width // cols
        for idx, p in enumerate(PRODUCTS):
            key = p[0]
            col, row = idx // rows, idx % rows
            x = body.x + col * cw
            y = body.y + 28 + row * 40
            info = PRODUCT_BY_KEY[key]
            shelf_total = shelf_totals[key]
            back = self.backstock.get(key, 0)
            inbound = self.pending.get(key, 0)
            out = shelf_total == 0
            low = 0 < shelf_total < 8
            # coloured status dot + name so out-of-stock items jump out
            dot_col = "ui_bad" if out else ("ui_gold" if low else "ui_good")
            pygame.draw.circle(sc, C(dot_col), (x + 4, y + 7), 4)
            name_col = "ui_bad" if out else ("ui_gold" if low else "ui_text")
            status = "  OUT!" if out else ("  low" if low else "")
            tag = " *cold*" if info["perishable"] else ""
            self._text(sc, self.font_s, f"{info['name']}{tag}{status}",
                       x + 14, y, name_col)
            self._text(sc, self.font_s,
                       f"shelf {shelf_total}  back {back}  inbound {inbound}",
                       x + 14, y + 15, "ui_bad" if (out and back == 0 and
                       inbound == 0) else "ui_dim")
            price = info["wholesale"] * CASE_SIZE * self.cost_mult
            if self._button((x + cw - 150, y, 130, 30),
                            f"+12  {money_str(price)}"):
                self.order_case(key)

    def _tab_staff(self, body):
        sc = self.screen
        self._text(sc, self.font_s,
                   "Wages are paid nightly. Low-morale staff may quit (grocery "
                   "turnover is brutal).", body.x, body.y, "ui_dim")
        y = body.y + 30
        for role, d in STAFF_TYPES.items():
            self._text(sc, self.font_m,
                       f"{d['name']}  (x{self.staff_count(role)})", body.x, y,
                       "ui_text")
            self._text(sc, self.font_s,
                       f"{d['desc']}  Wage {money_str(d['wage'])}/day",
                       body.x, y + 22, "ui_dim")
            if self._button((body.right - 320, y, 140, 34), "Hire", "ui_good",
                            text_color="black"):
                self.hire(role)
            if self._button((body.right - 165, y, 140, 34), "Fire", "ui_panel2",
                            enabled=self.staff_count(role) > 0):
                self.fire(role)
            y += 60
        total = sum(STAFF_TYPES[s.role]["wage"] for s in self.staff)
        self._text(sc, self.font_m, f"Total daily wages: {money_str(total)}",
                   body.x, y + 4, "ui_accent")

    def _tab_upgrades(self, body):
        sc = self.screen
        self._text(sc, self.font_s,
                   "One-time renovations -- plus buy extra shelves to grow.",
                   body.x, body.y, "ui_dim")
        y = body.y + 28
        for uid, name, cost, desc in UPGRADES:
            owned = uid in self.upgrades
            self._text(sc, self.font_m, name, body.x, y,
                       "ui_good" if owned else "ui_text")
            self._text(sc, self.font_s, desc, body.x, y + 22, "ui_dim")
            if owned:
                self._text(sc, self.font_m, "INSTALLED", body.right - 150, y + 6,
                           "ui_good")
            elif self._button((body.right - 190, y, 165, 34),
                              f"Buy {money_str(cost)}", enabled=self.money >= cost):
                self.buy_upgrade(uid)
            y += 50
        # buy extra shelf
        slots = sum(1 for s in self.world.expansion_slots
                    if self.world.fixture_at(*s) is None)
        self._text(sc, self.font_m, "Extra Shelf", body.x, y,
                   "ui_text" if slots else "ui_dim")
        self._text(sc, self.font_s,
                   f"Add a new shelf along the back wall. {slots} space(s) left.",
                   body.x, y + 22, "ui_dim")
        if self._button((body.right - 190, y, 165, 34),
                        f"Build {money_str(SHELF_PRICE)}",
                        enabled=slots > 0 and self.money >= SHELF_PRICE):
            self.buy_shelf()

    def _tab_finance(self, body):
        sc = self.screen
        fridge = "fridge" in self.upgrades
        util = UTILITIES_BASE + (UTILITIES_FRIDGE if fridge else 0)
        wages = sum(STAFF_TYPES[s.role]["wage"] for s in self.staff)
        lines = [
            ("Cash on hand", money_str(self.money), "ui_gold"),
            ("Outstanding loan", money_str(self.debt),
             "ui_bad" if self.debt else "ui_dim"),
            ("", "", "ui_dim"),
            ("Today's revenue", money_str(self.day_revenue), "ui_good"),
            ("Today's restock orders", money_str(self.day_orders), "ui_text"),
            ("Shrinkage (theft) today", money_str(self.day_shrink), "ui_bad"),
            ("Lost (angry) shoppers", str(self.day_lost), "ui_bad"),
            ("", "", "ui_dim"),
            ("Nightly utilities", money_str(util) +
             (" (fridge!)" if fridge else ""), "ui_text"),
            ("Nightly wages", money_str(wages), "ui_text"),
            ("Reputation", f"{self.reputation:.0f}/100", "ui_accent"),
            ("Cleanliness", f"{self.cleanliness:.0f}/100", "ui_accent"),
        ]
        y = body.y + 8
        for label, val, col in lines:
            if label:
                self._text(sc, self.font_m, label, body.x, y, "ui_dim")
                self._text(sc, self.font_m, val, body.x + 360, y, col)
            y += 26
        if self._button((body.x, y + 6, 220, 34), "Take $800 Loan", "ui_gold",
                        text_color="black"):
            self.take_loan()

    # ----------------------------------------------------- title / lobby --
    def _draw_title(self):
        self._draw_world_scaled()
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 210))
        sc.blit(shade, (0, 0))
        if self.title_mode in ("main", "join"):
            self._text(sc, self.font_xl, "GROCERY TYCOON", VIEW_W // 2, 80,
                       "ui_gold", center=True)
            self._text(sc, self.font_m,
                       "Fix up a run-down store -- solo or with friends.",
                       VIEW_W // 2, 134, "ui_text", center=True)
        cx = VIEW_W // 2
        {"main": self._title_main, "join": self._title_join,
         "account": self._title_account, "saves": self._title_saves,
         "newgame": self._title_newgame}.get(
            self.title_mode, self._title_main)(cx)
        if self.title_mode in ("main", "join") and self.status_msg:
            self._text(sc, self.font_s, self.status_msg, cx, 446, "ui_accent",
                       center=True)
        self._text(sc, self.font_s, "Esc to quit", cx, VIEW_H - 36, "ui_dim",
                   center=True)

    def _title_main(self, cx):
        sc = self.screen
        if self._button((cx - 160, 186, 320, 48), "Single Player",
                        "ui_good", text_color="black"):
            self.start_single()
        if self._button((cx - 160, 242, 320, 48), "Host Co-op Game",
                        "ui_gold", text_color="black"):
            self.start_host()
        if self._button((cx - 160, 298, 320, 48), "Join with Room Code"):
            self.title_mode = "join"
            self.status_msg = ""
        label = f"Cloud Saves  ({self.account})" if self.account \
            else "Cloud Saves / Account"
        if self._button((cx - 160, 354, 320, 48), label, "ui_panel2"):
            self.saves_msg = ""
            if self.account:
                self.title_mode = "saves"
                self._refresh_saves()
            else:
                self.title_mode = "account"
        self._text(sc, self.font_s,
                   "Co-op: friends join by room code (browser or app).  "
                   "Cloud Saves: keep your stores on your account.",
                   cx, 418, "ui_dim", center=True)

    def _title_join(self, cx):
        sc = self.screen
        self._text(sc, self.font_m, "Enter the room code:", cx, 210, "ui_text",
                   center=True)
        box = pygame.Rect(cx - 160, 246, 320, 56)
        pygame.draw.rect(sc, C("ui_panel2"), box)
        pygame.draw.rect(sc, C("ui_accent"), box, 2)
        self._text(sc, self.font_xl, (self.ip_text.upper() or "____"),
                   box.centerx, box.y + 8, "white", center=True)
        if self._button((cx - 205, 318, 130, 46), "Join", "ui_good",
                        text_color="black"):
            self.start_join(self.ip_text)
        if self._button((cx - 65, 318, 130, 46), "Paste", "ui_gold",
                        text_color="black"):
            pasted = "".join(ch for ch in paste_clip() if ch.isalnum())[:6]
            if pasted:
                self.ip_text = pasted.upper()
        if self._button((cx + 75, 318, 130, 46), "Back"):
            self.title_mode = "main"
        self._text(sc, self.font_s,
                   "Ask the host for their room code, type it in, and hit Join.",
                   cx, 384, "ui_dim", center=True)

    def _field(self, cx, y, label, value, key):
        sc = self.screen
        active = self.field == key
        box = pygame.Rect(cx - 150, y, 300, 44)
        pygame.draw.rect(sc, C("ui_panel2"), box)
        pygame.draw.rect(sc, C("ui_accent") if active else C("ui_border"), box, 2)
        self._text(sc, self.font_s, label, box.x - 60, y + 12, "ui_dim")
        self._text(sc, self.font_m, value + ("_" if active else ""),
                   box.x + 10, y + 11, "white")
        if self.click_pos and box.collidepoint(self.click_pos):
            self.field = key

    def _title_account(self, cx):
        sc = self.screen
        self._text(sc, self.font_l, "Sign In", cx, 150, "ui_gold", center=True)
        self._field(cx, 200, "User", self.user_text, "user")
        self._field(cx, 258, "Pass", "*" * len(self.pass_text), "pass")
        busy = self.req is not None
        if self._button((cx - 205, 322, 130, 46), "Sign In", "ui_good",
                        enabled=not busy, text_color="black"):
            self._begin("login", "/login",
                        {"username": self.user_text, "password": self.pass_text})
            self.saves_msg = "Signing in..."
        if self._button((cx - 65, 322, 130, 46), "Create", "ui_gold",
                        enabled=not busy, text_color="black"):
            self._begin("register", "/register",
                        {"username": self.user_text, "password": self.pass_text})
            self.saves_msg = "Creating account..."
        if self._button((cx + 75, 322, 130, 46), "Back"):
            self.title_mode = "main"
            self.saves_msg = ""
        self._text(sc, self.font_s,
                   "Click a field to type (Tab switches). New? Pick a name + "
                   "password and hit Create. Casual security -- don't reuse a "
                   "real password.", cx, 384, "ui_dim", center=True)
        if self.saves_msg:
            self._text(sc, self.font_s, self.saves_msg, cx, 414, "ui_accent",
                       center=True)

    def _title_saves(self, cx):
        sc = self.screen
        self._text(sc, self.font_l, f"Cloud Saves -- {self.account}", cx, 100,
                   "ui_gold", center=True)
        busy = self.req is not None
        if busy:
            self._text(sc, self.font_s, "working...", cx, 132, "ui_dim",
                       center=True)
        y = 160
        if not self.save_list and not busy:
            self._text(sc, self.font_s,
                       "No saves yet -- start a New Game, then Save (P) while "
                       "playing.", cx, y, "ui_dim", center=True)
            y += 28
        for s in self.save_list[:7]:
            name = s.get("name", "?")
            row = pygame.Rect(cx - 260, y, 520, 40)
            pygame.draw.rect(sc, C("ui_panel2"), row)
            pygame.draw.rect(sc, C("ui_border"), row, 1)
            self._text(sc, self.font_m, name, row.x + 12, row.y + 10, "ui_text")
            if self._button((row.right - 198, row.y + 5, 90, 30), "Load",
                            "ui_good", enabled=not busy, text_color="black"):
                self._begin("load", "/load", {**self._creds(), "name": name})
                self.saves_msg = "Loading..."
            if self._button((row.right - 100, row.y + 5, 90, 30), "Delete",
                            "ui_panel2", enabled=not busy):
                self._begin("delete", "/delete", {**self._creds(), "name": name})
            y += 46
        y = max(y, 430)
        if self._button((cx - 260, y, 165, 40), "+ New Game", "ui_gold",
                        text_color="black"):
            self.newname_text = ""
            self.title_mode = "newgame"
            self.saves_msg = ""
        if self._button((cx - 82, y, 160, 40), "Sign Out"):
            self.account = None
            self.account_pw = ""
            self.save_list = []
            self.title_mode = "main"
        if self._button((cx + 95, y, 160, 40), "Back"):
            self.title_mode = "main"
        if self.saves_msg:
            self._text(sc, self.font_s, self.saves_msg, cx, VIEW_H - 66,
                       "ui_accent", center=True)

    def _title_newgame(self, cx):
        sc = self.screen
        self._text(sc, self.font_l, "Name your store", cx, 190, "ui_gold",
                   center=True)
        box = pygame.Rect(cx - 200, 240, 400, 50)
        pygame.draw.rect(sc, C("ui_panel2"), box)
        pygame.draw.rect(sc, C("ui_accent"), box, 2)
        self._text(sc, self.font_m, (self.newname_text or "My Store") + "_",
                   box.x + 12, box.y + 14, "white")
        if self._button((cx - 160, 310, 150, 46), "Create", "ui_good",
                        text_color="black"):
            self.current_save = self.newname_text.strip() or "My Store"
            self.start_single()
        if self._button((cx + 10, 310, 150, 46), "Back"):
            self.title_mode = "saves"
        self._text(sc, self.font_s,
                   "This is your save slot. Save anytime from the pause menu (P).",
                   cx, 372, "ui_dim", center=True)

    def _draw_lobby(self):
        self._draw_world_scaled()
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 210))
        sc.blit(shade, (0, 0))
        cx = VIEW_W // 2
        self._text(sc, self.font_xl, "LOBBY", cx, 70, "ui_gold", center=True)
        if self.mode == "host":
            self._text(sc, self.font_m, "Share this room code with friends:",
                       cx, 124, "ui_text", center=True)
            self._text(sc, self.font_xl, self.room_code, cx, 150, "ui_gold",
                       center=True)
            if self._button((cx - 90, 200, 180, 32), "Copy Code", "ui_gold",
                            text_color="black"):
                self.status_msg = ("Code copied -- send it to your friends!"
                                   if copy_clip(self.room_code) else
                                   "Copy failed -- just type it out.")
            self._text(sc, self.font_s,
                       "They pick 'Join with Room Code' (in the app or at "
                       "grocery-tycoon.pages.dev) and enter it.",
                       cx, 240, "ui_dim", center=True)
            if self.status_msg:
                self._text(sc, self.font_s, self.status_msg, cx, 258, "ui_good",
                           center=True)
        else:
            self._text(sc, self.font_m,
                       self.status_msg or f"Joining {self.room_code}...",
                       cx, 150, "ui_accent", center=True)
        self._text(sc, self.font_m, "Players in store:", cx, 276, "ui_text",
                   center=True)
        y = 304
        for p in self.players.values():
            who = p.name + (" (you)" if p.pid == self.local_pid else "")
            if p.pid == 0 and self.mode == "host":
                who = "You (Owner)"
            self._text(sc, self.font_m, "- " + who, cx - 100, y, "ui_good")
            y += 26
        if self.mode == "host":
            if self._button((cx - 150, VIEW_H - 200, 300, 50), "START GAME",
                            "ui_good", text_color="black"):
                self.phase = PHASE_PLAY
        if self._button((cx - 110, VIEW_H - 130, 220, 42),
                        "Leave" if self.mode == "client" else "Cancel"):
            self.leave_to_title()

    def _draw_intro(self):
        self._draw_world_scaled()
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 205))
        sc.blit(shade, (0, 0))
        self._text(sc, self.font_xl, "GROCERY TYCOON", VIEW_W // 2, 70,
                   "ui_gold", center=True)
        lines = [
            "You just bought a run-down corner store. It's filthy, half the",
            "shelves are broken, and the lights barely work.",
            "",
            "MOVE: WASD / Arrows      INTERACT: Space or E      MANAGE: TAB",
            "",
            "Stand on grime to mop it. Face a shelf to stock or repair it.",
            "Face a stockroom crate to order. Stand behind a register to",
            "ring up the line yourself.",
            "",
            "Watch out for: spoilage, shoplifters, power outages, supply",
            "delays, health inspections and staff turnover. Good luck!",
        ]
        y = 150
        for ln in lines:
            self._text(sc, self.font_m, ln, VIEW_W // 2, y,
                       "ui_text" if ln else "ui_dim", center=True)
            y += 26
        if self._button((VIEW_W // 2 - 130, y + 14, 260, 44),
                        "OPEN THE STORE", "ui_good", text_color="black"):
            self.phase = PHASE_PLAY

    def _draw_summary(self):
        self._draw_world_scaled()
        sc = self.screen
        shade = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 200))
        sc.blit(shade, (0, 0))
        m = pygame.Rect(VIEW_W // 2 - 280, 70, 560, VIEW_H - 200)
        self._panel(m, f"DAY {self.day} -- CLOSING TIME")
        s = self.summary
        rows = [
            ("Sales revenue", money_str(s.get("revenue", 0)), "ui_good"),
            ("Restock orders", "-" + money_str(s.get("orders", 0)), "ui_text"),
            ("Wages", "-" + money_str(s.get("wages", 0)), "ui_text"),
            ("Utilities", "-" + money_str(s.get("utilities", 0)), "ui_text"),
        ]
        if s.get("shops"):
            rows.append(("Other shops income", money_str(s["shops"]), "ui_good"))
        if s.get("extra"):
            rows.append(("Extra costs", "-" + money_str(s["extra"]), "ui_bad"))
        if s.get("loan_pay"):
            rows.append(("Loan repayment", "-" + money_str(s["loan_pay"]),
                         "ui_bad"))
        rows += [
            ("Spoiled units (waste)", str(s.get("spoiled", 0)), "ui_bad"),
            ("Lost to theft", money_str(s.get("shrink", 0)), "ui_bad"),
            ("Angry shoppers", str(s.get("lost", 0)), "ui_bad"),
        ]
        y = m.y + 60
        for label, val, col in rows:
            self._text(sc, self.font_m, label, m.x + 30, y, "ui_dim")
            self._text(sc, self.font_m, val, m.right - 30, y, col, right=True)
            y += 30
        pygame.draw.line(sc, C("ui_border"), (m.x + 20, y), (m.right - 20, y), 2)
        y += 12
        net_v = s.get("net", 0)
        self._text(sc, self.font_l, "Net profit", m.x + 30, y, "ui_text")
        self._text(sc, self.font_l, money_str(net_v), m.right - 30, y,
                   "ui_good" if net_v >= 0 else "ui_bad", right=True)
        y += 44
        self._text(sc, self.font_m, "Cash on hand: " + money_str(self.money),
                   m.x + 30, y, "ui_gold")
        label = f"Open Day {self.day + 1}"
        if self.mode == "client":
            label = f"Ready (Day {self.day + 1})"
        if self._button((m.x + m.width // 2 - 130, m.bottom - 56, 260, 42),
                        label, "ui_good", text_color="black"):
            self.advance_day()

    def _draw_over(self):
        sc = self.screen
        sc.fill(C("black"))
        if self.death_reason == "out_of_stock":
            title = "OUT OF STOCK"
            sub = "Empty shelves, empty stockroom -- nothing left to sell."
        else:
            title = "BANKRUPT"
            sub = f"The store went under on Day {self.day}."
        self._text(sc, self.font_xl, title, VIEW_W // 2, VIEW_H // 2 - 80,
                   "ui_bad", center=True)
        self._text(sc, self.font_m, sub, VIEW_W // 2, VIEW_H // 2 - 20,
                   "ui_text", center=True)
        if self.mode == "client":
            self._text(sc, self.font_m, "The owner's store closed.",
                       VIEW_W // 2, VIEW_H // 2 + 8, "ui_dim", center=True)
        if self._button((VIEW_W // 2 - 120, VIEW_H // 2 + 60, 240, 44),
                        "Main Menu", "ui_good", text_color="black"):
            self.leave_to_title()

    def draw(self):
        if self.phase == PHASE_TITLE:
            self._draw_title()
        elif self.phase == PHASE_LOBBY:
            self._draw_lobby()
        elif self.phase == PHASE_INTRO:
            self._draw_intro()
        elif self.phase == PHASE_OVER:
            self._draw_over()
        elif self.phase == PHASE_SUMMARY:
            self._draw_summary()
        else:
            self._draw_playfield_scaled()
            if self._local_scene() == "street":
                self._draw_street_signs()
            self._draw_hud()
            self._draw_nametags()
            self._draw_toasts()
            if self.menu_open:
                self._draw_menu()
            elif self.paused:
                self._draw_pause_overlay()
        pygame.display.flip()

    # ------------------------------------------------------------ input ---
    def handle_events(self):
        self.click_pos = None
        self.mouse_pos = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.click_pos = e.pos
            if e.type == pygame.KEYDOWN:
                if not self._handle_key(e):
                    return False
        return True

    def _handle_key(self, e):
        k = e.key
        if self.phase == PHASE_TITLE:
            if self.title_mode == "join":
                mods = pygame.key.get_mods()
                if k == pygame.K_v and (mods & (pygame.KMOD_META | pygame.KMOD_CTRL)):
                    pasted = "".join(ch for ch in paste_clip() if ch.isalnum())[:6]
                    if pasted:
                        self.ip_text = pasted.upper()
                elif k == pygame.K_RETURN:
                    self.start_join(self.ip_text)
                elif k == pygame.K_BACKSPACE:
                    self.ip_text = self.ip_text[:-1]
                elif k == pygame.K_ESCAPE:
                    self.title_mode = "main"
                elif e.unicode and e.unicode.isalnum() and len(self.ip_text) < 6:
                    self.ip_text += e.unicode.upper()
            elif self.title_mode == "account":
                if k == pygame.K_TAB:
                    self.field = "pass" if self.field == "user" else "user"
                elif k == pygame.K_RETURN:
                    self._begin("login", "/login", {"username": self.user_text,
                                "password": self.pass_text})
                    self.saves_msg = "Signing in..."
                elif k == pygame.K_ESCAPE:
                    self.title_mode = "main"
                elif k == pygame.K_BACKSPACE:
                    if self.field == "user":
                        self.user_text = self.user_text[:-1]
                    else:
                        self.pass_text = self.pass_text[:-1]
                elif e.unicode and e.unicode.isprintable():
                    if self.field == "user":
                        if (e.unicode.isalnum() or e.unicode == "_") \
                                and len(self.user_text) < 20:
                            self.user_text += e.unicode.lower()
                    elif len(self.pass_text) < 40:
                        self.pass_text += e.unicode
            elif self.title_mode == "newgame":
                if k == pygame.K_RETURN:
                    self.current_save = self.newname_text.strip() or "My Store"
                    self.start_single()
                elif k == pygame.K_ESCAPE:
                    self.title_mode = "saves"
                elif k == pygame.K_BACKSPACE:
                    self.newname_text = self.newname_text[:-1]
                elif e.unicode and e.unicode.isprintable() \
                        and e.unicode not in '"\\' and len(self.newname_text) < 24:
                    self.newname_text += e.unicode
            elif self.title_mode == "saves":
                if k == pygame.K_ESCAPE:
                    self.title_mode = "main"
            elif k == pygame.K_ESCAPE:
                return False
            return True
        if self.phase == PHASE_LOBBY:
            if k == pygame.K_ESCAPE:
                self.leave_to_title()
            elif k == pygame.K_RETURN and self.mode == "host":
                self.phase = PHASE_PLAY
            return True
        if self.phase == PHASE_INTRO:
            if k in (pygame.K_SPACE, pygame.K_RETURN):
                self.phase = PHASE_PLAY
            elif k == pygame.K_ESCAPE:
                self.leave_to_title()
            return True
        if self.phase == PHASE_SUMMARY:
            if k in (pygame.K_SPACE, pygame.K_RETURN):
                self.advance_day()
            return True
        if self.phase == PHASE_PLAY:
            if k in (pygame.K_TAB, pygame.K_m):
                self.menu_open = not self.menu_open
            elif k == pygame.K_p and self.mode != "client" and not self.menu_open:
                self.paused = not self.paused
            elif k in (pygame.K_SPACE, pygame.K_e) and not self.menu_open \
                    and not self.paused:
                self.interact_local()
            elif k == pygame.K_ESCAPE:
                if self.menu_open:
                    self.menu_open = False
                else:
                    self.leave_to_title()
        return True

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            running = self.handle_events()
            self._net_tick(dt)
            self._poll_request()
            self.update(dt)
            self.draw()
        self._teardown_net()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
