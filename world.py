"""
The store: tile map + fixtures (shelves, checkouts, crates). Builds the
initial run-down layout the player has to fix up.
"""
from settings import (GRID_W, GRID_H, PRODUCTS, PRODUCT_BY_KEY,
                      SHELF_CAPACITY)

WALL, FLOOR, DOOR = "wall", "floor", "door"


class Shelf:
    def __init__(self, col, row, product_key, broken=False):
        self.col, self.row = col, row
        self.product = product_key
        p = PRODUCT_BY_KEY[product_key]
        self.category = p["category"]
        self.color = p["color"]
        self.perishable = p["perishable"]
        self.capacity = SHELF_CAPACITY
        self.stock = 0 if broken else 6
        self.broken = broken
        self.access = None    # walkable tile shoppers/stockers use

    def level(self):
        """0..3 fullness bucket for the sprite."""
        if self.broken or self.stock <= 0:
            return 0
        r = self.stock / self.capacity
        return 1 if r < 0.34 else (2 if r < 0.67 else 3)


class Checkout:
    def __init__(self, col, row):
        self.col, self.row = col, row
        self.staff_tile = (col, row - 1)     # cashier stands here
        self.cust_tile = (col, row + 1)      # shopper pays from here
        self.cashier = None                  # assigned Staff or None
        self.queue = []                      # list of Customer waiting


class World:
    def __init__(self):
        self.grid = [[WALL if (c == 0 or r == 0 or c == GRID_W - 1
                               or r == GRID_H - 1) else FLOOR
                      for c in range(GRID_W)] for r in range(GRID_H)]
        self.shelves = []
        self.checkouts = []
        self.crates = []          # decorative stockroom crates (col,row)
        self.plants = []
        self.dirty = {}           # (col,row) -> level 1..3
        self.cracks = set()       # (col,row) cracked floor tiles
        self._build()

    # ----------------------------------------------------------- build ----
    def _build(self):
        # entrance: two-wide door in the bottom wall
        for c in (9, 10):
            self.grid[GRID_H - 1][c] = DOOR

        # shelf gondolas: two blocks of 3-wide runs on three rows
        rows = [3, 5, 7]
        left = [3, 4, 5]
        right = [14, 15, 16]
        keys = [p[0] for p in PRODUCTS]
        i = 0
        broken_set = {(5, 3), (14, 5), (16, 7), (3, 7)}   # start damaged
        for r in rows:
            for c in left + right:
                key = keys[i % len(keys)]
                i += 1
                sh = Shelf(c, r, key, broken=((c, r) in broken_set))
                self.shelves.append(sh)

        # checkouts near the front
        for c in (6, 13):
            self.checkouts.append(Checkout(c, 10))

        # stockroom crates (top corners)
        for (c, r) in [(1, 1), (2, 1), (3, 1), (18, 1), (17, 1)]:
            self.crates.append((c, r))

        # decorative plants
        self.plants = [(1, 11), (18, 11)]

        # empty spots along the back wall where the player can BUY new shelves
        self.expansion_slots = [(c, 1) for c in (6, 7, 8, 9, 10, 11, 12, 13)]

        # compute access tiles for fixtures
        for sh in self.shelves:
            sh.access = self._nearest_walkable_neighbor(sh.col, sh.row)

        # run-down look: cracks over most of the floor, plus grime
        for r in range(1, GRID_H - 1):
            for c in range(1, GRID_W - 1):
                if self.is_floor(c, r) and (c * 7 + r * 13) % 3 == 0:
                    self.cracks.add((c, r))
        grime = [(8, 11), (11, 11), (4, 9), (15, 9), (9, 2), (10, 8),
                 (7, 4), (12, 6), (3, 11), (16, 11), (8, 8), (6, 6),
                 (13, 4), (2, 6), (17, 8), (10, 4)]
        for j, (c, r) in enumerate(grime):
            if self.walkable(c, r):
                self.dirty[(c, r)] = 1 + (j % 3)

    # --------------------------------------------------------- queries ----
    def in_bounds(self, c, r):
        return 0 <= c < GRID_W and 0 <= r < GRID_H

    def is_floor(self, c, r):
        return self.in_bounds(c, r) and self.grid[r][c] in (FLOOR, DOOR)

    def fixture_at(self, c, r):
        for sh in self.shelves:
            if sh.col == c and sh.row == r:
                return sh
        for ch in self.checkouts:
            if ch.col == c and ch.row == r:
                return ch
        if (c, r) in self.crates or (c, r) in self.plants:
            return "decor"
        return None

    def walkable(self, c, r):
        if not self.is_floor(c, r):
            return False
        return self.fixture_at(c, r) is None

    def _nearest_walkable_neighbor(self, c, r):
        # prefer below, then above, then sides
        for (dc, dr) in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
            if self.walkable(c + dc, r + dr):
                return (c + dc, r + dr)
        return None

    def next_free_slot(self):
        """First back-wall slot with no shelf yet, for buying expansions."""
        for s in self.expansion_slots:
            if self.is_floor(*s) and self.fixture_at(*s) is None:
                return s
        return None

    def stockroom_points(self):
        pts = []
        for (c, r) in self.crates:
            n = self._nearest_walkable_neighbor(c, r)
            if n:
                pts.append(n)
        return pts or [(2, 2)]
