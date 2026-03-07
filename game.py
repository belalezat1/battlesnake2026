"""Typed game state parsing for BattleSnake API."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Coord:
    x: int
    y: int

    def __add__(self, other: Coord) -> Coord:
        return Coord(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Coord) -> Coord:
        return Coord(self.x - other.x, self.y - other.y)

    def manhattan(self, other: Coord) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


# Direction constants
UP = Coord(0, 1)
DOWN = Coord(0, -1)
LEFT = Coord(-1, 0)
RIGHT = Coord(1, 0)

DIRECTIONS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}
ALL_MOVES = list(DIRECTIONS.items())


@dataclass(slots=True)
class Snake:
    id: str
    body: list[Coord]
    health: int
    name: str = ""

    @property
    def head(self) -> Coord:
        return self.body[0]

    @property
    def tail(self) -> Coord:
        return self.body[-1]

    @property
    def length(self) -> int:
        return len(self.body)

    @property
    def just_ate(self) -> bool:
        """If health is 100, the snake just ate — its tail didn't vacate."""
        return self.health == 100


@dataclass(slots=True)
class Board:
    width: int
    height: int
    food: list[Coord]
    hazards: list[Coord]
    snakes: list[Snake]


@dataclass(slots=True)
class GameState:
    turn: int
    board: Board
    me: Snake
    enemies: list[Snake]
    game_mode: str  # "standard", "royale", "constrictor", "snail"
    game_id: str

    @property
    def alive_snakes(self) -> list[Snake]:
        return self.board.snakes


def parse_coord(d: dict) -> Coord:
    return Coord(d["x"], d["y"])


def parse_snake(d: dict) -> Snake:
    return Snake(
        id=d["id"],
        body=[parse_coord(s) for s in d["body"]],
        health=d["health"],
        name=d.get("name", ""),
    )


def parse_state(data: dict) -> GameState:
    board_data = data["board"]
    me = parse_snake(data["you"])

    snakes = [parse_snake(s) for s in board_data["snakes"]]
    enemies = [s for s in snakes if s.id != me.id]

    board = Board(
        width=board_data["width"],
        height=board_data["height"],
        food=[parse_coord(f) for f in board_data["food"]],
        hazards=[parse_coord(h) for h in board_data.get("hazards", [])],
        snakes=snakes,
    )

    ruleset = data.get("game", {}).get("ruleset", {})
    game_mode = ruleset.get("name", "standard")
    game_id = data.get("game", {}).get("id", "")

    return GameState(
        turn=data["turn"],
        board=board,
        me=me,
        enemies=enemies,
        game_mode=game_mode,
        game_id=game_id,
    )
