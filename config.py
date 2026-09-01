"""Speed race bot configuration: paths, speed constants, token loading."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent  # repo root holding sw_data.db / mapping.json

DB_PATH = PARENT_DIR / "sw_data.db"
MAPPING_PATH = PARENT_DIR / "mapping.json"

# --- speed model constants (planning_doc.md) --------------------------------
TOWER_BONUS = 0.15          # 15% of base from the Speed Tower
SWIFT_BONUS = 0.25          # swift set, always assumed in both fields
# passive bonuses keyed by resolved English monster name (invisible in output)
PASSIVE_SPD = {"Chilling": 39, "Elsharion": 25}
PASSIVE_NOTE = {
    "Chilling": "Chilling gains +39 spd from two buffs.",
    "Elsharion": "Elsharion gains +25 spd.",
}

# --- swarfarm hybrid refresh ------------------------------------------------
SWARFARM_URL = "https://swarfarm.com/api/v2/monsters/?format=json"
SWARFARM_CACHE = BASE_DIR / "data" / "swarfarm_monsters.json"
SWARFARM_MAX_AGE_DAYS = 7
SWARFARM_USER_AGENT = "speedrace-bot/1.0"
SWARFARM_PAGE_SIZE = 100

# --- discord ----------------------------------------------------------------
def load_dotenv(path: Path | None = None) -> None:
    """Tiny .env loader (KEY=VALUE lines, # comments) — avoids an extra dep."""
    path = path or BASE_DIR / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = os.getenv("GUILD_ID")
if GUILD_ID:
    GUILD_ID = int(GUILD_ID)
