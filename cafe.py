"""
The Cozy Cafe interior -- a little restaurant minigame you run once you own the
cafe on the street. Guests come in, sit at a table, order, wait for you to bring
the food, eat, then ask for the check. You pay for ingredients (supplies).
"""
import random

from settings import GRID_W, GRID_H, CAFE_FOODS
from entities import Walker

WALL, FLOOR, DOOR, COUNTER, TABLE = "wall", "floor", "door", "counter", "table"

TABLE_SPOTS = [(5, 5), (9, 5), (14, 5), (5, 8), (9, 8), (14, 8)]


class Cafe:
    def __init__(self):
        self.grid = [[FLOOR] * GRID_W for _ in range(GRID_H)]
        for r in range(GRID_H):
            self.grid[r][0] = self.grid[r][GRID_W - 1] = WALL
        for c in range(GRID_W):
            self.grid[0][c] = self.grid[GRID_H - 1][c] = WALL
        # exit door (back to the street)
        for c in (9, 10):
            self.grid[GRID_H - 1][c] = DOOR
        self.door_tiles = {(9, GRID_H - 1), (10, GRID_H - 1)}
        # kitchen pass counter along the top
        self.kitchen = []
        for c in range(6, 14):
            self.grid[2][c] = COUNTER
            self.kitchen.append((c, 2))
        # ingredient supply crate (top-left)
        self.supply = (2, 2)
        self.grid[2][2] = WALL
        # tables, each with a seat tile directly below it
        self.tables = []
        for (tc, tr) in TABLE_SPOTS:
            self.grid[tr][tc] = TABLE
            self.tables.append({"table": (tc, tr), "seat": (tc, tr + 1),
                                "guest": None})
        self.entrance = (9, 11)

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
        self.order = None
        self.think = random.uniform(1.2, 2.8)
        self.eat = random.uniform(4.0, 7.0)
        self.patience = random.uniform(22, 34)
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
                self.order = random.choice(CAFE_FOODS)
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
