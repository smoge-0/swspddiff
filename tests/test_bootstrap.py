"""Tests for sw_data.db auto-creation (bootstrap) and bundled mapping.json."""

import tempfile
import unittest
from pathlib import Path

import monsters
from config import BASE_DIR, MAPPING_PATH

# minimal swarfarm-style entries: one playable monster + one excluded tower
ENTRIES = [
    {"id": 1, "com2us_id": 16114, "name": "Lora", "element": "Light",
     "base_hp": 11445, "base_attack": 681, "base_defense": 527, "speed": 120,
     "crit_rate": 15, "crit_damage": 50, "awaken_level": 1,
     "leader_skill": {"attribute": "SPD", "amount": 24, "area": "All"}},
    {"id": 2, "com2us_id": 100116, "name": "Tower", "element": "Pure",
     "base_hp": 1000, "base_attack": 0, "base_defense": 0, "speed": 150,
     "crit_rate": 0, "crit_damage": 0, "awaken_level": 0,
     "leader_skill": None},
]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_db = monsters.DB_PATH
        self._orig_cache = monsters.load_swarfarm_cache
        self._orig_cache_file = monsters.SWARFARM_CACHE
        monsters.DB_PATH = Path(self._tmp.name) / "sw_data.db"
        monsters.SWARFARM_CACHE = Path(self._tmp.name) / "swarfarm_cache.json"
        monsters.load_swarfarm_cache = lambda: [dict(e) for e in ENTRIES]

    def tearDown(self):
        monsters.DB_PATH = self._orig_db
        monsters.SWARFARM_CACHE = self._orig_cache_file
        monsters.load_swarfarm_cache = self._orig_cache
        self._tmp.cleanup()

    def test_creates_db_when_missing(self):
        self.assertFalse(monsters.DB_PATH.is_file())
        self.assertTrue(monsters.ensure_local_db())
        self.assertTrue(monsters.DB_PATH.is_file())
        roster = monsters._load_local_db()
        self.assertIn(16114, roster)
        self.assertEqual(roster[16114].speed, 120)
        self.assertEqual(roster[16114].name, "Lora")
        self.assertNotIn(100116, roster)  # excluded at roster level

    def test_noop_when_db_exists(self):
        self.assertTrue(monsters.ensure_local_db())
        self.assertFalse(monsters.ensure_local_db())

    def test_schema_compatible_with_parent(self):
        self.assertTrue(monsters.ensure_local_db())
        import sqlite3
        con = sqlite3.connect(str(monsters.DB_PATH))
        cols = [r[1] for r in con.execute("PRAGMA table_info(monsters)")]
        con.close()
        for col in ("com2us_id", "name", "element", "base_hp", "base_attack",
                    "base_defense", "speed", "crit_rate", "crit_damage",
                    "awaken_level", "ls_attribute", "ls_amount", "ls_area",
                    "ls_element"):
            self.assertIn(col, cols)


class MappingTests(unittest.TestCase):
    def test_mapping_bundled_in_repo(self):
        self.assertTrue(MAPPING_PATH.is_file())
        self.assertEqual(MAPPING_PATH, BASE_DIR / "mapping.json")


if __name__ == "__main__":
    unittest.main()
