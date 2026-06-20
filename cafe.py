"""
The Cozy Cafe interior -- a restaurant minigame you run once you own the cafe.

Guests sit at a table and order a specific dish. You fire the order at the
kitchen, it cooks, you pick it up when ready and carry it to the right guest.
After eating they ask for the check -- grab it at the register and bring it over
to get paid. Buy ingredient supplies, and spend on cafe-specific upgrades.
"""
import random

from settings import GRID_W, GRID_H, CAFE_FOODS
from entities import Walker

WALL, FLOOR, DOOR, COUNTER, TABLE = "wall", "floor", "door", "counter", "table"

BASE_TABLES = [(3, 4), (7, 4), (11, 4), (15, 4),
               (3, 7), (7, 7), (11, 7), (15, 7)]
PATIO_TABLES = [(3, 10), (7, 10), (11, 10), (15, 10)]
FOOD_KEYS = list(CAFE_FOODS.keys())
STOVE_COLS = [4, 6, 8, 10, 12, 14]      # one stove per dish along the top


class Cafe:
    def __init__(self):
        self.grid = [[FLOOR] * GRID_W for _ in range(GRID_H)]
        for r in range(GRID_H):
            self.grid[r][0] = self.grid[r][GRID_W - 1] = WALL
        for c in range(GRID_W):
            self.grid[0][c] = self.grid[GRID_H - 1][c] = WALL
        for c in (9, 10):
            self.grid[GRID_H - 1][c] = DOOR
        self.door_tiles = {(9, GRID_H - 1), (10, GRID_H - 1)}
        # one labelled stove per dish -- click (or E) a stove to make that dish
        self.stoves = []
        for food, c in zip(FOOD_KEYS, STOVE_COLS):
            self.grid[2][c] = COUNTER
            self.stoves.append({"food": food, "tile": (c, 2)})
        self.kitchen = [s["tile"] for s in self.stoves]
        self.stove_by_tile = {s["tile"]: s["food"] for s in self.stoves}
        # register (grab a guest's check here) + supply crate
        self.register = (17, 2)
        self.grid[2][17] = COUNTER
        self.supply = (2, 2)
        self.grid[2][2] = WALL
        self.tables = []
        for spot in BASE_TABLES:
            self._add_table(spot)
        self.has_patio = False
        self.entrance = (9, 11)

    def _add_table(self, spot):
        tc, tr = spot
        self.grid[tr][tc] = TABLE
        self.tables.append({"table": (tc, tr), "seat": (tc, tr + 1),
                            "guest": None})

    def add_patio(self):
        if self.has_patio:
            return
        self.has_patio = True
        for spot in PATIO_TABLES:
            self._add_table(spot)

    def in_bounds(self, c, r):
        return 0 <= c < GRID_W and 0 <= r < GRID_H

    def is_floor(self, c, r):
        return self.in_bounds(c, r) and self.grid[r][c] in (FLOOR, DOOR)

    def walkable(self, c, r):
        return self.is_floor(c, r)

    def fixture_at(self, c, r):
        return None

    def free_table(self):
        free = [t for t in self.tables if t["guest"] is None]
        return random.choice(free) if free else None


class CafeGuest:
    def __init__(self, cafe, skin):
        self.w = Walker(9, GRID_H - 1)
        self.w.SPEED = 36.0 + random.uniform(-4, 8)
        self.skin = skin
        self.state = "enter"
        self.table = None
        self.seat = None
        self.order = random.choice(FOOD_KEYS)
        self.fired = False          # kitchen has started cooking this order
        self.think = random.uniform(1.0, 2.6)
        self.eat = random.uniform(4.0, 7.0)
        self.patience = random.uniform(24, 36)
        self.start_patience = self.patience
        self.done = False
        self.angry = False

    def update(self, game, dt):
        cafe = game.cafe
        if self.state == "enter":
            t = cafe.free_table()
            if t is None:
                self._leave(game)
                return
            self.table, self.seat = t, t["seat"]
            t["guest"] = self
            self.state = "to_seat"
            if not self.w.set_goal(cafe, self.seat):
                self._leave(game)
        elif self.state == "to_seat":
            if self.w.step(dt) or not self.w.path:
                self.state = "seated"
                self.w.facing = "up"
        elif self.state == "seated":
            self.think -= dt
            if self.think <= 0:
                self.state = "ordered"
        elif self.state == "ordered":
            self.patience -= dt
            if self.patience <= 0:
                self.angry = True
                game.on_cafe_rage(self)
                self._leave(game)
        elif self.state == "eating":
            self.eat -= dt
            if self.eat <= 0:
                self.state = "check"
                self.patience = random.uniform(20, 30)
                self.start_patience = self.patience
        elif self.state == "check":
            self.patience -= dt
            if self.patience <= 0:
                self.angry = True
                game.on_cafe_rage(self)
                self._leave(game)
        elif self.state == "leaving":
            if self.w.step(dt) or not self.w.path:
                self.done = True

    def serve_food(self):
        self.state = "eating"

    def patience_frac(self):
        if self.start_patience <= 0:
            return 0.0
        return max(0.0, min(1.0, self.patience / self.start_patience))

    def _leave(self, game):
        if self.table:
            self.table["guest"] = None
        self.state = "leaving"
        self.w.facing = "down"
        self.w.set_goal(game.cafe, (9, GRID_H - 1))
