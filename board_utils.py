"""Board utility functions for BattleSnake."""

from __future__ import annotations
from game import Coord, GameState, Snake, ALL_MOVES


def in_bounds(c: Coord, width: int, height: int) -> bool:
    return 0 <= c.x < width and 0 <= c.y < height


def neighbors(c: Coord) -> list[tuple[str, Coord]]:
    """Return all 4 neighbors as (move_name, coord) pairs."""
    return [(name, c + delta) for name, delta in ALL_MOVES]


def build_obstacle_set(state: GameState) -> set[Coord]:
    """Build set of impassable cells from all snake bodies.

    Tails are excluded UNLESS the snake just ate (health==100).
    """
    obstacles: set[Coord] = set()
    for snake in state.board.snakes:
        body = snake.body
        # Add all segments except tail
        for seg in body[:-1]:
            obstacles.add(seg)
        # If snake just ate, tail stays
        if snake.just_ate:
            obstacles.add(body[-1])
    return obstacles


def build_hazard_set(state: GameState) -> set[Coord]:
    return set(state.board.hazards)


def get_danger_squares(state: GameState) -> set[Coord]:
    """Squares where equal-or-larger enemy heads could move next turn."""
    danger: set[Coord] = set()
    my_len = state.me.length
    w, h = state.board.width, state.board.height
    for enemy in state.enemies:
        if enemy.length >= my_len:
            for _, delta in ALL_MOVES:
                sq = enemy.head + delta
                if in_bounds(sq, w, h):
                    danger.add(sq)
    return danger


def get_kill_squares(state: GameState) -> set[Coord]:
    """Squares where we'd win a head-on collision (enemy is shorter)."""
    kills: set[Coord] = set()
    my_len = state.me.length
    w, h = state.board.width, state.board.height
    for enemy in state.enemies:
        if enemy.length < my_len:
            for _, delta in ALL_MOVES:
                sq = enemy.head + delta
                if in_bounds(sq, w, h):
                    kills.add(sq)
    return kills


def get_safe_moves(
    state: GameState,
    obstacles: set[Coord],
) -> list[tuple[str, Coord]]:
    """Return moves that don't hit walls or obstacles."""
    head = state.me.head
    w, h = state.board.width, state.board.height
    safe = []
    for name, delta in ALL_MOVES:
        pos = head + delta
        if in_bounds(pos, w, h) and pos not in obstacles:
            safe.append((name, pos))
    return safe
