"""
Moving things: the Player (you), Customers, and Staff. Customers and staff
share a simple BFS-pathing Walker base; the Player moves freely with collision.
"""
import random
from collections import deque
from settings import TILE, PRODUCT_BY_KEY, GRID_W, GRID_H, CASE_SIZE, LOW_SHELF


# ------------------------------------------------------------- pathfinding ---
def pathfind(world, start, goal):
    """BFS over walkable tiles. Returns list of tiles after start, or None."""
    if start == goal:
        return []
    seen = {start}
    q = deque([start])
    prev = {}
    while q:
        cur = q.popleft()
        for (dc, dr) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = (cur[0] + dc, cur[1] + dr)
            if nb in seen:
                continue
            if nb != goal and not world.walkable(*nb):
                continue
            if nb == goal and not (world.walkable(*nb) or world.is_floor(*nb)):
                continue
            seen.add(nb)
            prev[nb] = cur
            if nb == goal:
                path = [nb]
                while prev[path[-1]] != start:
                    path.append(prev[path[-1]])
                path.reverse()
                return path
            q.append(nb)
    return None


def tile_center(col, row):
    return col * TILE, row * TILE


# --------------------------------------------------------------- Walker ------
class Walker:
    SPEED = 42.0   # px/sec

    def __init__(self, col, row):
        self.x = float(col * TILE)
        self.y = float(row * TILE)
        self.path = []
        self.facing = "down"
        self.offset = (0, 0)   # extra pixel offset for queue positioning

    @property
    def col(self):
        return int(round(self.x / TILE))

    @property
    def row(self):
        return int(round(self.y / TILE))

    def at_tile(self, tile):
        return abs(self.x - tile[0] * TILE) < 1.5 and \
               abs(self.y - tile[1] * TILE) < 1.5

    def set_goal(self, world, goal):
        if goal is None:
            self.path = []
            return False
        p = pathfind(world, (self.col, self.row), goal)
        if p is None:
            self.path = []
            return False
        self.path = p
        return True

    def step(self, dt):
        """Advance along the path. Returns True when path just finished."""
        if not self.path:
            return False
        tx, ty = self.path[0][0] * TILE, self.path[0][1] * TILE
        dx, dy = tx - self.x, ty - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        elif dy != 0:
            self.facing = "down" if dy > 0 else "up"
        move = self.SPEED * dt
        if dist <= move or dist == 0:
            self.x, self.y = tx, ty
            self.path.pop(0)
            return not self.path
        self.x += move * dx / dist
        self.y += move * dy / dist
        return False


