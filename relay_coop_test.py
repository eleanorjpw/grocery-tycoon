"""Headless relay co-op test: host + client Game instances over the live relay."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from game import Game, PHASE_PLAY


def pump(host, client, n, dt=0.016):
    for _ in range(n):
        host._net_tick(dt); host.update(dt); host.draw()
        client._net_tick(dt); client.update(dt); client.draw()


host = Game()
host.start_host()
host.phase = PHASE_PLAY            # skip the lobby for the test
code = host.room_code
print("room code:", code)

client = Game()
client.start_join(code)

# give the relay time to connect both ends (network RTT)
pump(host, client, 1200)

print("host players:", len(host.players), "client players:", len(client.players))
print("client phase==PLAY:", client.phase == PHASE_PLAY)
print("money host/client:", round(host.money), round(client.money))
assert len(host.players) >= 2, "client never joined the host"
assert client.phase == PHASE_PLAY, "client never received a snapshot"
assert abs(client.money - host.money) < 5, "money not synced"

# client orders stock -> host applies (shared budget)
m0 = host.money
client.order_case("bread")
pump(host, client, 300)
assert host.money < m0, "client command did not reach host"

# client moves -> host authoritative position changes -> client sees it
cid = client.local_pid
x0 = host.players[cid].x
client.client.send({"t": "input", "dx": 1, "dy": 0})
pump(host, client, 250)
assert host.players[cid].x > x0 + 3, "client movement did not drive host"
pump(host, client, 120)
print("moved x host:", round(host.players[cid].x), "client sees:",
      round(client.players[cid].x))
assert abs(client.players[cid].x - host.players[cid].x) < 16, "position desync"

print("RELAY CO-OP OK")
host._teardown_net(); client._teardown_net()
pygame.quit()
