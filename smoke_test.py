"""Headless smoke test: drive the single-player sim without a window/input."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
random.seed(7)

import pygame
from game import Game, PHASE_PLAY, PHASE_SUMMARY, PHASE_TITLE
from settings import UPGRADES, STAFF_TYPES, PRODUCTS

g = Game()
# exercise title + menu draw paths
g.draw()                      # title
g.start_single()
g.phase = PHASE_PLAY

for role in STAFF_TYPES:
    g.money += 500
    g.hire(role)
for p in PRODUCTS[:6]:
    g.money += 200
    g.order_case(p[0])
g.money += 6000
for uid, *_ in UPGRADES:
    g.buy_upgrade(uid)
for _ in range(6):
    g.buy_shelf()             # buy extra shelves

frames = 0
days_seen = set()
for _ in range(40000):
    frames += 1
    g.draw()
    g.update(0.05)
    if g.phase == PHASE_SUMMARY:
        days_seen.add(g.day)
        g._start_new_day()
    if g.day >= 5:
        break

# player interaction: repair a broken shelf
g.phase = PHASE_PLAY
broken = [s for s in g.world.shelves if s.broken]
if broken:
    sh = broken[0]
    g.me.x = sh.access[0] * 16.0
    g.me.y = sh.access[1] * 16.0
    g.me.facing = "up" if sh.access[1] > sh.row else "down"
    g.money += 200
    before = g.money
    g.interact(g.me)
    assert g.money <= before, "repair should cost money"

# draw the management menu
g.menu_open = True
for tab in range(4):
    g.menu_tab = tab
    g.draw()
g.menu_open = False

# "See the World": buy upgrade, walk out, buy a shop, come back
g.upgrades.add("see_world")
g.me.x, g.me.y = 9 * 16.0, 12 * 16.0          # step onto the door
g.update(0.05)
assert g.me.scene == "street", "did not go outside"
g.draw()                                       # render the street + signs
shop = g.street.shops[0]
g.me.x, g.me.y = shop.door[0] * 16.0, 10 * 16.0  # stand in front of the door
g.me.facing = "up"
g.money += shop.price + 100
g.interact(g.me)
assert shop.owned, "shop purchase failed"
# go back inside via your store's door
g.me.x, g.me.y = g.street.store_col * 16.0, 10 * 16.0
g.me.facing = "up"
g.interact(g.me)
assert g.me.scene == "store", "did not return inside"

# pause stops the clock
g.paused = True
t0 = g.game_clock
for _ in range(20):
    g.update(0.05)
assert g.game_clock == t0, "pause did not freeze the clock"
g.paused = False

print(f"OK frames={frames} day={g.day} money={g.money:.0f} "
      f"shelves={len(g.world.shelves)} staff={len(g.staff)} "
      f"days_closed={sorted(days_seen)} rep={g.reputation:.0f}")
pygame.quit()
