"""Headless multiplayer test: host + client over the loopback socket."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from game import Game, PHASE_PLAY


def pump(host, client, n, dt=0.016):
    for _ in range(n):
        host._net_tick(dt)
        host.update(dt)
        client._net_tick(dt)
        client.update(dt)
        host.draw()
        client.draw()


host = Game()
host.start_host()
host.phase = PHASE_PLAY          # skip the lobby for the test

client = Game()
client.start_join("127.0.0.1")

# let them connect + sync
pump(host, client, 600)

assert client.local_pid != 0, "client never got a player id"
assert len(host.players) >= 2, f"host has {len(host.players)} players"
assert len(client.players) >= 2, f"client sees {len(client.players)} players"
assert abs(client.money - host.money) < 5, "money not synced"

# client issues a management command -> host applies it (shared budget)
m0 = host.money
client.order_case("bread")
pump(host, client, 200)
assert host.money < m0, "client's order did not apply on the host"

# client moves right -> host (authoritative) moves that player
cid = client.local_pid
x0 = host.players[cid].x
client.client.send({"t": "input", "dx": 1, "dy": 0})
pump(host, client, 150)
assert host.players[cid].x > x0 + 4, "client movement did not drive host"

# the client sees the moved position too
pump(host, client, 60)
assert abs(client.players[cid].x - host.players[cid].x) < 12, "position desync"

# scene + shop ownership sync over the wire
host.upgrades.add("see_world")
host.players[cid].scene = "street"
host.street.shops[0].owned = True
pump(host, client, 60)
assert client.players[cid].scene == "street", "player scene not synced"
assert client.street.shops[0].owned, "shop ownership not synced"

print(f"OK host_players={len(host.players)} client_players={len(client.players)} "
      f"host_money={host.money:.0f} client_money={client.money:.0f} "
      f"moved_to_x={host.players[cid].x:.0f} scene_sync=ok shop_sync=ok")

host._teardown_net()
client._teardown_net()
pygame.quit()
