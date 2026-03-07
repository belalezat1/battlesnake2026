import heapq
from collections import deque

MOVES = {
    "up":    (0,  1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1,  0),
}


def choose_move(data: dict) -> dict:
    me = data["you"]
    board = data["board"]
    width = board["width"]
    height = board["height"]

    head = (me["body"][0]["x"], me["body"][0]["y"])
    tail = (me["body"][-1]["x"], me["body"][-1]["y"])
    my_len = len(me["body"])
    health = me["health"]

    food = [(f["x"], f["y"]) for f in board["food"]]

    # --- Build obstacle set ---
    # Exclude tails: tails vacate each turn (unless snake just ate, which is rare
    # to track perfectly — this is a safe approximation).
    obstacles = set()
    enemy_heads = []  # (x, y, length)

    for snake in board["snakes"]:
        body = snake["body"]
        # Add every segment except the tail
        for seg in body[:-1]:
            obstacles.add((seg["x"], seg["y"]))
        if snake["id"] != me["id"]:
            h = body[0]
            enemy_heads.append((h["x"], h["y"], len(body)))

    # Squares where an equal-or-larger enemy head could move next turn
    danger_squares = set()
    kill_squares = set()  # squares where WE could win a head-on (enemy smaller)
    for ex, ey, elen in enemy_heads:
        for dx, dy in MOVES.values():
            sq = (ex + dx, ey + dy)
            if elen >= my_len:
                danger_squares.add(sq)
            else:
                kill_squares.add(sq)  # we'd win here

    # --- Helpers ---
    def in_bounds(x, y):
        return 0 <= x < width and 0 <= y < height

    def is_passable(x, y):
        return in_bounds(x, y) and (x, y) not in obstacles

    # --- Candidate moves ---
    all_safe = []
    for name, (dx, dy) in MOVES.items():
        nx, ny = head[0] + dx, head[1] + dy
        if is_passable(nx, ny):
            all_safe.append((name, nx, ny))

    if not all_safe:
        return {"move": "up"}  # no safe moves; pick anything

    # Prefer moves that avoid danger squares from equal/larger enemies
    non_dangerous = [(n, x, y) for n, x, y in all_safe if (x, y) not in danger_squares]
    candidates = non_dangerous if non_dangerous else all_safe

    # --- Flood fill ---
    def flood_fill(sx, sy):
        """Count reachable squares from (sx, sy), treating obstacles as walls."""
        visited = {(sx, sy)}
        queue = deque([(sx, sy)])
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in MOVES.values():
                p = (cx + dx, cy + dy)
                if is_passable(*p) and p not in visited:
                    visited.add(p)
                    queue.append(p)
        return len(visited)

    # --- A* pathfinding ---
    def astar(start, goal):
        """Return shortest path length from start to goal, or None if unreachable."""
        if start == goal:
            return 0
        h = lambda p: abs(p[0] - goal[0]) + abs(p[1] - goal[1])
        open_heap = [(h(start), 0, start)]
        g_score = {start: 0}
        while open_heap:
            _, cost, cur = heapq.heappop(open_heap)
            if cur == goal:
                return cost
            if cost > g_score.get(cur, float("inf")):
                continue
            for dx, dy in MOVES.values():
                nb = (cur[0] + dx, cur[1] + dy)
                if not is_passable(*nb):
                    continue
                ng = cost + 1
                if ng < g_score.get(nb, float("inf")):
                    g_score[nb] = ng
                    heapq.heappush(open_heap, (ng + h(nb), ng, nb))
        return None  # unreachable

    # --- Strategy ---
    # Need food if health is low or snake is small
    need_food = health < 40 or my_len < 5

    # Find nearest reachable food via A*
    target_food = None
    best_food_dist = float("inf")
    for f in food:
        dist = astar(head, f)
        if dist is not None and dist < best_food_dist:
            best_food_dist = dist
            target_food = f

    # --- Score each candidate move ---
    def score_move(nx, ny):
        space = flood_fill(nx, ny)

        # Primary: available space. Penalise heavily if space < our length (trap risk).
        if space < my_len:
            primary = space * 0.3
        else:
            primary = float(space)

        secondary = 0.0

        if need_food and target_food:
            # Move toward nearest food
            dist = abs(nx - target_food[0]) + abs(ny - target_food[1])
            secondary = (width + height - dist) * 0.5
        else:
            # Tail-chase: follow our own tail to stay mobile and hard to trap
            td = abs(nx - tail[0]) + abs(ny - tail[1])
            secondary = (width + height - td) * 0.3

        # Small bonus for moving into a kill square (head-on vs smaller snake)
        kill_bonus = 1.5 if (nx, ny) in kill_squares else 0.0

        return primary + secondary + kill_bonus

    best = max(candidates, key=lambda m: score_move(m[1], m[2]))
    return {"move": best[0]}
