"""
Grocery Tycoon - global settings, palette, and game data.

The whole game uses a chunky 16px tile grid scaled up (32-bit / Stardew-ish look).
"""

# ---------------------------------------------------------------- rendering ---
TILE = 16                # world pixels per tile
SCALE = 3                # integer upscale for the chunky pixel look
GRID_W = 20              # store width in tiles
GRID_H = 13              # store height in tiles

PLAYFIELD_W = GRID_W * TILE          # 320
PLAYFIELD_H = GRID_H * TILE          # 208
HUD_H = 40                           # HUD height in *world* px (scaled with view)

VIEW_W = PLAYFIELD_W * SCALE         # 960
VIEW_H = (PLAYFIELD_H + HUD_H) * SCALE
WIN_W = VIEW_W
WIN_H = VIEW_H
FPS = 60

# ------------------------------------------------------------------- timing ---
# A "day" runs the store clock from OPEN_HOUR to CLOSE_HOUR.
OPEN_HOUR = 8
CLOSE_HOUR = 20
# real seconds per in-game hour
SECONDS_PER_HOUR = 18.0          # ~3.6 real min per full open day

# --------------------------------------------------------------- economy ------
START_MONEY = 500.0
START_DAY = 1

# --------------------------------------------------------------- palette ------
# A warm, slightly desaturated Stardew-style palette.
PAL = {
    "black":     (24, 20, 28),
    "dark":      (43, 38, 51),
    "shadow":    (58, 50, 64),
    "wall":      (94, 73, 71),
    "wall_lt":   (120, 96, 92),
    "wall_dk":   (70, 52, 52),
    "floor1":    (196, 174, 142),
    "floor2":    (182, 158, 126),
    "floor_crack": (120, 104, 86),
    "floor_new1": (214, 206, 188),
    "floor_new2": (200, 190, 170),
    "grout":     (150, 130, 104),
    "wood":      (150, 100, 58),
    "wood_dk":   (110, 70, 40),
    "wood_lt":   (184, 132, 80),
    "metal":     (150, 158, 170),
    "metal_dk":  (104, 112, 126),
    "metal_lt":  (196, 202, 214),
    "glass":     (150, 200, 214),
    "dirt":      (96, 84, 60),
    "dirt2":     (78, 66, 48),
    "green":     (96, 168, 76),
    "green_dk":  (60, 120, 52),
    "red":       (200, 72, 64),
    "red_dk":    (150, 48, 44),
    "orange":    (228, 148, 64),
    "yellow":    (238, 206, 96),
    "purple":    (150, 96, 168),
    "brown":     (150, 106, 70),
    "white":     (238, 238, 226),
    "cream":     (224, 210, 178),
    "skin":      (232, 184, 144),
    "skin2":     (208, 156, 120),
    "hair_brn":  (96, 66, 42),
    "shirt_blue":(72, 116, 196),
    "shirt_red": (196, 80, 72),
    "shirt_grn": (76, 156, 96),
    "shirt_ylw": (228, 196, 92),
    "apron":     (84, 132, 168),
    "ui_panel":  (47, 40, 56),
    "ui_panel2": (62, 53, 74),
    "ui_border": (150, 124, 96),
    "ui_text":   (236, 230, 214),
    "ui_dim":    (160, 150, 138),
    "ui_good":   (120, 200, 110),
    "ui_bad":    (224, 96, 88),
    "ui_gold":   (240, 200, 96),
    "ui_accent": (236, 168, 84),
}

