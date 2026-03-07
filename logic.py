"""Main orchestrator: wires game state, strategy, MCTS, and personality."""

from __future__ import annotations
import time
from game import parse_state
from board_utils import build_obstacle_set, get_safe_moves, get_danger_squares
from strategy import evaluate_moves
from simulation import mcts
from personality import generate_shout

# Store last game state for debug dashboard
_last_debug: dict = {}


def get_last_debug() -> dict:
    return _last_debug


def choose_move(data: dict) -> dict:
    """Main entry point: parse state, evaluate moves, run MCTS, return best move."""
    global _last_debug
    start_time = time.time()

    state = parse_state(data)

    # Phase 1: Heuristic evaluation of all moves
    scored_moves = evaluate_moves(state)

    if not scored_moves:
        return {"move": "up", "shout": "404 move not found"}

    # Phase 2: MCTS refinement (use remaining time budget)
    elapsed_ms = (time.time() - start_time) * 1000
    mcts_budget = max(50.0, 250.0 - elapsed_ms)  # Leave ~200ms buffer before 500ms timeout

    obstacles = build_obstacle_set(state)
    safe_moves = get_safe_moves(state, obstacles)
    danger = get_danger_squares(state)
    non_dangerous = [(n, p) for n, p in safe_moves if p not in danger]
    candidates = non_dangerous if non_dangerous else safe_moves

    mcts_scores = {}
    if candidates and len(state.enemies) > 0:
        mcts_scores = mcts(state, candidates, time_budget_ms=mcts_budget)

    # Phase 3: Combine heuristic + MCTS scores
    heuristic_map = {name: score for name, _, score in scored_moves}

    # Normalize scores for combination
    h_values = list(heuristic_map.values())
    h_min, h_max = min(h_values), max(h_values)
    h_range = h_max - h_min if h_max != h_min else 1.0

    combined: dict[str, float] = {}
    for name, _, h_score in scored_moves:
        norm_h = (h_score - h_min) / h_range  # 0-1

        if name in mcts_scores:
            m_values = list(mcts_scores.values())
            m_min, m_max = min(m_values), max(m_values)
            m_range = m_max - m_min if m_max != m_min else 1.0
            norm_m = (mcts_scores[name] - m_min) / m_range  # 0-1
            # Weight: 60% heuristic, 40% MCTS
            combined[name] = norm_h * 0.6 + norm_m * 0.4
        else:
            combined[name] = norm_h

    best_move = max(combined, key=lambda k: combined[k])

    # Detect events for shouts
    ate_food = state.me.head in set(state.board.food)
    shout = generate_shout(state, ate_food=ate_food)

    # Store debug info
    elapsed_total = (time.time() - start_time) * 1000
    _last_debug = {
        "turn": state.turn,
        "phase": "early" if state.me.length < 6 else ("late" if len(state.enemies) <= 1 else "mid"),
        "health": state.me.health,
        "length": state.me.length,
        "heuristic_scores": {name: round(score, 2) for name, _, score in scored_moves},
        "mcts_scores": {k: round(v, 2) for k, v in mcts_scores.items()},
        "combined_scores": {k: round(v, 4) for k, v in combined.items()},
        "best_move": best_move,
        "elapsed_ms": round(elapsed_total, 1),
        "board": {
            "width": state.board.width,
            "height": state.board.height,
            "food": [{"x": f.x, "y": f.y} for f in state.board.food],
            "hazards": [{"x": h.x, "y": h.y} for h in state.board.hazards],
            "snakes": [
                {
                    "id": s.id,
                    "name": s.name,
                    "body": [{"x": c.x, "y": c.y} for c in s.body],
                    "health": s.health,
                    "is_me": s.id == state.me.id,
                }
                for s in state.board.snakes
            ],
        },
    }

    return {"move": best_move, "shout": shout}
