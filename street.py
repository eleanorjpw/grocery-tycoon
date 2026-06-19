"""
The street outside your store -- unlocked by the "See the World" upgrade.
You walk the sidewalk and can buy other shops, each of which pays you a daily
passive income.
"""
from settings import GRID_W, GRID_H

WALL, FLOOR, DOOR, ROAD = "wall", "floor", "door", "road"

# id, name, price, daily income, awning colour
SHOPS = [
    ("cafe",    "Cozy Cafe",    1500, 110, "red"),
    ("florist", "Flower Shop",  2400, 175, "green"),
    ("books",   "Bookstore",    3600, 270, "shirt_blue"),
    ("electro", "Electronics",  5200, 400, "purple"),
]
SHOP_COLS = [3, 6, 9, 12]
STORE_COL = 16              # your own store's door on the street


class StreetShop:
    def __init__(self, sid, name, price, income, color, col):
        self.id = sid
        self.name = name
        self.price = price
        self.income = income
        self.color = color
        self.col = col
        self.door = (col, 4)
        self.owned = False


class Street:
    def __init__(self):
        self.grid = [[FLOOR] * GRID_W for _ in range(GRID_H)]
        # building block (rows 0..4) + perimeter
        for r in range(GRID_H):
            for c in range(GRID_W):
                if r <= 4 or r == GRID_H - 1 or c == 0 or c == GRID_W - 1:
                    self.grid[r][c] = WALL
        # road band near the bottom
        for r in range(9, 12):
            for c in range(1, GRID_W - 1):
                self.grid[r][c] = ROAD
        # shop doors carved into the storefront (row 4)
        self.shops = []
        for (sid, name, price, income, color), c in zip(SHOPS, SHOP_COLS):
            self.shops.append(StreetShop(sid, name, price, income, color, c))
            self.grid[4][c] = DOOR
        # your own store's door (to go back inside)
        self.store_col = STORE_COL
        self.store_door = (STORE_COL, 4)
        self.grid[4][STORE_COL] = DOOR
        # where the player appears when stepping outside
        self.entrance = (STORE_COL, 6)

    def in_bounds(self, c, r):
        return 0 <= c < GRID_W and 0 <= r < GRID_H

    def is_floor(self, c, r):
        return self.in_bounds(c, r) and self.grid[r][c] in (FLOOR, DOOR, ROAD)

    def walkable(self, c, r):
        # doors are storefronts you buy from, not tiles you walk onto
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] in (FLOOR, ROAD)

    def fixture_at(self, c, r):
        return None
