"""Strategy engine: game phases, food targeting, move scoring."""

from __future__ import annotations
from game import Coord, GameState
from board_utils import (
    build_obstacle_set,
    build_hazard_set,
    get_danger_squares,
    get_kill_squares,
    get_safe_moves,
)
from pathfinding import astar, flood_fill, flood_fill_time_aware, voronoi


# --- Game phase detection ---

def detect_phase(state: GameState) -> str:
    """Detect current game phase based on snake state."""
    me = state.me
    num_enemies = len(state.enemies)

    if me.health < 15:
        return "desperation"
    if me.length < 6:
        return "early"
    if num_enemies <= 1:
        return "late"
    return "mid"


# --- Food targeting ---

def find_best_food(
    state: GameState,
    obstacles: set[Coord],
    hazards: set[Coord],
) -> tuple[Coord | None, int | None, list[Coord]]:
    """Find the best food target considering distance and competition.

    Returns (food_coord, distance, path) or (None, None, []).
    """
    w, h = state.board.width, state.board.height
    head = state.me.head
    my_len = state.me.length
    game_mode = state.game_mode

    hazard_cost = 15.0 if game_mode == "royale" else 1.0

    best_food: Coord | None = None
    best_score = float("-inf")
    best_dist: int | None = None
    best_path: list[Coord] = []

    for food in state.board.food:
        dist, path = astar(head, food, obstacles, w, h, hazards, hazard_cost)
        if dist is None:
            continue

        # Check if any enemy is closer or equidistant
        closest_enemy = None
        for enemy in state.enemies:
            e_dist = enemy.head.manhattan(food)
            if e_dist <= dist:
                closest_enemy = enemy
                break

        # Score this food
        score = -dist  # Closer is better

        if closest_enemy is not None:
            if closest_enemy.length >= my_len:
                score -= 20  # Heavily penalize if enemy is bigger
            else:
                score += 5  # Bonus: we can win the head-on

        # Bonus for food that makes us larger than nearest enemy
        if state.enemies:
            smallest_gap = min(e.length - my_len for e in state.enemies)
            if smallest_gap >= 0:
                score += 10  # We need to grow

        if score > best_score:
            best_score = score
            best_food = food
            best_dist = dist
            best_path = path

    return best_food, best_dist, best_path


# --- Move scoring ---

def score_move(
    move_name: str,
    pos: Coord,
    state: GameState,
    obstacles: set[Coord],
    hazards: set[Coord],
    danger_squares: set[Coord],
    kill_squares: set[Coord],
    voronoi_counts: dict[str, int],
    target_food: Coord | None,
    food_dist: int | None,
    phase: str,
) -> float:
    """Score a candidate move with weighted combination of factors."""
    w, h = state.board.width, state.board.height
    me = state.me
    total_cells = w * h

    # --- Space score (flood fill) ---
    snake_bodies = [s.body for s in state.board.snakes]
    space = flood_fill_time_aware(pos, obstacles, snake_bodies, w, h)

    if space < me.length:
        space_score = space * 0.3  # Trap risk
    else:
        space_score = float(space)

    # --- Territory score (Voronoi) ---
    my_territory = voronoi_counts.get(me.id, 0)
    max_enemy_territory = max(
        (voronoi_counts.get(e.id, 0) for e in state.enemies), default=0
    )
    territory_score = (my_territory - max_enemy_territory) * 0.5

    # --- Food score ---
    food_score = 0.0
    # Aggressive food strategy: always pursue food, grow as large as possible
    # Bigger snake = harder to kill, more head-on wins, more board control
    if me.health < 20:
        food_urgency = 3.0  # Critical — will die soon
    elif me.health < 50:
        food_urgency = 2.0  # Hungry — prioritize food
    elif me.health < 80:
        food_urgency = 1.5  # Proactive — keep health topped up
    else:
        food_urgency = 1.0  # Full health — still actively seek food to grow

    if state.game_mode == "constrictor":
        food_urgency = 0.0  # No food in constrictor

    if target_food is not None:
        dist_to_food = pos.manhattan(target_food)
        food_score = (w + h - dist_to_food) * food_urgency
        # Bonus: we're stepping onto the food
        if dist_to_food == 0:
            food_score += 10.0

    # --- Aggression score ---
    aggression_score = 0.0
    if pos in kill_squares:
        aggression_score += 3.0
    # Cutoff bonus: if moving here reduces enemy territory significantly
    if phase == "late" and state.enemies:
        aggression_score += territory_score * 0.3

    # --- Safety score ---
    safety_score = 0.0
    if pos in danger_squares:
        safety_score -= 10.0
    if pos in hazards:
        safety_score -= 5.0 if state.game_mode == "royale" else 1.0

    # --- Center score (slight bias for optionality) ---
    center_x, center_y = w / 2.0, h / 2.0
    dist_to_center = abs(pos.x - center_x) + abs(pos.y - center_y)
    max_center_dist = center_x + center_y
    center_score = (max_center_dist - dist_to_center) * 0.15

    # --- Tail chase (only as fallback when no food target) ---
    tail_score = 0.0
    if target_food is None and state.game_mode != "constrictor":
        tail_dist = pos.manhattan(me.tail)
        tail_score = (w + h - tail_dist) * 0.3

    # --- Phase-specific weighting ---
    if phase == "desperation":
        # Override: maximize food pursuit
        return food_score * 5.0 + space_score * 0.5 + safety_score
    elif phase == "early":
        return space_score + food_score * 2.0 + safety_score * 2.0 + center_score
    elif phase == "late":
        return (
            space_score
            + food_score  # Must still eat to survive
            + territory_score * 2.0
            + aggression_score * 2.0
            + safety_score
            + tail_score
        )
    else:  # mid
        return (
            space_score
            + food_score
            + territory_score
            + aggression_score
            + safety_score
            + center_score
            + tail_score
        )


def evaluate_moves(
    state: GameState,
) -> list[tuple[str, Coord, float]]:
    """Evaluate all safe moves and return sorted by score (best first).

    Returns list of (move_name, position, score).
    """
    obstacles = build_obstacle_set(state)
    hazards = build_hazard_set(state)
    danger = get_danger_squares(state)
    kills = get_kill_squares(state)
    safe_moves = get_safe_moves(state, obstacles)

    if not safe_moves:
        return [("up", state.me.head + Coord(0, 1), -999.0)]

    # Prefer non-dangerous moves, but fall back to all safe moves
    non_dangerous = [(n, p) for n, p in safe_moves if p not in danger]
    candidates = non_dangerous if non_dangerous else safe_moves

    # Compute Voronoi territory
    v_counts = voronoi(state, obstacles)

    # Detect game phase
    phase = detect_phase(state)

    # Find best food target
    target_food, food_dist, _ = find_best_food(state, obstacles, hazards)

    # Score each move
    scored: list[tuple[str, Coord, float]] = []
    for name, pos in candidates:
        s = score_move(
            name, pos, state, obstacles, hazards,
            danger, kills, v_counts, target_food, food_dist, phase,
        )
        scored.append((name, pos, s))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored
