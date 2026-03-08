"""Enemy move prediction and Monte Carlo Tree Search (MCTS)."""

from __future__ import annotations
import random
import time
from copy import deepcopy
from game import Coord, GameState, Snake, Board, ALL_MOVES
from board_utils import in_bounds, build_obstacle_set
from pathfinding import flood_fill


# --- Lightweight simulation state ---

class SimState:
    """Minimal game state for fast simulation."""

    __slots__ = ("width", "height", "snakes", "food", "hazards")

    def __init__(self, state: GameState):
        self.width = state.board.width
        self.height = state.board.height
        self.snakes: list[SimSnake] = []
        for s in state.board.snakes:
            self.snakes.append(SimSnake(
                id=s.id,
                body=list(s.body),
                health=s.health,
                is_me=(s.id == state.me.id),
            ))
        self.food: set[Coord] = set(state.board.food)
        self.hazards: set[Coord] = set(state.board.hazards)

    def copy(self) -> SimState:
        new = object.__new__(SimState)
        new.width = self.width
        new.height = self.height
        new.snakes = [s.copy() for s in self.snakes]
        new.food = set(self.food)
        new.hazards = set(self.hazards)
        return new


class SimSnake:
    """Minimal snake for simulation."""

    __slots__ = ("id", "body", "health", "is_me", "alive")

    def __init__(self, id: str, body: list[Coord], health: int, is_me: bool):
        self.id = id
        self.body = body
        self.health = health
        self.is_me = is_me
        self.alive = True

    @property
    def head(self) -> Coord:
        return self.body[0]

    @property
    def length(self) -> int:
        return len(self.body)

    def copy(self) -> SimSnake:
        s = object.__new__(SimSnake)
        s.id = self.id
        s.body = list(self.body)
        s.health = self.health
        s.is_me = self.is_me
        s.alive = True
        return s


def predict_enemy_move(snake: SimSnake, sim: SimState) -> Coord:
    """Predict most likely enemy move: toward food if hungry, else most space."""
    head = snake.body[0]
    w, h = sim.width, sim.height

    # Build obstacles (all snake bodies except tails)
    obstacles: set[Coord] = set()
    for s in sim.snakes:
        if s.alive:
            for seg in s.body[:-1]:
                obstacles.add(seg)

    # Get valid moves
    valid: list[tuple[str, Coord]] = []
    for name, delta in ALL_MOVES:
        pos = head + delta
        if in_bounds(pos, w, h) and pos not in obstacles:
            valid.append((name, pos))

    if not valid:
        # No valid moves, will die
        return head + Coord(0, 1)

    # If hungry, move toward nearest food
    if snake.health < 50 and sim.food:
        nearest_food = min(sim.food, key=lambda f: head.manhattan(f))
        best = min(valid, key=lambda m: m[1].manhattan(nearest_food))
        return best[1]

    # Otherwise, move toward most open space
    best_space = -1
    best_pos = valid[0][1]
    for _, pos in valid:
        count, _ = flood_fill(pos, obstacles, w, h)
        if count > best_space:
            best_space = count
            best_pos = pos

    return best_pos


def simulate_step(sim: SimState, my_move: Coord) -> None:
    """Advance simulation by one step. Modifies sim in place."""
    w, h = sim.width, sim.height

    # Determine moves for all snakes
    moves: dict[str, Coord] = {}
    for snake in sim.snakes:
        if not snake.alive:
            continue
        if snake.is_me:
            moves[snake.id] = my_move
        else:
            moves[snake.id] = predict_enemy_move(snake, sim)

    # Apply moves
    for snake in sim.snakes:
        if not snake.alive:
            continue
        new_head = moves.get(snake.id)
        if new_head is None:
            continue
        snake.body.insert(0, new_head)

        # Check food
        if new_head in sim.food:
            snake.health = 100
            sim.food.discard(new_head)
        else:
            snake.body.pop()  # Remove tail
            snake.health -= 1

        # Hazard damage
        if new_head in sim.hazards:
            snake.health -= 15

    # Check eliminations
    # Build body sets (excluding heads for head-on checks)
    body_cells: set[Coord] = set()
    for snake in sim.snakes:
        if snake.alive:
            for seg in snake.body[1:]:
                body_cells.add(seg)

    for snake in sim.snakes:
        if not snake.alive:
            continue
        head = snake.body[0]

        # Wall collision
        if not in_bounds(head, w, h):
            snake.alive = False
            continue

        # Health
        if snake.health <= 0:
            snake.alive = False
            continue

        # Body collision (including self)
        if head in body_cells:
            snake.alive = False
            continue

    # Head-on collisions
    heads: dict[Coord, list[SimSnake]] = {}
    for snake in sim.snakes:
        if snake.alive:
            heads.setdefault(snake.body[0], []).append(snake)

    for coord, snakes_at in heads.items():
        if len(snakes_at) > 1:
            max_len = max(s.length for s in snakes_at)
            for s in snakes_at:
                if s.length < max_len:
                    s.alive = False
                elif snakes_at.count(s) < len(snakes_at):
                    # Check if all same length
                    if all(ss.length == max_len for ss in snakes_at):
                        s.alive = False


def evaluate_sim(sim: SimState) -> float:
    """Evaluate simulation state from our snake's perspective. Higher = better."""
    me = None
    for s in sim.snakes:
        if s.is_me:
            me = s
            break

    if me is None or not me.alive:
        return -1000.0

    alive_enemies = sum(1 for s in sim.snakes if s.alive and not s.is_me)

    # Survived + enemy attrition is good
    score = 100.0
    score += (len(sim.snakes) - 1 - alive_enemies) * 50.0  # Enemies eliminated
    score += me.health * 0.5
    score += me.length * 2.0

    # Space available
    obstacles: set[Coord] = set()
    for s in sim.snakes:
        if s.alive:
            for seg in s.body[:-1]:
                obstacles.add(seg)
    space, _ = flood_fill(me.body[0], obstacles, sim.width, sim.height)
    score += space * 0.5

    return score


def mcts(
    state: GameState,
    candidate_moves: list[tuple[str, Coord]],
    time_budget_ms: float = 200.0,
    max_playouts: int = 50,
    playout_depth: int = 4,
) -> dict[str, float]:
    """Monte Carlo Tree Search over candidate moves.

    Returns dict mapping move_name -> average score from playouts.
    """
    if not candidate_moves:
        return {}

    start_time = time.time()
    deadline = start_time + time_budget_ms / 1000.0

    scores: dict[str, list[float]] = {name: [] for name, _ in candidate_moves}
    playout_count = 0

    while playout_count < max_playouts and time.time() < deadline:
        for move_name, move_pos in candidate_moves:
            if time.time() >= deadline:
                break

            sim = SimState(state)
            simulate_step(sim, move_pos)

            # Run playout
            me_snake = None
            for s in sim.snakes:
                if s.is_me and s.alive:
                    me_snake = s
                    break

            if me_snake is None:
                scores[move_name].append(-1000.0)
                continue

            for _ in range(playout_depth - 1):
                if not me_snake.alive:
                    break

                # Pick a random valid move for us
                head = me_snake.body[0]
                obstacles: set[Coord] = set()
                for s in sim.snakes:
                    if s.alive:
                        for seg in s.body[:-1]:
                            obstacles.add(seg)

                valid = []
                for _, delta in ALL_MOVES:
                    p = head + delta
                    if in_bounds(p, sim.width, sim.height) and p not in obstacles:
                        valid.append(p)

                if not valid:
                    break

                my_next = random.choice(valid)
                simulate_step(sim, my_next)

            scores[move_name].append(evaluate_sim(sim))
            playout_count += 1

    # Average scores
    result: dict[str, float] = {}
    for name, score_list in scores.items():
        if score_list:
            result[name] = sum(score_list) / len(score_list)
        else:
            result[name] = 0.0

    return result
