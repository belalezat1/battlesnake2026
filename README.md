# BattleSnake 2026 — packet_sniffers

**NJIT Hackathon · BattleSnake 2026**

A competitive BattleSnake bot with an **aggressive** playstyle: **hunt food first to grow, then use size and position to eliminate opponents.**

---

## Project overview

This bot participates in the [BattleSnake](https://play.battlesnake.com/) game engine via the standard HTTP API. It runs as a web service that receives game state each turn and returns a single move (`up`, `down`, `left`, `right`).

**Strategy summary:**

- **Aggressive, food-first approach** — Prioritize reaching food to grow. A larger snake wins head-on collisions, controls more space (Voronoi), and can safely hunt smaller enemies.
- **Then kill** — Once we have a size or health advantage, we score moves that put us on **kill squares** (where we win head-on), cut off enemy space, and squeeze opponents in the late game.
- **Safety and space** — We still avoid danger squares (where equal/larger heads can move), traps (low flood-fill space), and bad edges/corners.
- **Refinement with MCTS** — Candidate moves from the heuristic engine are refined with Monte Carlo Tree Search within the turn time budget.

The stack is **Python 3.12**, **Flask** for the API, and **Docker** for deployment. The codebase is modular: game state, board utilities, pathfinding, strategy, simulation (MCTS), and personality are in separate modules.

---

## How it was built

- **Runtime:** Python 3.12  
- **API:** Flask (and Gunicorn in production)  
- **Deployment:** Docker; single worker, 10s timeout  
- **API version:** BattleSnake API v1  

**Run locally:**

```bash
pip install -r requirements.txt
python main.py   # Server on port 8000 (or PORT env)
```

**Run with Docker:**

```bash
docker build -t battlesnake2026 .
docker run -p 8080:8080 battlesnake2026
```

Endpoints:

- `GET /` — Bot metadata (author, color, head, tail, version)  
- `POST /start` — Game start  
- `POST /move` — Receives game state, returns `{ "move": "up", "shout": "..." }`  
- `POST /end` — Game end  
- `GET /debug`, `GET /debug/state` — Debug UI and last-turn state  

---

## Logic and strategy

### 1. Game state and board

- **`game.py`** — Parses the BattleSnake JSON into typed structures: `Coord`, `Snake`, `Board`, `GameState`. Handles ruleset (standard, royale, constrictor, etc.).
- **`board_utils.py`** — Builds obstacle set (all body segments; tail excluded unless the snake just ate), hazard set, **danger squares** (cells where an equal-or-larger enemy head can move next turn), **kill squares** (cells where we win a head-on because the enemy is shorter), and **safe moves** (no wall/obstacle).

### 2. Pathfinding

- **`pathfinding.py`**
  - **A\*** — Shortest path to a target (e.g. food) with optional hazard cost (important in royale).
  - **Flood fill** — Reachable cell count from a position (used for space and trap detection).
  - **Time-aware flood fill** — Treats body segments as freeing over time (tail moves), for better trap evaluation.
  - **Voronoi** — Simultaneous BFS from all heads; each cell assigned to the closest head. Used for territory and aggression.

### 3. Aggressive strategy: food first, then kill

- **`strategy.py`**
  - **Game phase:** `early` (length &lt; 6), `mid`, `late` (≤1 enemy), `desperation` (health &lt; 15).
  - **Food targeting (`find_best_food`):** For each food, A* distance from our head; compare with enemy distances. Score favors:
    - Closer food.
    - Food we can reach before or with smaller enemies; heavy penalty if a bigger enemy is closer.
    - Bonus when we need to grow (smallest gap to enemies ≥ 0).
  - **Move scoring (`score_move`):**
    - **Food score (aggressive):** We always pursue food to grow. Food urgency scales by health (critical &lt; 20, hungry &lt; 50, proactive &lt; 80). Bonus for stepping onto the target food. In Constrictor mode, food score is disabled.
    - **Space score:** Time-aware flood fill from the candidate cell. Severe penalty if space &lt; length (trap), moderate if &lt; 2× length.
    - **Territory (Voronoi):** Favors moves that increase our controlled cells vs. enemies.
    - **Aggression / kill:** Bonus for moving onto **kill squares**. In late game, extra weight for reducing enemy territory.
    - **Hunt score:** When we’re much bigger (e.g. 1.5× min enemy length) in mid/late, we score moves toward the nearest enemy head and give a bonus when the enemy’s flood fill is squeezed (space &lt; 2× their length).
    - **Safety:** Large penalty for danger squares, penalty for hazards (stronger in royale).
    - **Edge/corner:** Penalties for edges and especially corners to avoid getting trapped.
    - **Tail chase:** Used as a fallback when there’s no food target (e.g. Constrictor).
  - Phase-specific weighting (e.g. desperation = max food; late = more territory, aggression, hunt) keeps the same “food first, then kill” idea while adapting to the game state.

So: we **hunt and take food first** to get bigger and healthier; then we **kill** by favoring kill squares, territory, and hunt behavior when we have an advantage.

### 4. Move selection and MCTS

- **`logic.py`** — Orchestrator:
  1. Parse state, then run **heuristic evaluation** (`evaluate_moves`) to get scored candidate moves.
  2. Run **MCTS** (`simulation.mcts`) on safe (prefer non-danger) moves with a time budget (~150 ms or so before 500 ms timeout).
  3. **Combine scores:** 60% normalized heuristic, 40% normalized MCTS; pick the move with highest combined score.
  4. Optionally set a contextual shout and store debug state for the debug UI.

- **`simulation.py`**
  - **SimState / SimSnake** — Lightweight state for fast simulation.
  - **Enemy move prediction** — Hungry enemies move toward nearest food; others move toward maximum flood-fill space.
  - **`simulate_step`** — Applies our move and predicted enemy moves, handles food, hazards, body/wall/head-on collisions.
  - **MCTS** — For each candidate move, run short playouts (depth ~4) with random follow-up moves for us and predicted moves for enemies; evaluate with `evaluate_sim` (survival, enemy eliminations, health, length, space). Returns average score per move to blend with the heuristic.

### 5. Personality and debug

- **`personality.py`** — Defines snake look (e.g. color, head/tail) and **contextual shouts** (eating, kill, low health, large, winning, general) for a “packet_sniffers” theme.
- **`static/debug.html`** + **`GET /debug/state`** — Simple debug dashboard using the last stored state (scores, board, best move, timing).

---

## File structure

```
battlesnake2026/
├── main.py           # Flask app: /, /start, /move, /end, /debug
├── logic.py          # choose_move(): parse → heuristic → MCTS → combine → response
├── game.py           # Coord, Snake, Board, GameState, parse_state()
├── board_utils.py    # Obstacles, hazards, danger/kill squares, safe moves
├── pathfinding.py    # A*, flood_fill, flood_fill_time_aware, voronoi
├── strategy.py       # Game phase, find_best_food(), score_move(), evaluate_moves()
├── simulation.py     # SimState, enemy prediction, simulate_step(), mcts()
├── personality.py    # Cosmetics + contextual shouts
├── requirements.txt  # flask, gunicorn
├── Dockerfile        # Python 3.12-slim, gunicorn
├── static/
│   └── debug.html    # Debug UI
├── test_logic.py     # Tests (if present)
├── render.yaml       # Render deployment (if used)
└── README.md         # This file
```

### Main files and roles

| File            | Role |
|-----------------|------|
| **main.py**     | HTTP API and bot metadata. |
| **logic.py**    | Turn pipeline: parse → heuristic scoring → MCTS → combine → shout/debug. |
| **game.py**     | Data models and JSON parsing for game state. |
| **board_utils.py** | Obstacles, hazards, danger/kill squares, safe moves. |
| **pathfinding.py** | A*, flood fill (normal + time-aware), Voronoi. |
| **strategy.py** | Phases, food targeting, move scoring (food-first aggressive, then kill/territory/hunt). |
| **simulation.py** | Rollout state, enemy prediction, step simulation, MCTS. |
| **personality.py** | Snake appearance and contextual shouts. |

---

## Approach in one sentence

**We play aggressively: hunt and take food first to grow, then use size and position to kill—backed by safety checks, space awareness, and MCTS refinement.**

---

**Team:** packet_sniffers · **Event:** NJIT Hackathon — BattleSnake 2026
