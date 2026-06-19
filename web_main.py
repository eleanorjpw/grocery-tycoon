"""
Browser entry point for Grocery Tycoon (compiled to WebAssembly with pygbag).

In the browser there are no real sockets, so this build is SINGLE-PLAYER only;
multiplayer lives in the downloadable desktop version. pygbag requires an async
main loop that yields to the browser every frame via `await asyncio.sleep(0)`.
"""
import asyncio
import pygame
import game


async def main():
    g = game.Game()
    while True:
        dt = min(g.clock.tick(60) / 1000.0, 0.05)
        g.handle_events()      # quit is ignored in the browser; keep looping
        g._net_tick(dt)        # no-op in single-player / web
        g.update(dt)
        g.draw()
        await asyncio.sleep(0)


asyncio.run(main())
