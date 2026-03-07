# BattleSnake 2026 – Deploy & Test Guide

Deploy your bot to the web, then test it with the [BattleSnake Board](https://github.com/njitacm/BattleSnake_2026).

---

## 1. Deploy to Render (get your bot URL)

Your project has `render.yaml` configured.

1. Push your code to GitHub.
2. Go to [render.com](https://render.com) and sign in with GitHub.
3. **New → Web Service**, connect the repo that contains `render.yaml`.
4. Render will detect the Python service; confirm:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 10`
5. Deploy. Render will assign a URL like `https://packet-sniffers-xxxx.onrender.com`.

**Note:** On the free plan the service may spin down when idle; the first request after idle can be slow (cold start).

---

## 2. Test with the BattleSnake Board

The [BattleSnake_2026](https://github.com/njitacm/BattleSnake_2026) repo provides a Docker-based game runner that plays games and calls your bot by URL.

### One-time setup

```bash
git clone https://github.com/njitacm/BattleSnake_2026.git
cd BattleSnake_2026/battlesnake_board
docker network create snakenet
docker build -t battlesnake_board .
```

### Run a game (use your deployed URL)

Replace `https://packet-sniffers-xxxx.onrender.com` with your actual Render URL:

```bash
docker run --rm --network snakenet battlesnake_board battlesnake play \
  -W 11 -H 11 --timeout 5000 \
  --name packet_sniffers \
  --url https://packet-sniffers-xxxx.onrender.com
```

**Optional:** Save replays to a folder:

```bash
mkdir -p C:/battlesnake/replays
docker run --rm --network snakenet -v "C:/battlesnake/replays:/replays" \
  battlesnake_board battlesnake play -W 11 -H 11 --timeout 5000 \
  --output "/replays/battlesnake_replay_$(date +%Y%m%d-%H%M%S).json" \
  --name packet_sniffers \
  --url https://packet-sniffers-xxxx.onrender.com
```

**Useful board flags:**

- `-W`, `-H` – board width/height (e.g. 11)
- `--timeout 5000` – move timeout in ms
- `--name` – your snake’s display name
- `--url` – your bot’s base URL (no trailing slash)
- `-v` – verbose
- `--browser` – open in browser (if supported)
- `--help` – full options

---

## Checklist

| Step | Action |
|------|--------|
| 1. Deploy | Push to GitHub → Connect repo on Render → Deploy |
| 2. Get URL | Copy your service URL (e.g. `https://packet-sniffers-xxxx.onrender.com`) |
| 3. Setup board (once) | Clone BattleSnake_2026 → `cd battlesnake_board` → `docker network create snakenet` → `docker build -t battlesnake_board .` |
| 4. Play a game | `docker run --rm --network snakenet battlesnake_board battlesnake play ... --url <YOUR_RENDER_URL> --name packet_sniffers` |

BattleSnake Board repo: https://github.com/njitacm/BattleSnake_2026