# --------------------------------------------------------------- products -----
# category color is used to tint the product on its shelf.
# perishable items spoil without refrigeration.
# Prices reflect modern (mid-2020s) US grocery prices. wholesale is what the
# store pays; retail is what shoppers pay (grocery margins are thin).
PRODUCTS = [
    # key,        name,              category,    wholesale, retail, perishable, color
    ("bread",     "Bread",           "Bakery",    2.10,   3.49, True,  "wood_lt"),
    ("milk",      "Milk (gal)",      "Dairy",     3.00,   4.29, True,  "white"),
    ("eggs",      "Eggs (dozen)",    "Dairy",     3.40,   4.99, True,  "cream"),
    ("apples",    "Apples (bag)",    "Produce",   1.40,   2.49, True,  "red"),
    ("bananas",   "Bananas (lb)",    "Produce",   0.45,   0.79, True,  "yellow"),
    ("lettuce",   "Lettuce",         "Produce",   1.40,   2.49, True,  "green"),
    ("chicken",   "Chicken (lb)",    "Meat",      3.30,   4.99, True,  "skin2"),
    ("cereal",    "Cereal",          "Pantry",    3.50,   5.49, False, "orange"),
    ("pasta",     "Pasta",           "Pantry",    1.10,   1.99, False, "yellow"),
    ("beans",     "Canned Beans",    "Pantry",    0.70,   1.29, False, "red_dk"),
    ("soda",      "Soda (2L)",       "Drinks",    1.40,   2.49, False, "purple"),
    ("chips",     "Chips",           "Snacks",    2.90,   4.99, False, "orange"),
    ("soap",      "Soap",            "Household", 2.30,   3.99, False, "glass"),
    ("coffee",    "Coffee",          "Pantry",    5.80,   8.99, False, "wood_dk"),
]

# quick lookup
PRODUCT_BY_KEY = {p[0]: {
    "key": p[0], "name": p[1], "category": p[2],
    "wholesale": p[3], "retail": p[4], "perishable": p[5], "color": p[6],
} for p in PRODUCTS}

CASE_SIZE = 12           # ordering happens in cases of 12 units

# --------------------------------------------------------------- staff --------
STAFF_TYPES = {
    "cashier": {"name": "Cashier", "wage": 110, "color": "shirt_blue",
                "desc": "Runs a checkout so you don't have to."},
    "stocker": {"name": "Stocker", "wage": 95,  "color": "shirt_grn",
                "desc": "Refills low shelves from the stockroom."},
    "cleaner": {"name": "Cleaner", "wage": 85,  "color": "shirt_ylw",
                "desc": "Mops up dirt and keeps the place tidy."},
    "guard":   {"name": "Security","wage": 130, "color": "shirt_red",
                "desc": "Deters shoplifters and reduces shrinkage."},
}

# --------------------------------------------------------------- upgrades -----
# id, name, cost, one-line description
UPGRADES = [
    ("lights",   "Bright Lighting",   600,
     "Replace the flickering tubes. +reputation, shoppers feel safe."),
    ("floor",    "New Floor Tiles",   800,
     "Lay fresh tile. Cleaner-looking and slower to get dirty."),
    ("fridge",   "Refrigeration",     1200,
     "Proper cold cases. Perishables spoil far slower."),
    ("cameras",  "Security Cameras",  900,
     "CCTV over the aisles. Cuts shoplifting losses."),
    ("signage",  "Storefront Signage",500,
     "A bright new sign out front pulls in more foot traffic."),
    ("see_world","See the World",    0,
     "FREE -- walk out the front door and down the street to buy OTHER "
     "shops (each pays you daily passive income)."),
]

# buying an individual extra shelf (placed along the back wall)
SHELF_PRICE = 160
REPAIR_COST = 80            # cost to fix a broken shelf

# --------------------------------------------------------------- network ------
NET_PORT = 50007            # TCP port the host listens on (legacy direct-IP)

# Cloudflare relay for room-code multiplayer (works in browser + desktop).
# Filled in after deploying relay/  (wss://<worker>.workers.dev/ws)
RELAY_URL = "wss://grocery-tycoon-relay.eleanorjpw.workers.dev/ws"

# Cloudflare account + cloud-save backend (saves/).
SAVES_URL = "https://grocery-tycoon-saves.eleanorjpw.workers.dev"

# --------------------------------------------------------------- balance ------
START_CLEANLINESS = 35
START_REPUTATION = 30
RENT_PER_DAY = 0            # rent removed
UTILITIES_BASE = 25
UTILITIES_FRIDGE = 35       # added when refrigeration installed (energy cost!)
SHELF_CAPACITY = 24
LOW_SHELF = 8               # stocker refills below this
