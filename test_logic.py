"""Tests for battlesnake logic."""

import pytest
from game import Coord, parse_state, parse_coord, Snake
from board_utils import (
    in_bounds,
    build_obstacle_set,
    get_danger_squares,
    get_kill_squares,
    get_safe_moves,
)
from pathfinding import astar, flood_fill, voronoi
from strategy import detect_phase, find_best_food, evaluate_moves
from logic import choose_move

# testing
# --- Fixtures ---

def make_game_state(
    width=11,
    height=11,
    my_body=None,
    my_health=100,
    enemies=None,
    food=None,
    hazards=None,
    turn=0,
    game_mode="standard",
):
    """Build a minimal BattleSnake API game state dict."""
    if my_body is None:
        my_body = [{"x": 5, "y": 5}, {"x": 5, "y": 4}, {"x": 5, "y": 3}]
    if enemies is None:
        enemies = []
    if food is None:
        food = []
    if hazards is None:
        hazards = []

    me = {
        "id": "me",
        "name": "packet_sniffers",
        "body": my_body,
        "health": my_health,
    }
    snakes = [me] + enemies

    return {
        "game": {"id": "test", "ruleset": {"name": game_mode}},
        "turn": turn,
        "you": me,
        "board": {
            "width": width,
            "height": height,
            "food": food,
            "hazards": hazards,
            "snakes": snakes,
        },
    }


# --- Coord tests ---

class TestCoord:
    def test_add(self):
        assert Coord(1, 2) + Coord(3, 4) == Coord(4, 6)

    def test_sub(self):
        assert Coord(5, 5) - Coord(2, 3) == Coord(3, 2)

    def test_manhattan(self):
        assert Coord(0, 0).manhattan(Coord(3, 4)) == 7

    def test_hashable(self):
        s = {Coord(1, 1), Coord(1, 1), Coord(2, 2)}
        assert len(s) == 2


# --- Board utils tests ---

