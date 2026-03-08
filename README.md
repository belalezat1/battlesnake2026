# 🐍 BattleSnake 2026 — Packet Sniffers

**NJIT Hackathon · BattleSnake 2026**

A competitive BattleSnake bot with an **aggressive** playstyle: **hunt food first 🍎 → grow big 🐍 → then eliminate opponents 💀**

---

## 🎯 Overview

We play **aggressively**: prioritize food to grow, then use our size advantage to hunt and kill. Bigger snake = head-on wins + more board control. Safety checks, space awareness, and MCTS refinement keep us alive.

---

## 🛠️ Built With

- **Python 3.12** · **Flask** · **Docker**
- BattleSnake API v1

**Run locally:**
```bash
pip install -r requirements.txt
python main.py
```

**Run with Docker:**
```bash
docker build -t battlesnake2026 .
docker run -p 8080:8080 battlesnake2026
```

---

## 🧠 Logic & Strategy

| Component | What it does |
|-----------|---------------|
| **`game.py`** | Parses game state (Coord, Snake, Board) |
| **`board_utils.py`** | Obstacles, danger squares, kill squares, safe moves |
| **`pathfinding.py`** | A* to food, flood fill (space/traps), Voronoi (territory) |
| **`strategy.py`** | Food targeting, move scoring, phases (early/mid/late) |
| **`simulation.py`** | MCTS + enemy prediction for move refinement |
| **`logic.py`** | Orchestrates: heuristic (60%) + MCTS (40%) → best move |

**Approach:** Food urgency scales with health. We score kill squares (win head-on), hunt when bigger, and squeeze enemies in late game. Avoid danger, traps, and bad edges.

---

## 📁 File Structure

```
battlesnake2026/
├── main.py          # Flask API
├── logic.py         # Turn pipeline
├── game.py          # State parsing
├── board_utils.py   # Board logic
├── pathfinding.py   # A*, flood fill, Voronoi
├── strategy.py      # Aggressive scoring
├── simulation.py    # MCTS
├── personality.py   # Shouts & cosmetics
├── requirements.txt
└── Dockerfile
```

---


