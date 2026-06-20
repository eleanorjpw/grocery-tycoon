"""
The street outside your store -- unlocked by the "See the World" upgrade.

Each shop is a big, detailed storefront building filling most of the height
down to the road. You walk the strip in front of them and press E at a door to
buy that shop (each pays a daily passive income).
"""
from settings import GRID_W, GRID_H

WALL, FLOOR, DOOR, ROAD = "wall", "floor", "door", "road"

# id, name, price, daily income, awning colour, window theme
SHOPS = [
    ("cafe",    "Cozy Cafe",    1500, 110, "red",        "cafe"),
    ("florist", "Flower Shop",  2400, 175, "green",      "florist"),
    ("books",   "Bookstore",    3600, 270, "shirt_blue", "books"),
    ("electro", "Electronics",  5200, 400, "purple",     "electro"),
]
BLOCK_W = 4                       # each building is 4 tiles wide (5 blocks = 20)
BUILD_BOTTOM = 9                  # buildings occupy rows 0..9; doors on row 9
WALK_ROW = 10                     # sidewalk you walk on, in front of the doors


class StreetShop:
    def __init__(self, sid, name, price, income, color, theme, c0):
        self.id = sid
        self.name = name
        self.price = price
        self.income = income
        self.color = color
        self.theme = theme
        self.c0 = c0
        self.c1 = c0 + BLOCK_W - 1
        self.door = (c0 + 2, BUILD_BOTTOM)
        self.owned = False


class Street:
    def __init__(self):
        self.grid = [[FLOOR] * GRID_W for _ in range(GRID_H)]
        # buildings: solid walls rows 0..9
        for r in range(0, BUILD_BOTTOM + 1):
            for c in range(GRID_W):
                self.grid[r][c] = WALL
        # sidewalk you walk on
        for c in range(GRID_W):
            self.grid[WALK_ROW][c] = FLOOR
        # road at the very bottom (black + yellow dashes)
        for r in range(WALK_ROW + 1, GRID_H):
            for c in range(GRID_W):
                self.grid[r][c] = ROAD

        self.shops = []
        for i, (sid, name, price, income, color, theme) in enumerate(SHOPS):
            sh = StreetShop(sid, name, price, income, color, theme, i * BLOCK_W)
            self.shops.append(sh)
            self.grid[BUILD_BOTTOM][sh.door[0]] = DOOR

        # your own store is the last building block
        self.store_c0 = len(SHOPS) * BLOCK_W
        self.store_col = self.store_c0 + 2
        self.store_door = (self.store_col, BUILD_BOTTOM)
        self.grid[BUILD_BOTTOM][self.store_col] = DOOR

        # where the player appears when stepping outside
        self.entrance = (self.store_col, WALK_ROW)

    # building blocks for the renderer: (c0, color, theme, name, is_store)
    def buildings(self):
        out = [(s.c0, s.color, s.theme, s, False) for s in self.shops]
        out.append((self.store_c0, "ui_gold", "grocery", None, True))
        return out

    def in_bounds(self, c, r):
        return 0 <= c < GRID_W and 0 <= r < GRID_H

    def is_floor(self, c, r):
        return self.in_bounds(c, r) and self.grid[r][c] in (FLOOR, DOOR, ROAD)

    def walkable(self, c, r):
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] in (FLOOR, ROAD)

    def fixture_at(self, c, r):
        return None