class TestBoardUtils:
    def test_in_bounds(self):
        assert in_bounds(Coord(0, 0), 11, 11)
        assert in_bounds(Coord(10, 10), 11, 11)
        assert not in_bounds(Coord(-1, 0), 11, 11)
        assert not in_bounds(Coord(11, 0), 11, 11)

    def test_obstacle_set_excludes_tail(self):
        data = make_game_state(my_health=50)  # Not just ate
        state = parse_state(data)
        obstacles = build_obstacle_set(state)
        tail = state.me.tail
        assert tail not in obstacles

    def test_obstacle_set_includes_tail_when_ate(self):
        data = make_game_state(my_health=100)  # Just ate
        state = parse_state(data)
        obstacles = build_obstacle_set(state)
        tail = state.me.tail
        assert tail in obstacles

    def test_safe_moves_avoids_wall(self):
        data = make_game_state(
            my_body=[{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
        )
        state = parse_state(data)
        obstacles = build_obstacle_set(state)
        safe = get_safe_moves(state, obstacles)
        move_names = [n for n, _ in safe]
        assert "down" not in move_names  # Wall
        assert "left" not in move_names  # Wall

    def test_danger_squares(self):
        enemy = {
            "id": "enemy1",
            "name": "enemy",
            "body": [{"x": 7, "y": 5}, {"x": 7, "y": 4}, {"x": 7, "y": 3}],
            "health": 90,
        }
        data = make_game_state(enemies=[enemy])
        state = parse_state(data)
        danger = get_danger_squares(state)
        # Enemy head at (7,5), same length as us (3), so danger squares
        assert Coord(7, 6) in danger
        assert Coord(8, 5) in danger

    def test_kill_squares(self):
        enemy = {
            "id": "enemy1",
            "name": "enemy",
            "body": [{"x": 7, "y": 5}, {"x": 7, "y": 4}],  # Length 2, shorter
            "health": 90,
        }
        data = make_game_state(enemies=[enemy])
        state = parse_state(data)
        kills = get_kill_squares(state)
        assert Coord(7, 6) in kills


# --- Pathfinding tests ---

class TestPathfinding:
    def test_astar_simple(self):
        dist, path = astar(Coord(0, 0), Coord(3, 0), set(), 11, 11)
        assert dist == 3
        assert path[0] == Coord(0, 0)
        assert path[-1] == Coord(3, 0)

    def test_astar_with_obstacle(self):
        obstacles = {Coord(1, 0), Coord(1, 1)}
        dist, path = astar(Coord(0, 0), Coord(2, 0), obstacles, 11, 11)
        assert dist is not None
        assert dist > 2  # Must go around

    def test_astar_unreachable(self):
        # Surround the goal
        obstacles = {Coord(4, 5), Coord(6, 5), Coord(5, 4), Coord(5, 6)}
        dist, path = astar(Coord(0, 0), Coord(5, 5), obstacles, 11, 11)
        assert dist is None
        assert path == []

    def test_flood_fill_open_board(self):
        count, cells = flood_fill(Coord(5, 5), set(), 11, 11)
        assert count == 121  # Full 11x11 board

    def test_flood_fill_with_obstacles(self):
        # Create a wall that splits the board
        wall = {Coord(i, 5) for i in range(11)}
        count, cells = flood_fill(Coord(5, 6), wall, 11, 11)
        assert count < 121
        assert count == 55  # Top half

    def test_voronoi(self):
        data = make_game_state(
            my_body=[{"x": 2, "y": 5}, {"x": 1, "y": 5}, {"x": 0, "y": 5}],
            enemies=[{
                "id": "enemy1",
                "name": "enemy",
                "body": [{"x": 8, "y": 5}, {"x": 9, "y": 5}, {"x": 10, "y": 5}],
                "health": 90,
            }],
        )
        state = parse_state(data)
        obstacles = build_obstacle_set(state)
        counts = voronoi(state, obstacles)
        # We should control roughly half the board
        assert counts.get("me", 0) > 30
        assert counts.get("enemy1", 0) > 30


# --- Strategy tests ---

class TestStrategy:
    def test_phase_early(self):
        data = make_game_state(
            my_body=[{"x": 5, "y": 5}, {"x": 5, "y": 4}],  # Length 2
            my_health=80,
            enemies=[{
                "id": "e1", "name": "e", "health": 90,
                "body": [{"x": 0, "y": 0}, {"x": 1, "y": 0}],
            }],
        )
        state = parse_state(data)
        assert detect_phase(state) == "early"

    def test_phase_desperation(self):
        data = make_game_state(my_health=10)
        state = parse_state(data)
        assert detect_phase(state) == "desperation"

    def test_phase_late(self):
        data = make_game_state(
            my_body=[{"x": i, "y": 5} for i in range(8)],
            my_health=80,
        )
        state = parse_state(data)
        assert detect_phase(state) == "late"  # No enemies

    def test_evaluate_moves_returns_results(self):
        data = make_game_state(
            food=[{"x": 5, "y": 8}],
            enemies=[{
                "id": "e1", "name": "e", "health": 90,
                "body": [{"x": 8, "y": 8}, {"x": 9, "y": 8}, {"x": 10, "y": 8}],
            }],
        )
        state = parse_state(data)
        moves = evaluate_moves(state)
        assert len(moves) > 0
        assert all(len(m) == 3 for m in moves)


# --- Integration tests ---

class TestChooseMove:
    def test_returns_valid_move(self):
        data = make_game_state()
        result = choose_move(data)
        assert result["move"] in ("up", "down", "left", "right")

    def test_returns_shout(self):
        data = make_game_state()
        result = choose_move(data)
        assert "shout" in result
        assert len(result["shout"]) <= 256

    def test_avoids_wall(self):
        data = make_game_state(
            my_body=[{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
        )
        result = choose_move(data)
        assert result["move"] in ("up", "right")  # Not left or down (walls)

    def test_avoids_self(self):
        data = make_game_state(
            my_body=[
                {"x": 5, "y": 5},
                {"x": 5, "y": 6},
                {"x": 4, "y": 6},
                {"x": 4, "y": 5},
                {"x": 4, "y": 4},
            ],
        )
        result = choose_move(data)
        # Head at (5,5), body blocks left and up
        assert result["move"] in ("right", "down")

    def test_with_food(self):
        data = make_game_state(
            my_health=20,  # Hungry!
            food=[{"x": 5, "y": 8}],
        )
        result = choose_move(data)
        assert result["move"] in ("up", "down", "left", "right")

    def test_constrictor_mode(self):
        data = make_game_state(game_mode="constrictor")
        result = choose_move(data)
        assert result["move"] in ("up", "down", "left", "right")

    def test_with_hazards(self):
        hazards = [{"x": x, "y": y} for x in range(3) for y in range(3)]
        data = make_game_state(hazards=hazards, game_mode="royale")
        result = choose_move(data)
        assert result["move"] in ("up", "down", "left", "right")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
