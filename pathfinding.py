"""Pathfinding algorithms: A*, flood fill, and Voronoi territory."""

from __future__ import annotations
import heapq
from collections import deque
from game import Coord, GameState, ALL_MOVES
from board_utils import in_bounds


def astar(
    start: Coord,
    goal: Coord,
    obstacles: set[Coord],
    width: int,
    height: int,
    hazards: set[Coord] | None = None,
    hazard_cost: float = 15.0,
) -> tuple[int | None, list[Coord]]:
    """A* pathfinding with optional hazard weighting.

    Returns (distance, path) or (None, []) if unreachable.
    Path includes start and goal.
    """
    if start == goal:
        return 0, [start]

    def h(p: Coord) -> int:
        return abs(p.x - goal.x) + abs(p.y - goal.y)

    hz = hazards or set()
    # (f_score, g_score, coord)
    open_heap: list[tuple[float, float, int, Coord]] = [(h(start), 0.0, 0, start)]
    g_score: dict[Coord, float] = {start: 0.0}
    came_from: dict[Coord, Coord] = {}
    counter = 1

    while open_heap:
        _, cost, _, cur = heapq.heappop(open_heap)
        if cur == goal:
            # Reconstruct path
            path = [cur]
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur)
            path.reverse()
            return int(cost), path

        if cost > g_score.get(cur, float("inf")):
            continue

        for _, delta in ALL_MOVES:
            nb = cur + delta
            if not in_bounds(nb, width, height) or nb in obstacles:
                continue
            move_cost = hazard_cost if nb in hz else 1.0
            ng = cost + move_cost
            if ng < g_score.get(nb, float("inf")):
                g_score[nb] = ng
                came_from[nb] = cur
                heapq.heappush(open_heap, (ng + h(nb), ng, counter, nb))
                counter += 1

    return None, []


def flood_fill(
    start: Coord,
    obstacles: set[Coord],
    width: int,
    height: int,
) -> tuple[int, set[Coord]]:
    """BFS flood fill from start. Returns (count, reachable_cells)."""
    visited: set[Coord] = {start}
    queue: deque[Coord] = deque([start])

    while queue:
        cur = queue.popleft()
        for _, delta in ALL_MOVES:
            nb = cur + delta
            if in_bounds(nb, width, height) and nb not in obstacles and nb not in visited:
                visited.add(nb)
                queue.append(nb)

    return len(visited), visited


def flood_fill_time_aware(
    start: Coord,
    obstacles: set[Coord],
    snake_bodies: list[list[Coord]],
    width: int,
    height: int,
    max_depth: int = 20,
) -> int:
    """Time-aware flood fill that accounts for tails vacating over time.

    As BFS expands at depth d, body segments that are <= d steps from
    the tail are treated as free (they'll have moved by then).
    """
    # Precompute when each body cell becomes free
    # cell -> earliest turn it becomes passable
    free_at: dict[Coord, int] = {}
    for body in snake_bodies:
        body_len = len(body)
        for i, seg in enumerate(body):
            # Segment i is (body_len - 1 - i) steps from tail
            # It becomes free after that many turns
            turns_until_free = body_len - 1 - i
            if seg in free_at:
                free_at[seg] = min(free_at[seg], turns_until_free)
            else:
                free_at[seg] = turns_until_free

    visited: set[Coord] = {start}
    queue: deque[tuple[Coord, int]] = deque([(start, 0)])
    count = 1

    while queue:
        cur, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for _, delta in ALL_MOVES:
            nb = cur + delta
            if nb in visited or not in_bounds(nb, width, height):
                continue
            next_depth = depth + 1
            # Check if cell is passable at this time step
            if nb in obstacles:
                # Will it be free by the time we get there?
                if nb in free_at and free_at[nb] <= next_depth:
                    pass  # It'll be free
                else:
                    continue
            visited.add(nb)
            queue.append((nb, next_depth))
            count += 1

    return count


def voronoi(
    state: GameState,
    obstacles: set[Coord],
) -> dict[str, int]:
    """Simultaneous BFS from all snake heads.

    Returns dict mapping snake_id -> number of cells they control
    (cells closer to them than any other snake).
    """
    w, h = state.board.width, state.board.height
    # (coord) -> (distance, snake_id)
    owner: dict[Coord, tuple[int, str]] = {}
    contested: set[Coord] = set()
    queue: deque[tuple[Coord, int, str]] = deque()

    for snake in state.board.snakes:
        head = snake.head
        owner[head] = (0, snake.id)
        queue.append((head, 0, snake.id))

    while queue:
        cur, dist, sid = queue.popleft()

        # Check if we still own this cell
        if cur in contested:
            continue
        if cur in owner and owner[cur] != (dist, sid):
            continue

        for _, delta in ALL_MOVES:
            nb = cur + delta
            if not in_bounds(nb, w, h) or nb in obstacles or nb in contested:
                continue
            nd = dist + 1
            if nb not in owner:
                owner[nb] = (nd, sid)
                queue.append((nb, nd, sid))
            elif owner[nb][0] == nd and owner[nb][1] != sid:
                # Equidistant from two snakes — contested
                contested.add(nb)
                del owner[nb]

    # Count cells per snake
    counts: dict[str, int] = {}
    for _, (_, sid) in owner.items():
        counts[sid] = counts.get(sid, 0) + 1

    return counts
