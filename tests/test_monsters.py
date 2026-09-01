"""Roster tests against the real ../sw_data.db + mapping.json."""

import unittest

from monsters import Roster, _is_excluded, load_roster


class RosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load_roster()

    def test_roster_size(self):
        self.assertGreater(len(self.roster), 2500)

    def test_doc_units_present_with_correct_base_speeds(self):
        lora = self.roster.resolve("16114")
        triton = self.roster.resolve("19713")
        chilling = self.roster.resolve("20711")
        elsharion = self.roster.resolve("19214")
        self.assertIsNotNone(lora)
        self.assertIsNotNone(triton)
        self.assertIsNotNone(chilling)
        self.assertIsNotNone(elsharion)
        self.assertEqual(lora.speed, 120)
        self.assertEqual(triton.speed, 116)
        self.assertEqual(chilling.speed, 101)
        self.assertEqual(elsharion.speed, 100)

    def test_resolve_formats(self):
        self.assertEqual(self.roster.resolve("Lora").com2us_id, 16114)
        self.assertEqual(self.roster.resolve("Lora (Light, 120)").com2us_id, 16114)
        self.assertEqual(self.roster.resolve("Water Chilling").name, "Chilling")
        self.assertEqual(self.roster.resolve("not-a-monster"), None)

    def test_search_case_insensitive(self):
        hits = self.roster.search("lora")
        self.assertTrue(hits)
        self.assertEqual(hits[0].name, "Lora")
        self.assertIn(hits[0].element, {"Light", "Dark", "Fire", "Water", "Wind"})

    def test_nonplayable_excluded(self):
        for query in ("Tower", "Incarnation", "Small Crystal", "Homunculus"):
            for mon in self.roster.search(query, limit=100):
                if mon.name == "Homunculus(Attack)" or mon.name == "Homunculus(Support)":
                    continue  # homunculi are playable
                self.assertNotIn(query.lower(), mon.name.lower())

    def test_fodder_excluded(self):
        for name in ("Angelmon", "Devilmon", "King Angelmon",
                     "Rainbowmon", "Super Angelmon"):
            self.assertIsNone(self.roster.resolve(name), name)

    def test_all_names_english_and_speed_positive(self):
        for mon in self.roster.by_id.values():
            # allow ASCII + Latin accents (Übel, Pavé); reject Hangul/CJK/Greek
            latin = lambda c: ord(c) < 0x2B0 or 0x1E00 <= ord(c) < 0x1F00
            self.assertTrue(all(latin(c) for c in mon.name),
                            f"non-Latin name: {mon.name!r}")
            self.assertGreater(mon.speed, 0, mon)

    def test_new_monster_english_name_via_mapping(self):
        belial = self.roster.resolve("Belial")  # awakened Dark Demon (23211)
        self.assertIsNotNone(belial)
        demon = self.roster.resolve("Demon")    # unawakened family name
        self.assertIsNotNone(demon)


class ExclusionTests(unittest.TestCase):
    def test_families(self):
        self.assertTrue(_is_excluded(100116))    # Tower
        self.assertTrue(_is_excluded(210106))    # Small Crystal
        self.assertTrue(_is_excluded(110306))    # Incarnation
        self.assertFalse(_is_excluded(16114))    # Lora
        self.assertFalse(_is_excluded(1000101))  # Homunculus(Attack)


if __name__ == "__main__":
    unittest.main()