# --------------------------------------------------------------- Customer ----
class Customer:
    SPEED = 40.0

    def __init__(self, world, skin_idx):
        self.w = Walker(9, GRID_H - 1)   # spawn at the door
        self.w.SPEED = self.SPEED + random.uniform(-6, 10)
        self.skin_idx = skin_idx
        self.state = "enter"
        self.list = []            # product keys still to grab
        self.basket = []          # (key, retail) collected
        self.target_shelf = None
        self.checkout = None
        self.patience = random.uniform(16, 26)
        self.pay_progress = 0.0
        self.shoplifter = False
        self.done = False
        self.pick_timer = 0.0
        self.angry = False

    # -- helpers ----------------------------------------------------------
    def basket_value(self):
        return sum(v for _, v in self.basket)

    def _choose_list(self, game):
        avail = [s.product for s in game.world.shelves
                 if not s.broken and s.stock > 0]
        if not avail:
            return []
        random.shuffle(avail)
        n = random.randint(1, 3)
        return list(dict.fromkeys(avail))[:n]

    def _shelf_for(self, game, key):
        cands = [s for s in game.world.shelves
                 if s.product == key and not s.broken and s.stock > 0]
        if not cands:
            return None
        return random.choice(cands)

    def _nearest_checkout(self, game):
        return min(game.world.checkouts,
                   key=lambda ch: len(ch.queue) * 3 +
                   abs(ch.cust_tile[0] - self.w.col))

    # -- main update ------------------------------------------------------
    def update(self, game, dt):
        w = game.world
        if self.state == "enter":
            self.list = self._choose_list(game)
            self.shoplifter = (random.random() < game.shoplift_chance()
                               and self.basket is not None)
            if not self.list:
                self.state = "leave"
                self.w.set_goal(w, (9, GRID_H - 1))
            else:
                self._go_next_shelf(game)

        elif self.state == "to_shelf":
            if self.w.step(dt) or not self.w.path:
                if self.target_shelf and self.w.at_tile(self.target_shelf.access):
                    self.state = "pick"
                    self.pick_timer = random.uniform(0.4, 0.9)
                else:
                    self._go_next_shelf(game)

        elif self.state == "pick":
            self.pick_timer -= dt
            if self.pick_timer <= 0:
                sh = self.target_shelf
                if sh and sh.stock > 0:
                    take = min(sh.stock, random.randint(1, 2))
                    sh.stock -= take
                    p = PRODUCT_BY_KEY[sh.product]
                    for _ in range(take):
                        self.basket.append((sh.product, p["retail"]))
                if self.list:
                    self._go_next_shelf(game)
                else:
                    self._go_checkout(game)

        elif self.state == "to_checkout":
            if self.w.step(dt) or not self.w.path:
                if self.w.at_tile(self.checkout.cust_tile) or not self.w.path:
                    self.state = "queue"
                    if self not in self.checkout.queue:
                        self.checkout.queue.append(self)

        elif self.state == "queue":
            idx = self.checkout.queue.index(self) if self in self.checkout.queue else 0
            # line up behind the register
            self.w.offset = (0, idx * 6)
            self.patience -= dt
            if self.patience <= 0:
                self.angry = True
                game.on_customer_rage(self)
                self._leave_now(game)

        elif self.state == "steal":
            if self.w.step(dt) or not self.w.path:
                if self.w.at_tile((9, GRID_H - 1)) or not self.w.path:
                    game.on_shoplift(self)
                    self.done = True

        elif self.state == "leave":
            if self.w.step(dt) or not self.w.path:
                self.done = True

    def _go_next_shelf(self, game):
        if not self.list:
            self._go_checkout(game)
            return
        key = self.list.pop(0)
        sh = self._shelf_for(game, key)
        if sh is None:
            # shelf emptied out from under them
            game.on_empty_shelf()
            if self.list:
                self._go_next_shelf(game)
            else:
                self._go_checkout(game)
            return
        self.target_shelf = sh
        self.state = "to_shelf"
        if not self.w.set_goal(game.world, sh.access):
            self._go_checkout(game)

    def _go_checkout(self, game):
        if not self.basket:
            self.state = "leave"
            self.w.set_goal(game.world, (9, GRID_H - 1))
            return
        if self.shoplifter:
            self.state = "steal"
            self.w.set_goal(game.world, (9, GRID_H - 1))
            return
        self.checkout = self._nearest_checkout(game)
        self.state = "to_checkout"
        self.w.offset = (0, 0)
        self.w.set_goal(game.world, self.checkout.cust_tile)

    def _leave_now(self, game):
        if self.checkout and self in self.checkout.queue:
            self.checkout.queue.remove(self)
        self.w.offset = (0, 0)
        self.state = "leave"
        self.w.set_goal(game.world, (9, GRID_H - 1))

    def complete_sale(self, game):
        if self.checkout and self in self.checkout.queue:
            self.checkout.queue.remove(self)
        game.on_sale(self)
        self.w.offset = (0, 0)
        self.state = "leave"
        self.w.set_goal(game.world, (9, GRID_H - 1))


