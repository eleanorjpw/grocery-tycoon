"""
Procedural pixel art, rendered at 3x detail (48px tiles) with light-from-top-left
shading -- a higher-fidelity, less-blocky look than the old 16px sprites.

Game logic still works in 16px tile units; the renderer scales positions by
SCALE, and every sprite here is authored at T = TILE * SCALE (= 48) pixels so it
blits 1:1 at the window's native resolution.
"""
import pygame
from settings import PAL, TILE, SCALE

T = TILE * SCALE          # sprite size in screen pixels (48)
U = SCALE                 # one "art unit" = SCALE screen px (keeps proportions)


def _c(c):
    return PAL[c] if isinstance(c, str) else c


def _surf():
    return pygame.Surface((T, T), pygame.SRCALPHA)


def px(s, c, x, y, w=1, h=1):
    pygame.draw.rect(s, _c(c), (x, y, w, h))


def shade(c, d):
    """Lighten (d>0) or darken (d<0) a palette colour."""
    r, g, b = _c(c)[:3]
    return (max(0, min(255, r + d)), max(0, min(255, g + d)),
            max(0, min(255, b + d)))


def outline(s, c="black"):
    """Draw a 1px dark outline around opaque pixels (cheap silhouette pop)."""
    col = _c(c)
    mask = pygame.mask.from_surface(s)
    out = mask.outline()
    if len(out) > 1:
        pygame.draw.lines(s, col, True, out, 1)


# ============================================================ floor / walls ==
def floor_tile(new=False, crack=False, dirty=0):
    s = _surf()
    a = "floor_new1" if new else "floor1"
    b = "floor_new2" if new else "floor2"
    s.fill(_c(a))
    # big checker tiles with a soft inner shadow + highlight bevel
    half = T // 2
    for (cx, cy) in ((0, 0), (half, half)):
        px(s, b, cx, cy, half, half)
    # grout lines
    px(s, shade(a, -26), 0, 0, T, U)
    px(s, shade(a, -26), 0, 0, U, T)
    px(s, shade(a, -16), 0, half, T, 1)
    px(s, shade(a, -16), half, 0, 1, T)
    # subtle highlight just under the top grout
    px(s, shade(a, 14), U, U, T - U, 1)
    if crack and not new:
        cc = shade("floor_crack", -10)
        pts = [(14, 6), (16, 10), (15, 15), (19, 19), (18, 24),
               (22, 28), (21, 33), (26, 38), (30, 42)]
        for i in range(len(pts) - 1):
            pygame.draw.line(s, _c(cc), pts[i], pts[i + 1], 1)
        pygame.draw.line(s, _c("floor_crack"),
                         (22, 28), (32, 26), 1)
    return s


