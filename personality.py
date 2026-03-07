"""Snake personality: contextual shouts and cosmetics."""

from __future__ import annotations
import random
from game import GameState

# --- Cosmetics ---
SNAKE_COLOR = "#00FF41"  # Matrix green
SNAKE_HEAD = "evil"
SNAKE_TAIL = "bolt"
SNAKE_AUTHOR = "packet_sniffers"

# --- Shout categories ---

SHOUTS_EATING = [
    "packet received",
    "ACK",
    "200 OK",
    "nom nom nom",
    "downloading food.exe",
    "payload delivered",
]

SHOUTS_KILL = [
    "connection reset by peer",
    "sniffed you out",
    "EOF",
    "rm -rf /snake",
    "segfault",
    "404 snake not found",
    "connection terminated",
]

SHOUTS_LOW_HEALTH = [
    "signal weak...",
    "packet loss detected",
    "low bandwidth",
    "buffering...",
    "connection unstable",
]

SHOUTS_LARGE = [
    "buffer overflow incoming",
    "DDoS mode activated",
    "root access granted",
    "sudo snake",
    "stack overflow",
]

SHOUTS_WINNING = [
    "gg no re",
    "pwned",
    "root access granted",
    "hack complete",
    "all your base are belong to us",
]

SHOUTS_GENERAL = [
    "sniffing packets...",
    "wireshark mode",
    "ping... pong...",
    "traceroute in progress",
    "SYN... SYN-ACK...",
    "decrypting...",
    "man-in-the-middle",
    "port scanning...",
    "nmap -sS",
    "chmod 777",
]


def generate_shout(
    state: GameState,
    ate_food: bool = False,
    killed_enemy: bool = False,
) -> str:
    """Generate a contextual shout based on game state."""
    me = state.me
    num_enemies = len(state.enemies)

    # Priority-based shout selection
    if killed_enemy:
        return random.choice(SHOUTS_KILL)
    if ate_food:
        return random.choice(SHOUTS_EATING)
    if me.health < 20:
        return random.choice(SHOUTS_LOW_HEALTH)
    if num_enemies == 0:
        return random.choice(SHOUTS_WINNING)
    if me.length > 15:
        return random.choice(SHOUTS_LARGE)

    return random.choice(SHOUTS_GENERAL)
