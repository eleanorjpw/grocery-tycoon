"""
Procedural 32-bit-style pixel art. No external image files needed -- every
sprite is drawn into a 16x16 surface at load time, then scaled up by the view.
"""
import pygame
from settings import PAL, TILE

T = TILE


def _surf():
    s = pygame.Surface((T, T), pygame.SRCALPHA)
    return s


def px(s, c, x, y, w=1, h=1):
    """Fill a block of pixels with a palette colour."""
    if isinstance(c, str):
        c = PAL[c]
    pygame.draw.rect(s, c, (x, y, w, h))


def _noise(s, color, spots):
    """Scatter a few darker/lighter pixels for texture (deterministic)."""
    if isinstance(color, str):
        color = PAL[color]
    for (x, y) in spots:
        px(s, color, x, y)


# --------------------------------------------------------------- tiles --------
def floor_tile(new=False, crack=False, dirty=0):
    s = _surf()
    a, b = ("floor_new1", "floor_new2") if new else ("floor1", "floor2")
    px(s, a, 0, 0, T, T)
    # subtle checker / grout lines
    for y in range(0, T, 8):
        for x in range(0, T, 8):
            if (x // 8 + y // 8) % 2 == 0:
                px(s, b, x, y, 8, 8)
    px(s, "grout", 0, 0, T, 1)
    px(s, "grout", 0, 0, 1, T)
    if crack and not new:
        # a thin crack across the tile
        for (x, y) in [(4, 2), (5, 3), (5, 4), (6, 5), (6, 6), (7, 7),
                       (8, 8), (8, 9), (9, 10), (10, 11)]:
            px(s, "floor_crack", x, y)
    if dirty:
        _dirty_overlay(s, dirty)
    return s


def _dirty_overlay(s, level):
    spots = [(2, 11), (3, 12), (4, 11), (11, 3), (12, 4), (13, 3),
             (10, 12), (12, 13), (3, 4), (13, 11), (7, 8), (8, 6)]
    n = min(len(spots), 4 + level * 3)
    for i in range(n):
        x, y = spots[i % len(spots)]
        x = (x + i * 3) % T
        y = (y + i * 5) % T
        px(s, "dirt", x, y, 2, 2)
        px(s, "dirt2", x, y)


def wall_tile():
    s = _surf()
    px(s, "wall", 0, 0, T, T)
    # brick rows
    for y in range(0, T, 4):
        px(s, "wall_dk", 0, y, T, 1)
        off = 0 if (y // 4) % 2 == 0 else 4
        for x in range(off, T, 8):
            px(s, "wall_dk", x, y, 1, 4)
    px(s, "wall_lt", 0, 0, T, 1)
    return s


def door_tile():
    s = _surf()
    px(s, "floor1", 0, 0, T, T)
    px(s, "wood_dk", 1, 0, T - 2, 2)
    # welcome mat
    px(s, "green_dk", 2, 11, 12, 4)
    px(s, "green", 3, 12, 10, 2)
    return s


# --------------------------------------------------------------- fixtures -----
def shelf(category_color="orange", level=3, broken=False):
    """A grocery shelf seen from above-ish. level 0..3 = how full."""
    s = _surf()
    if broken:
        px(s, "wood_dk", 0, 1, T, T - 2)
        px(s, "shadow", 1, 2, T - 2, T - 4)
        # toppled / cracked boards
        px(s, "wood", 1, 3, T - 2, 2)
        px(s, "wood", 2, 9, T - 3, 2)
        for (x, y) in [(3, 6), (7, 7), (10, 5), (12, 10), (5, 11)]:
            px(s, "black", x, y, 2, 1)
        return s
    # shelf body
    px(s, "wood_dk", 0, 0, T, T)
    px(s, "wood", 1, 1, T - 2, T - 2)
    px(s, "wood_lt", 1, 1, T - 2, 1)
    # two product rows
    if level > 0:
        rows = [(2, 3), (2, 9)]
        per = max(1, level)
        for (rx, ry) in rows:
            for i in range(per):
                bx = rx + i * 3
                if bx > T - 3:
                    break
                px(s, category_color, bx, ry, 2, 4)
                px(s, "white", bx, ry, 2, 1)
    else:
        # empty: just dark shelf interior
        px(s, "wood_dk", 2, 3, T - 4, 4)
        px(s, "wood_dk", 2, 9, T - 4, 4)
    return s


def fridge(category_color="white", level=3):
    s = _surf()
    px(s, "metal_dk", 0, 0, T, T)
    px(s, "metal", 1, 1, T - 2, T - 2)
    # glass door
    px(s, "glass", 2, 2, T - 4, T - 4)
    px(s, "metal_lt", 2, 2, T - 4, 1)
    if level > 0:
        for i in range(max(1, level)):
            bx = 3 + i * 3
            if bx > T - 4:
                break
            px(s, category_color, bx, 4, 2, 3)
            px(s, category_color, bx, 9, 2, 3)
    # frosty highlight
    px(s, "white", 3, 3, 1, T - 6)
    return s


def counter():
    s = _surf()
    px(s, "wood_dk", 0, 0, T, T)
    px(s, "wood", 0, 0, T, 12)
    px(s, "wood_lt", 0, 0, T, 1)
    px(s, "metal_dk", 0, 12, T, 4)
    return s


def register():
    s = _surf()
    px(s, "wood", 0, 0, T, T)
    px(s, "wood_lt", 0, 0, T, 1)
    # the register body
    px(s, "metal_dk", 3, 3, 10, 9)
    px(s, "metal", 4, 4, 8, 5)
    px(s, "glass", 5, 5, 6, 3)       # screen
    px(s, "metal_lt", 4, 10, 8, 2)   # keypad
    px(s, "green", 11, 4, 1, 1)
    return s


def crate(category_color="brown", level=3):
    """A stockroom crate. level 0..3 = how much stock it's holding."""
    s = _surf()
    # contents poking out the top (more = fuller)
    if level >= 1:
        px(s, category_color, 3, 1, 3, 3)
        px(s, "white", 3, 1, 1, 1)
    if level >= 2:
        px(s, category_color, 8, 1, 3, 3)
    if level >= 3:
        px(s, "orange", 6, 0, 2, 3)
    # wooden box
    px(s, "wood_dk", 1, 2, T - 2, T - 3)
    px(s, "wood", 2, 3, T - 4, T - 5)
    px(s, "wood_lt", 2, 3, T - 4, 1)
    # slats
    px(s, "wood_dk", 2, 8, T - 4, 1)
    px(s, "wood_dk", 2, 12, T - 4, 1)
    if level == 0:
        # empty: darker interior showing through
        px(s, "shadow", 3, 4, T - 6, 3)
    return s


def sidewalk_tile():
    s = _surf()
    px(s, "metal", 0, 0, T, T)
    px(s, "metal_dk", 0, 0, T, 1)
    px(s, "metal_dk", 0, 0, 1, T)
    px(s, "metal_lt", 1, 1, T - 2, 1)
    # paver seams
    px(s, "metal_dk", 8, 0, 1, T)
    px(s, "metal_dk", 0, 8, T, 1)
    return s


def road_tile(dash=False):
    s = _surf()
    px(s, "dark", 0, 0, T, T)
    px(s, "shadow", 0, 0, T, 1)
    _noise(s, "black", [(3, 5), (11, 9), (6, 12), (13, 3), (8, 7)])
    if dash:
        px(s, "yellow", 6, 4, 4, 8)
    return s


def storefront(color="red"):
    """A building facade tile with a coloured awning band."""
    s = _surf()
    px(s, "wall", 0, 0, T, T)
    for y in range(0, T, 4):
        px(s, "wall_dk", 0, y, T, 1)
    # windows
    px(s, "glass", 2, 3, 4, 5)
    px(s, "glass", 10, 3, 4, 5)
    px(s, "metal_dk", 2, 3, 4, 5)
    px(s, "glass", 3, 4, 2, 3)
    px(s, "glass", 11, 4, 2, 3)
    # awning along the bottom of the facade
    px(s, color, 0, 11, T, 5)
    px(s, "white", 0, 11, T, 1)
    for x in range(1, T, 4):
        px(s, "white", x, 12, 2, 4)
    return s


def plant():
    s = _surf()
    px(s, "wood_dk", 5, 11, 6, 4)
    px(s, "wood", 5, 11, 6, 1)
    px(s, "green_dk", 4, 4, 8, 7)
    px(s, "green", 5, 3, 6, 6)
    px(s, "green", 3, 6, 3, 3)
    px(s, "green", 10, 6, 3, 3)
    return s


# --------------------------------------------------------------- people -------
def _person(shirt, hair="hair_brn", facing="down", apron=False):
    s = _surf()
    # shadow
    px(s, (0, 0, 0, 70), 4, 14, 8, 2)
    # legs
    px(s, "wood_dk", 5, 12, 2, 3)
    px(s, "wood_dk", 9, 12, 2, 3)
    # body / shirt
    px(s, shirt, 4, 7, 8, 6)
    px(s, shirt, 3, 8, 1, 3)   # arms
    px(s, shirt, 12, 8, 1, 3)
    if apron:
        px(s, "apron", 6, 8, 4, 5)
    # head
    px(s, "skin", 5, 2, 6, 6)
    px(s, "skin2", 5, 7, 6, 1)
    # hair
    px(s, hair, 5, 1, 6, 2)
    px(s, hair, 4, 2, 1, 3)
    px(s, hair, 11, 2, 1, 3)
    # face by facing
    if facing == "down":
        px(s, "black", 6, 4, 1, 1)
        px(s, "black", 9, 4, 1, 1)
    elif facing == "up":
        px(s, hair, 5, 2, 6, 4)
    elif facing == "left":
        px(s, "black", 6, 4, 1, 1)
        px(s, hair, 9, 2, 2, 4)
    elif facing == "right":
        px(s, "black", 9, 4, 1, 1)
        px(s, hair, 5, 2, 2, 4)
    return s


def person_set(shirt, hair="hair_brn", apron=False):
    return {f: _person(shirt, hair, f, apron)
            for f in ("down", "up", "left", "right")}


# --------------------------------------------------------------- fx -----------
def dirt_decal():
    s = _surf()
    for (x, y) in [(3, 4), (4, 5), (5, 4), (4, 6), (9, 9), (10, 10),
                   (11, 9), (10, 8), (7, 11), (12, 4)]:
        px(s, "dirt", x, y, 2, 2)
        px(s, "dirt2", x, y)
    return s


def _badge(s):
    """A small cream sign-plate with a dark border, for product icons."""
    px(s, "black", 2, 2, 13, 12)
    px(s, "cream", 3, 3, 11, 10)
    px(s, "white", 3, 3, 11, 1)


def product_icon(key, fallback="orange"):
    """A tiny 16x16 label icon showing roughly what a shelf sells."""
    s = _surf()
    _badge(s)
    if key == "bread":
        px(s, "wood", 4, 6, 9, 5)
        px(s, "wood_lt", 4, 6, 9, 2)
        px(s, "wood_dk", 6, 8, 1, 2)
        px(s, "wood_dk", 9, 8, 1, 2)
    elif key == "milk":
        px(s, "white", 5, 5, 7, 7)
        px(s, "metal", 6, 3, 5, 2)
        px(s, "shirt_blue", 5, 8, 7, 2)
    elif key == "eggs":
        px(s, "white", 4, 6, 4, 5)
        px(s, "white", 9, 6, 4, 5)
        px(s, "cream", 5, 7, 2, 3)
        px(s, "cream", 10, 7, 2, 3)
    elif key == "apples":
        px(s, "red", 4, 6, 9, 5)
        px(s, "red_dk", 4, 9, 9, 2)
        px(s, "green", 9, 3, 2, 2)
        px(s, "wood_dk", 8, 3, 1, 3)
    elif key == "bananas":
        px(s, "yellow", 4, 5, 2, 2)
        px(s, "yellow", 5, 6, 3, 2)
        px(s, "yellow", 7, 7, 3, 2)
        px(s, "yellow", 9, 6, 2, 3)
        px(s, "wood_dk", 4, 5, 1, 1)
    elif key == "lettuce":
        px(s, "green", 4, 5, 9, 6)
        px(s, "green_dk", 5, 7, 7, 2)
        px(s, "green", 6, 4, 5, 2)
    elif key == "chicken":
        px(s, "skin", 5, 5, 6, 4)
        px(s, "skin2", 5, 8, 6, 2)
        px(s, "white", 10, 9, 3, 2)
    elif key == "cereal":
        px(s, "orange", 4, 4, 9, 8)
        px(s, "red", 4, 4, 9, 2)
        px(s, "yellow", 6, 7, 5, 3)
    elif key == "pasta":
        px(s, "yellow", 4, 4, 9, 8)
        px(s, "red", 4, 4, 9, 2)
        px(s, "wood_lt", 6, 6, 1, 5)
        px(s, "wood_lt", 9, 6, 1, 5)
    elif key == "beans":
        px(s, "red_dk", 5, 4, 7, 8)
        px(s, "metal_lt", 5, 4, 7, 1)
        px(s, "cream", 6, 6, 5, 3)
    elif key == "soda":
        px(s, "purple", 6, 4, 4, 8)
        px(s, "purple", 7, 3, 2, 1)
        px(s, "white", 7, 6, 2, 3)
    elif key == "chips":
        px(s, "orange", 4, 4, 9, 9)
        px(s, "yellow", 4, 4, 9, 2)
        px(s, "red", 6, 7, 5, 3)
    elif key == "soap":
        px(s, "glass", 6, 5, 4, 7)
        px(s, "white", 7, 3, 2, 2)
        px(s, "metal_lt", 7, 7, 2, 2)
    elif key == "coffee":
        px(s, "wood_dk", 5, 5, 7, 7)
        px(s, "wood", 5, 5, 7, 2)
        px(s, "cream", 6, 7, 5, 3)
    else:
        px(s, fallback, 5, 5, 7, 7)
    return s


def coin():
    s = _surf()
    px(s, "ui_gold", 5, 5, 6, 6)
    px(s, "yellow", 6, 6, 4, 4)
    px(s, "white", 6, 6, 1, 1)
    return s


def sparkle():
    s = _surf()
    px(s, "white", 7, 4, 2, 8)
    px(s, "white", 4, 7, 8, 2)
    px(s, "yellow", 7, 5, 2, 6)
    px(s, "yellow", 5, 7, 6, 2)
    return s


# ------------------------------------------------------------- build all ------
def build_sprites():
    """Build and return a dict of all base (unscaled) sprites."""
    sp = {
        "floor":        floor_tile(),
        "floor_crack":  floor_tile(crack=True),
        "floor_new":    floor_tile(new=True),
        "wall":         wall_tile(),
        "door":         door_tile(),
        "counter":      counter(),
        "register":     register(),
        "plant":        plant(),
        "sidewalk":     sidewalk_tile(),
        "road":         road_tile(),
        "road_dash":    road_tile(dash=True),
        "storefront":   storefront("wall"),
        "crate0":       crate(level=0),
        "crate1":       crate(level=1),
        "crate2":       crate(level=2),
        "crate3":       crate(level=3),
        "dirt":         dirt_decal(),
        "coin":         coin(),
        "sparkle":      sparkle(),
    }
    # dirty floors at levels 1..3 (and on new floor)
    for lvl in (1, 2, 3):
        sp[f"floor_dirty{lvl}"] = floor_tile(dirty=lvl)
        sp[f"floor_new_dirty{lvl}"] = floor_tile(new=True, dirty=lvl)
    return sp