# --------------------------------------------------------------- Staff -------
class Staff:
    def __init__(self, role, col, row):
        self.role = role
        self.w = Walker(col, row)
        self.w.SPEED = 46.0
        self.task = "idle"
        self.target = None
        self.work_timer = 0.0
        self.carry = 0
        self.carry_key = None
        self.checkout = None        # cashiers: assigned checkout
        self.morale = random.uniform(70, 100)
        self.patrol_i = 0

    @property
    def at_station(self):
        return (self.checkout is not None and
                self.w.at_tile(self.checkout.staff_tile) and not self.w.path)

    def update(self, game, dt):
        getattr(self, f"_do_{self.role}")(game, dt)

    # -- cashier ----------------------------------------------------------
    def _do_cashier(self, game, dt):
        if self.checkout is None:
            return
        if not self.w.at_tile(self.checkout.staff_tile) and not self.w.path:
            self.w.set_goal(game.world, self.checkout.staff_tile)
        self.w.step(dt)
        self.w.facing = "down"

    # -- cleaner ----------------------------------------------------------
    def _do_cleaner(self, game, dt):
        w = game.world
        if self.task == "idle":
            if not w.dirty:
                self._wander(game, dt)
                return
            # nearest dirty tile
            tile = min(w.dirty.keys(),
                       key=lambda t: abs(t[0]-self.w.col)+abs(t[1]-self.w.row))
            self.target = tile
            self.task = "goto"
            if not self.w.set_goal(w, tile):
                self.task = "idle"
        elif self.task == "goto":
            if self.w.step(dt) or not self.w.path:
                if self.target in w.dirty and self.w.at_tile(self.target):
                    self.task = "clean"
                    self.work_timer = 1.0
                else:
                    self.task = "idle"
        elif self.task == "clean":
            self.work_timer -= dt
            if self.work_timer <= 0:
                if self.target in w.dirty:
                    del w.dirty[self.target]
                    game.cleanliness = min(100, game.cleanliness + 2)
                    game.popup(self.w.x, self.w.y, "spark")
                self.task = "idle"

    # -- stocker ----------------------------------------------------------
    def _do_stocker(self, game, dt):
        w = game.world
        if self.task == "idle":
            sh = self._find_low_shelf(game)
            if sh is None:
                self._wander(game, dt)
                return
            self.target = sh
            self.carry_key = sh.product
            self.task = "to_stock"
            pts = w.stockroom_points()
            pt = min(pts, key=lambda t: abs(t[0]-self.w.col)+abs(t[1]-self.w.row))
            self.w.set_goal(w, pt)
        elif self.task == "to_stock":
            if self.w.step(dt) or not self.w.path:
                avail = game.backstock.get(self.carry_key, 0)
                self.carry = min(CASE_SIZE, avail,
                                 self.target.capacity - self.target.stock)
                if self.carry <= 0:
                    self.task = "idle"
                    return
                self.task = "to_shelf"
                self.w.set_goal(w, self.target.access)
        elif self.task == "to_shelf":
            if self.w.step(dt) or not self.w.path:
                self.task = "fill"
                self.work_timer = 0.8
        elif self.task == "fill":
            self.work_timer -= dt
            if self.work_timer <= 0:
                sh = self.target
                give = min(self.carry, sh.capacity - sh.stock,
                           game.backstock.get(self.carry_key, 0))
                if give > 0 and not sh.broken:
                    sh.stock += give
                    game.backstock[self.carry_key] -= give
                    game.popup(self.w.x, self.w.y, "spark")
                self.carry = 0
                self.task = "idle"

    def _find_low_shelf(self, game):
        cands = [s for s in game.world.shelves
                 if not s.broken and s.stock < LOW_SHELF
                 and game.backstock.get(s.product, 0) > 0]
        if not cands:
            return None
        return min(cands, key=lambda s: s.stock)

    # -- guard ------------------------------------------------------------
    def _do_guard(self, game, dt):
        pts = [(9, 9), (6, 11), (13, 11), (10, 6)]
        if not self.w.path:
            self.patrol_i = (self.patrol_i + 1) % len(pts)
            self.w.set_goal(game.world, pts[self.patrol_i])
        self.w.step(dt)

    def _wander(self, game, dt):
        if not self.w.path:
            c = random.randint(2, GRID_W - 3)
            r = random.randint(2, GRID_H - 3)
            if game.world.walkable(c, r):
                self.w.set_goal(game.world, (c, r))
        self.w.step(dt)