def wall_tile():
    s = _surf()
    s.fill(_c("wall"))
    bh = T // 4                       # brick row height (12)
    for row in range(4):
        y = row * bh
        px(s, "wall_dk", 0, y, T, U)              # mortar line
        off = 0 if row % 2 == 0 else T // 2
        x = off
        while x < T:
            px(s, "wall_dk", x, y, U, bh)         # vertical mortar
            # brick face shading
            px(s, shade("wall", 16), x + U, y + U, T // 2 - U - 1, 2)
            px(s, shade("wall", -18), x + U, y + bh - 2, T // 2 - U - 1, 2)
            x += T // 2
    px(s, "wall_lt", 0, 0, T, U)                  # top catch-light
    return s


def door_tile():
    s = _surf()
    s.fill(_c("floor1"))
    px(s, "wood_dk", 0, 0, T, 6)
    px(s, "wood", 0, 0, T, 3)
    # welcome mat
    pygame.draw.rect(s, _c("green_dk"), (8, T - 16, T - 16, 12), border_radius=3)
    pygame.draw.rect(s, _c("green"), (11, T - 13, T - 22, 6), border_radius=2)
    px(s, shade("green", 30), 13, T - 12, T - 26, 1)
    return s


def sidewalk_tile():
    s = _surf()
    s.fill(_c("metal"))
    px(s, "metal_dk", 0, 0, T, U)
    px(s, "metal_dk", 0, 0, U, T)
    px(s, shade("metal", 18), U, U, T - U, 1)
    # paver seams (cross)
    px(s, "metal_dk", T // 2, 0, 1, T)
    px(s, "metal_dk", 0, T // 2, T, 1)
    # speckle
    for (x, y) in ((10, 30), (34, 12), (20, 40), (40, 28)):
        px(s, shade("metal", -14), x, y, 2, 2)
    return s


def road_tile(dash=False):
    s = _surf()
    s.fill(_c("dark"))
    px(s, "shadow", 0, 0, T, U)
    for (x, y) in ((8, 14), (33, 27), (18, 36), (39, 9), (24, 21), (12, 40)):
        px(s, "black", x, y, 2, 2)
    if dash:
        pygame.draw.rect(s, _c("yellow"), (T // 2 - 3, 10, 6, T - 20),
                         border_radius=2)
    return s


def storefront(color="red"):
    s = _surf()
    s.fill(_c("wall"))
    px(s, "wall_dk", 0, 0, T, T)
    px(s, "wall", 0, 0, T, T - 16)
    for y in range(0, T, 6):
        px(s, "wall_dk", 0, y, T, 1)
    # two windows with glass + reflection
    for wx in (6, 27):
        pygame.draw.rect(s, _c("metal_dk"), (wx, 8, 15, 18))
        pygame.draw.rect(s, _c("glass"), (wx + 2, 10, 11, 14))
        pygame.draw.line(s, _c("white"), (wx + 3, 11), (wx + 6, 22), 1)
        pygame.draw.line(s, _c(shade("glass", 30)), (wx + 8, 11), (wx + 10, 20), 1)
    # awning with scalloped edge
    pygame.draw.rect(s, _c(color), (0, T - 16, T, 11))
    px(s, "white", 0, T - 16, T, 2)
    for x in range(0, T, 8):
        pygame.draw.polygon(s, _c("white"),
                            [(x, T - 5), (x + 4, T - 5), (x + 2, T - 1)])
    px(s, shade(color, -30), 0, T - 7, T, 2)
    return s


# ================================================================ fixtures ==
def shelf(category_color="orange", level=3, broken=False):
    s = _surf()
    if broken:
        px(s, "wood_dk", 0, 4, T, T - 8)
        px(s, "shadow", 3, 7, T - 6, T - 14)
        for (x, y, w) in ((4, 10, T - 8), (6, 28, T - 12), (10, 38, T - 18)):
            px(s, "wood", x, y, w, 4)
        for (x, y) in ((9, 18), (22, 21), (31, 15), (37, 31), (15, 34)):
            px(s, "black", x, y, 3, 2)
        outline(s, shade("wood_dk", -30))
        return s
    # cabinet body with bevel
    pygame.draw.rect(s, _c("wood_dk"), (0, 0, T, T))
    pygame.draw.rect(s, _c("wood"), (2, 2, T - 4, T - 4))
    px(s, "wood_lt", 2, 2, T - 4, 2)
    px(s, shade("wood_dk", -16), 2, T - 4, T - 4, 2)
    # two shelf boards, each holding product "items"
    for (by, sy) in ((8, 6), (28, 26)):
        px(s, "wood_dk", 3, by + 14, T - 6, 3)          # board edge + shadow
        px(s, shade("wood_dk", -20), 3, by + 17, T - 6, 2)
        if level > 0:
            n = {1: 2, 2: 3, 3: 4}[level]
            gap = (T - 8) // n
            for i in range(n):
                ix = 5 + i * gap
                pygame.draw.rect(s, _c(category_color), (ix, sy + 2, gap - 3, 12))
                px(s, shade(category_color, 30), ix, sy + 2, gap - 3, 2)   # top light
                px(s, shade(category_color, -28), ix, sy + 12, gap - 3, 2)  # base
                px(s, "white", ix + 1, sy + 4, 1, 5)                       # highlight
    return s


def fridge(category_color="white", level=3):
    s = _surf()
    pygame.draw.rect(s, _c("metal_dk"), (0, 0, T, T))
    pygame.draw.rect(s, _c("metal"), (2, 2, T - 4, T - 4))
    pygame.draw.rect(s, _c("glass"), (5, 5, T - 10, T - 10))
    px(s, shade("glass", 30), 5, 5, T - 10, 2)
    # frosty diagonal reflection
    pygame.draw.line(s, _c("white"), (9, 8), (16, T - 9), 2)
    pygame.draw.line(s, _c(shade("glass", 24)), (18, 8), (24, T - 12), 1)
    if level > 0:
        n = {1: 2, 2: 3, 3: 3}[level]
        gap = (T - 14) // n
        for i in range(n):
            ix = 8 + i * gap
            pygame.draw.rect(s, _c(category_color), (ix, 12, gap - 4, 9))
            pygame.draw.rect(s, _c(category_color), (ix, 28, gap - 4, 9))
            px(s, shade(category_color, 28), ix, 12, gap - 4, 2)
            px(s, shade(category_color, 28), ix, 28, gap - 4, 2)
    px(s, "metal_lt", T - 7, 10, 3, T - 20)            # handle
    return s


def counter():
    s = _surf()
    pygame.draw.rect(s, _c("wood_dk"), (0, 0, T, T))
    pygame.draw.rect(s, _c("wood"), (0, 0, T, T - 12))
    px(s, "wood_lt", 0, 0, T, 3)
    px(s, shade("wood", -14), 0, T - 18, T, 2)
    px(s, "metal_dk", 0, T - 12, T, 12)
    px(s, "metal", 0, T - 12, T, 2)
    return s


def register():
    s = _surf()
    pygame.draw.rect(s, _c("wood"), (0, 0, T, T))
    px(s, "wood_lt", 0, 0, T, 3)
    pygame.draw.rect(s, _c("metal_dk"), (9, 8, 30, 28))
    pygame.draw.rect(s, _c("metal"), (12, 11, 24, 15))
    pygame.draw.rect(s, _c("glass"), (15, 14, 18, 9))     # screen
    px(s, "white", 16, 15, 6, 1)
    pygame.draw.rect(s, _c("metal_lt"), (12, 28, 24, 6))  # keypad
    for kx in range(14, 34, 4):
        px(s, "metal_dk", kx, 29, 2, 2)
        px(s, "metal_dk", kx, 32, 2, 1)
    px(s, "green", 34, 12, 2, 2)
    return s


def crate(category_color="brown", level=3):
    s = _surf()
    if level >= 1:
        pygame.draw.rect(s, _c(category_color), (9, 2, 9, 9))
        px(s, "white", 9, 2, 3, 1)
    if level >= 2:
        pygame.draw.rect(s, _c(category_color), (24, 2, 9, 9))
    if level >= 3:
        pygame.draw.rect(s, _c("orange"), (18, 0, 6, 8))
    pygame.draw.rect(s, _c("wood_dk"), (3, 6, T - 6, T - 9))
    pygame.draw.rect(s, _c("wood"), (6, 9, T - 12, T - 15))
    px(s, "wood_lt", 6, 9, T - 12, 2)
    # slats + corner posts
    px(s, "wood_dk", 6, 24, T - 12, 2)
    px(s, "wood_dk", 6, 36, T - 12, 2)
    px(s, "wood_dk", 6, 9, 3, T - 15)
    px(s, "wood_dk", T - 9, 9, 3, T - 15)
    if level == 0:
        px(s, "shadow", 9, 12, T - 18, 8)
    return s


def plant():
    s = _surf()
    pygame.draw.rect(s, _c("wood_dk"), (15, T - 14, 18, 12), border_radius=2)
    px(s, "wood", 15, T - 14, 18, 3)
    px(s, shade("wood_dk", -16), 15, T - 4, 18, 2)
    for (cx, cy, r, col) in ((24, 18, 11, "green_dk"), (24, 15, 9, "green"),
                             (16, 22, 6, "green_dk"), (32, 22, 6, "green"),
                             (24, 12, 5, shade("green", 26))):
        pygame.draw.circle(s, _c(col), (cx, cy), r)
    return s


# ================================================================== people ==
def _person(shirt, hair="hair_brn", facing="down", apron=False):
    s = _surf()
    pygame.draw.ellipse(s, (0, 0, 0, 80), (12, T - 7, 24, 6))   # shadow
    # legs
    px(s, "wood_dk", 16, 36, 6, 9)
    px(s, "wood_dk", 26, 36, 6, 9)
    px(s, shade("wood_dk", -18), 16, 43, 6, 2)
    px(s, shade("wood_dk", -18), 26, 43, 6, 2)
    # torso
    pygame.draw.rect(s, _c(shirt), (12, 20, 24, 18), border_radius=3)
    px(s, shade(shirt, 24), 13, 21, 22, 2)
    px(s, shade(shirt, -26), 13, 35, 22, 2)
    px(s, shirt, 9, 22, 4, 10)        # arms
    px(s, shirt, 35, 22, 4, 10)
    px(s, "skin", 9, 30, 4, 4)        # hands
    px(s, "skin", 35, 30, 4, 4)
    if apron:
        pygame.draw.rect(s, _c("apron"), (18, 22, 12, 15), border_radius=2)
        px(s, shade("apron", 26), 19, 23, 10, 1)
    # head
    pygame.draw.rect(s, _c("skin"), (15, 6, 18, 17), border_radius=5)
    px(s, "skin2", 15, 20, 18, 3)
    px(s, shade("skin", 22), 16, 7, 10, 2)
    # hair
    px(s, hair, 14, 4, 20, 6)
    px(s, hair, 13, 6, 3, 9)
    px(s, hair, 32, 6, 3, 9)
    if facing == "down":
        for ex in (19, 27):
            px(s, "white", ex, 12, 4, 4)
            px(s, "black", ex + 1, 13, 2, 2)
        px(s, "skin2", 23, 16, 2, 2)              # nose
        px(s, shade("red", 10), 21, 19, 6, 1)     # smile
    elif facing == "up":
        px(s, hair, 14, 4, 20, 11)
    elif facing == "left":
        px(s, "white", 17, 12, 4, 4)
        px(s, "black", 17, 13, 2, 2)
        px(s, hair, 27, 6, 7, 10)
    elif facing == "right":
        px(s, "white", 27, 12, 4, 4)
        px(s, "black", 28, 13, 2, 2)
        px(s, hair, 14, 6, 7, 10)
    outline(s, shade(hair, -40))
    return s


def person_set(shirt, hair="hair_brn", apron=False):
    return {f: _person(shirt, hair, f, apron)
            for f in ("down", "up", "left", "right")}


# ====================================================================== fx ==
def dirt_decal():
    s = _surf()
    for (x, y, r) in ((12, 14, 4), (15, 18, 3), (30, 30, 4), (33, 27, 3),
                      (22, 34, 3), (36, 13, 3), (9, 30, 3)):
        pygame.draw.circle(s, _c("dirt"), (x, y), r)
        pygame.draw.circle(s, _c("dirt2"), (x, y), max(1, r - 2))
    return s


def coin():
    s = _surf()
    pygame.draw.circle(s, _c("wood_dk"), (24, 24), 11)
    pygame.draw.circle(s, _c("ui_gold"), (24, 24), 10)
    pygame.draw.circle(s, _c("yellow"), (24, 24), 6)
    px(s, "white", 20, 18, 3, 3)
    px(s, shade("ui_gold", -40), 28, 30, 4, 3)
    return s


def sparkle():
    s = _surf()
    pygame.draw.polygon(s, _c("white"),
                        [(24, 8), (27, 21), (40, 24), (27, 27),
                         (24, 40), (21, 27), (8, 24), (21, 21)])
    pygame.draw.polygon(s, _c("yellow"),
                        [(24, 14), (26, 22), (34, 24), (26, 26),
                         (24, 34), (22, 26), (14, 24), (22, 22)])
    return s


# ============================================================ product icons ==
def _badge(s):
    pygame.draw.rect(s, _c("black"), (5, 5, T - 11, T - 11), border_radius=4)
    pygame.draw.rect(s, _c("cream"), (7, 7, T - 15, T - 15), border_radius=3)
    px(s, "white", 8, 8, T - 17, 2)


def product_icon(key, fallback="orange"):
    s = _surf()
    _badge(s)
    cx, cy = 24, 25
    if key == "bread":
        pygame.draw.ellipse(s, _c("wood"), (12, 18, 24, 16))
        pygame.draw.ellipse(s, _c("wood_lt"), (13, 17, 22, 8))
        for x in (18, 24, 30):
            px(s, "wood_dk", x, 22, 1, 7)
    elif key == "milk":
        pygame.draw.rect(s, _c("white"), (16, 14, 16, 22), border_radius=2)
        pygame.draw.polygon(s, _c("white"), [(16, 14), (32, 14), (28, 9), (20, 9)])
        pygame.draw.rect(s, _c("shirt_blue"), (16, 26, 16, 6))
    elif key == "eggs":
        for ex in (17, 27):
            pygame.draw.ellipse(s, _c("white"), (ex, 16, 9, 13))
            pygame.draw.ellipse(s, _c("cream"), (ex + 2, 22, 5, 5))
    elif key == "apples":
        pygame.draw.circle(s, _c("red"), (cx, 27), 10)
        pygame.draw.circle(s, _c(shade("red", 36)), (20, 23), 3)
        px(s, "wood_dk", 23, 13, 2, 5)
        pygame.draw.circle(s, _c("green"), (28, 14), 3)
    elif key == "bananas":
        pygame.draw.arc(s, _c("yellow"), (12, 12, 24, 24), 3.6, 5.8, 6)
        px(s, "wood_dk", 14, 18, 3, 3)
    elif key == "lettuce":
        pygame.draw.circle(s, _c("green"), (cx, 26), 11)
        pygame.draw.circle(s, _c("green_dk"), (cx, 28), 7)
        pygame.draw.circle(s, _c(shade("green", 26)), (20, 22), 3)
    elif key == "chicken":
        pygame.draw.circle(s, _c("skin"), (22, 24), 9)
        pygame.draw.rect(s, _c("white"), (29, 28, 8, 5), border_radius=2)
        px(s, "skin2", 18, 28, 8, 3)
    elif key == "cereal":
        pygame.draw.rect(s, _c("orange"), (13, 13, 22, 24), border_radius=2)
        px(s, "red", 13, 13, 22, 5)
        pygame.draw.circle(s, _c("yellow"), (24, 26), 5)
    elif key == "pasta":
        pygame.draw.rect(s, _c("yellow"), (14, 12, 20, 25), border_radius=2)
        px(s, "red", 14, 12, 20, 5)
        for x in (19, 24, 29):
            px(s, "wood_lt", x, 19, 2, 14)
    elif key == "beans":
        pygame.draw.rect(s, _c("red_dk"), (15, 13, 18, 22), border_radius=3)
        px(s, "metal_lt", 15, 13, 18, 3)
        pygame.draw.rect(s, _c("cream"), (18, 19, 12, 9))
    elif key == "soda":
        pygame.draw.rect(s, _c("purple"), (18, 12, 12, 25), border_radius=4)
        pygame.draw.rect(s, _c("purple"), (21, 8, 6, 5))
        pygame.draw.rect(s, _c("white"), (20, 20, 8, 8))
    elif key == "chips":
        pygame.draw.rect(s, _c("orange"), (13, 12, 22, 26), border_radius=3)
        px(s, "yellow", 13, 12, 22, 6)
        pygame.draw.circle(s, _c("red"), (24, 26), 6)
    elif key == "soap":
        pygame.draw.rect(s, _c("glass"), (18, 14, 12, 22), border_radius=3)
        pygame.draw.rect(s, _c("white"), (21, 9, 6, 6), border_radius=2)
        pygame.draw.circle(s, _c("white"), (24, 24), 3)
    elif key == "coffee":
        pygame.draw.rect(s, _c("wood_dk"), (15, 13, 18, 23), border_radius=3)
        px(s, "wood", 15, 13, 18, 5)
        pygame.draw.circle(s, _c("cream"), (24, 26), 5)
    else:
        pygame.draw.circle(s, _c(fallback), (cx, cy), 9)
    return s


# ================================================================ build all ==
def build_sprites():
    sp = {
        "floor":       floor_tile(),
        "floor_crack": floor_tile(crack=True),
        "floor_new":   floor_tile(new=True),
        "wall":        wall_tile(),
        "door":        door_tile(),
        "counter":     counter(),
        "register":    register(),
        "plant":       plant(),
        "sidewalk":    sidewalk_tile(),
        "road":        road_tile(),
        "road_dash":   road_tile(dash=True),
        "storefront":  storefront("wall"),
        "dirt":        dirt_decal(),
        "coin":        coin(),
        "sparkle":     sparkle(),
    }
    for lvl in (0, 1, 2, 3):
        sp[f"crate{lvl}"] = crate(level=lvl)
    return sp
