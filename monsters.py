"""Monster roster: local sw_data.db (primary) + hybrid swarfarm refresh.

The local database is itself generated from the swarfarm API
(``save_monster_list.py`` in the parent repo) and is the authoritative,
offline source for base speeds. On startup (or when the cache is stale) the
bot tries to refresh from the live swarfarm API and only *adds* monsters that
are missing locally — existing entries are never overridden.

English names: the db stores Korean names for newer monsters; they are
translated via ``../mapping.json`` (family name for unawakened forms,
individual name for awakened forms), mirroring ``optimizer_discord``.

Non-playable entities (towers, crystals, incarnations, bosses, dummies) are
excluded: every family id >= 1000 except the homunculi, plus a small explicit
list of non-playable families below 1000.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from config import (
    DB_PATH,
    MAPPING_PATH,
    SWARFARM_CACHE,
    SWARFARM_MAX_AGE_DAYS,
    SWARFARM_PAGE_SIZE,
    SWARFARM_URL,
    SWARFARM_USER_AGENT,
)

log = logging.getLogger("speedrace.monsters")

# Non-playable families below 1000 (bosses, dummies, tutorial/raid mobs,
# 2A awakening bosses, ToA towers, world/guild bosses, event units...).
_NONPLAYABLE_FAMILIES = frozenset({
    # Fodder / awakening material (never used in battle, speed 0 or cosmetic)
    142, 143, 151, 182, 217,
    *range(604, 612),  # transmogrified Angelmon / Devilmon / Rainbowmon
    255,               # ROBO boss wreckage
    315, 316,          # tombstones (event decoration)
    450,               # costume-item dummies
    460, 462,          # labyrinth boss head/arms/rune patterns
    480, 481, 482,     # 2A awakening bosses
    622,               # world boss
    631, 632, 633,     # tutorial bosses
    720,               # guild boss
    1101, 1102,        # Trial of Ascension towers
    1110,              # tutorial tower
    1120,              # artifact boss
    1210, 1211, 1212, 1213, 1214, 1215, 1216, 1217,  # 2A position-fix dummies
    2110, 2114, 2115,  # guard spirits
    3200, 3201,        # cake wolf (event)
    4010, 4011, 4012, 4013,  # dimensional hole raid bosses
    9000,              # April Fools Irene
})

# Families >= 1000 are all non-playable *except* the homunculi.
_HOMUNCULUS_FAMILIES = frozenset({10001, 10002})  # Attack / Support homunculus

# Playable families whose English name is missing from mapping.json
_FAMILY_NAME_OVERRIDES = {
    238: "Zombie",
    273: "Altair",
    330: "Mishima Heihachi",
    345: "Gandalf",
}


@dataclass(frozen=True)
class Monster:
    com2us_id: int
    name: str        # English name
    element: str
    speed: int       # level-40 base speed
    awaken_level: int


def _family(com2us_id: int) -> int:
    return com2us_id // 100


def _is_excluded(com2us_id: int) -> bool:
    fam = _family(com2us_id)
    if fam >= 1000:
        return fam not in _HOMUNCULUS_FAMILIES
    return fam in _NONPLAYABLE_FAMILIES


@lru_cache(maxsize=1)
def _mapping_names() -> dict[str, str]:
    if not MAPPING_PATH.is_file():
        return {}
    data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return data.get("monster", {}).get("names", {})


def english_name(com2us_id: int, raw_name: str, awaken_level: int) -> str:
    """Resolve a db row to its English name (see module docstring)."""
    if all(ord(ch) <= 127 for ch in raw_name):
        return raw_name
    names = _mapping_names()
    if awaken_level:
        en = names.get(str(com2us_id))
        if en and all(ord(ch) <= 127 for ch in en):
            return en
    fam = _family(com2us_id)
    if fam in _FAMILY_NAME_OVERRIDES:
        return _FAMILY_NAME_OVERRIDES[fam]
    en = names.get(str(fam))
    if en and all(ord(ch) <= 127 for ch in en):
        return en
    return raw_name  # accented Latin or unknown — keep as-is


# --- local db roster --------------------------------------------------------

def _load_local_db() -> dict[int, Monster]:
    """Read playable monsters from ../sw_data.db keyed by com2us_id."""
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"monster database not found: {DB_PATH}")
    con = sqlite3.connect(str(DB_PATH))
    try:
        rows = con.execute(
            "SELECT com2us_id, name, element, speed, awaken_level FROM monsters"
        ).fetchall()
    finally:
        con.close()
    roster: dict[int, Monster] = {}
    for cid, raw, element, speed, awaken in rows:
        if _is_excluded(cid):
            continue
        roster[cid] = Monster(cid, english_name(cid, raw, awaken), element, speed, awaken)
    return roster


# --- swarfarm hybrid refresh ------------------------------------------------

def _fetch_swarfarm_pages() -> list[dict]:
    """Fetch every page of the swarfarm v2 monsters endpoint."""
    out: list[dict] = []
    url: str | None = SWARFARM_URL
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": SWARFARM_USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        out.extend(data.get("results", []))
        url = data.get("next")
        if url:
            time.sleep(0.25)  # be polite to the API
        if len(out) > 5000:  # sanity guard against runaway pagination
            break
    return out


def refresh_from_swarfarm(force: bool = False) -> int:
    """Fetch swarfarm monsters into the disk cache (stale check); return count.

    Never raises: any failure is logged and the existing cache/local db remain
    in use.
    """
    cache = Path(SWARFARM_CACHE)
    if not force and cache.is_file():
        age_days = (time.time() - cache.stat().st_mtime) / 86400
        if age_days < SWARFARM_MAX_AGE_DAYS:
            return -1  # fresh enough, nothing to do
    try:
        entries = _fetch_swarfarm_pages()
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        log.warning("swarfarm refresh failed: %s", exc)
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(entries), encoding="utf-8")
    return len(entries)


def load_swarfarm_cache() -> list[dict]:
    """Read the cached swarfarm payload (empty list if absent)."""
    cache = Path(SWARFARM_CACHE)
    if not cache.is_file():
        return []
    try:
        return json.loads(cache.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def merge_swarfarm_entries(roster: dict[int, Monster], entries: list[dict]) -> dict[int, Monster]:
    """Add swarfarm monsters missing from the roster (never override)."""
    merged = dict(roster)
    added = 0
    for entry in entries:
        try:
            cid = int(entry["com2us_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if cid in merged or _is_excluded(cid):
            continue
        name = entry.get("name")
        element = entry.get("element")
        speed = entry.get("speed")
        awaken = int(entry.get("awaken_level") or 0)
        if not name or not element or speed is None:
            continue
        merged[cid] = Monster(cid, name, element, int(speed), awaken)
        added += 1
    if added:
        log.info("swarfarm refresh added %d monsters", added)
    return merged


# --- roster facade ----------------------------------------------------------

class Roster:
    """In-memory monster catalog with search + resolution."""

    def __init__(self, monsters: dict[int, Monster]):
        self.by_id: dict[int, Monster] = monsters
        # (name_lower, element_lower) -> best monster (highest awaken, then id)
        self.by_name_element: dict[tuple[str, str], Monster] = {}
        for mon in sorted(monsters.values(), key=lambda m: (m.awaken_level, m.com2us_id)):
            key = (mon.name.lower(), mon.element.lower())
            self.by_name_element[key] = mon

    @classmethod
    def build(cls) -> "Roster":
        roster = _load_local_db()
        for entry in load_swarfarm_cache():
            roster = merge_swarfarm_entries(roster, [entry])
        return cls(roster)

    def __len__(self) -> int:
        return len(self.by_id)

    def get(self, com2us_id: int) -> Monster | None:
        return self.by_id.get(com2us_id)

    def search(self, query: str, limit: int = 25) -> list[Monster]:
        """Substring search over English names (case-insensitive), deduped."""
        wanted = query.strip().lower()
        if not wanted:
            return []
        hits: list[Monster] = []
        seen: set[tuple[str, str]] = set()
        for mon in self.by_id.values():
            if mon.name.lower() == wanted:
                hits.insert(0, mon)  # exact matches first
            elif wanted in mon.name.lower():
                hits.append(mon)
        deduped = []
        for mon in hits:
            key = (mon.name.lower(), mon.element.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(mon)
            if len(deduped) >= limit:
                break
        return deduped

    def resolve(self, value: str) -> Monster | None:
        """Resolve a dropdown value (com2us_id) or free-typed name/label.

        Accepts: "16114", "Lora", "Lora (Light, 120)", "Water Chilling".
        """
        value = value.strip()
        if value.isdigit():
            return self.by_id.get(int(value))
        label = value.split("(", 1)[0].strip()  # strip autocomplete suffix
        parts = label.split()
        if len(parts) >= 2 and parts[0].lower() in {
            "water", "fire", "wind", "light", "dark", "pure",
        }:
            element, name = parts[0], " ".join(parts[1:])
            return self.by_name_element.get((name.lower(), element.lower()))
        name = " ".join(parts)
        candidates = self.search(name, limit=10)
        if not candidates:
            return None
        exact = [m for m in candidates if m.name.lower() == name.lower()]
        return exact[0] if exact else candidates[0]


def load_roster() -> Roster:
    """Build the roster from local db + cached swarfarm data."""
    return Roster.build()
