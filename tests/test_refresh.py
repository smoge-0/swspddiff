"""Swarfarm hybrid-refresh merge tests (no network — fixtures only)."""

import unittest

from monsters import Monster, merge_swarfarm_entries, _is_excluded


LORA = Monster(16114, "Lora", "Light", 120, 1)
TRITON = Monster(19713, "Triton", "Wind", 116, 1)


class MergeTests(unittest.TestCase):
    def test_adds_missing_and_keeps_existing(self):
        roster = {16114: LORA, 19713: TRITON}
        entries = [
            {"com2us_id": 16114, "name": "Lora (renamed?)", "element": "Light",
             "speed": 999, "awaken_level": 1},          # existing -> ignored
            {"com2us_id": 23211, "name": "Belial", "element": "Dark",
             "speed": 103, "awaken_level": 1},           # new -> added
            {"com2us_id": 100116, "name": "Tower", "element": "Pure",
             "speed": 150, "awaken_level": 0},           # excluded -> skipped
            {"com2us_id": 99999, "name": "Bad", "element": None,
             "speed": None},                             # malformed -> skipped
        ]
        merged = merge_swarfarm_entries(roster, entries)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[16114].speed, 120)       # not overridden
        self.assertEqual(merged[23211].name, "Belial")
        self.assertNotIn(100116, merged)
        self.assertNotIn(99999, merged)

    def test_adds_missing_but_does_not_override_existing(self):
        roster = {16114: LORA}
        merged = merge_swarfarm_entries(roster, [{
            "com2us_id": 16114, "name": "Changed", "element": "Light",
            "speed": 120, "awaken_level": 1,
        }])
        self.assertEqual(merged[16114], LORA)


if __name__ == "__main__":
    unittest.main()
