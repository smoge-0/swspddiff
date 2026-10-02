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

    def test_resolve_selection_accepts_dropdown_id_only(self):
        # the autocomplete submits the com2us_id as the option value
        self.assertEqual(self.roster.resolve_selection("16114").name, "Lora")
        self.assertEqual(self.roster.resolve_selection(" 16114 ").name, "Lora")
        self.assertIsNotNone(self.roster.resolve_selection("20711"))

    def test_resolve_selection_rejects_free_typed_text(self):
        for value in ("Lora", "Lora (Light, 120)", "Water Chilling",
                      "lora", "Zenitsu", "", "   ", "abc", "-1", "1e5"):
            self.assertIsNone(self.roster.resolve_selection(value), repr(value))

    def test_resolve_selection_rejects_unknown_id(self):
        self.assertIsNone(self.roster.resolve_selection("99999999"))
        self.assertIsNone(self.roster.resolve_selection("0"))

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

    def test_search_prefers_higher_awaken_level(self):
        # Zenitsu Agatsuma: unawakened 32201-32205 (105) vs awakened 32211-32215 (106)
        hits = self.roster.search("zenitsu")
        self.assertEqual(len(hits), 5)
        for mon in hits:
            self.assertEqual(mon.awaken_level, 1, mon)
            self.assertEqual(mon.speed, 106, mon)
        self.assertEqual({m.com2us_id for m in hits},
                         {32211, 32212, 32213, 32214, 32215})

    def test_resolve_zenitsu_uses_awakened_form(self):
        mon = self.roster.resolve("Zenitsu")
        self.assertIsNotNone(mon)
        self.assertEqual(mon.awaken_level, 1)
        self.assertEqual(mon.speed, 106)

    def test_search_has_no_duplicate_name_element_pairs(self):
        for query in ("zenitsu", "fairy", "slime", "lora", "a"):
            hits = self.roster.search(query, limit=1000)
            keys = [(m.name, m.element) for m in hits]
            self.assertEqual(len(keys), len(set(keys)), query)

    def test_search_never_returns_lower_awaken_variant(self):
        # every name/element group with several entries must resolve to the
        # highest awaken level, never a lower one
        from collections import defaultdict
        groups: dict[tuple[str, str], list] = defaultdict(list)
        for mon in self.roster.by_id.values():
            groups[(mon.name, mon.element)].append(mon)
        dupes = [key for key, members in groups.items() if len(members) > 1]
        self.assertTrue(dupes, "expected units with unawakened/awakened pairs")
        for name, element in dupes:
            members = groups[(name, element)]
            best = max(members, key=lambda m: (m.awaken_level, m.com2us_id))
            hits = {m.com2us_id for m in self.roster.search(name, limit=1000)}
            self.assertIn(best.com2us_id, hits, (name, element))
            for mon in members:
                if (mon.awaken_level, mon.com2us_id) < (best.awaken_level, best.com2us_id):
                    self.assertNotIn(mon.com2us_id, hits, (name, element))

    def test_ambiguous_names_flagged(self):
        # family names shared by 2+ elements get element disambiguation
        self.assertIn("Fairy", self.roster.ambiguous_names)
        self.assertIn("Slime", self.roster.ambiguous_names)
        self.assertIn("Werewolf", self.roster.ambiguous_names)
        # unique awakened names are not ambiguous
        for name in ("Lora", "Triton", "Chilling", "Elsharion", "Eshir", "Belial"):
            self.assertNotIn(name, self.roster.ambiguous_names, name)


class ExclusionTests(unittest.TestCase):
    def test_families(self):
        self.assertTrue(_is_excluded(100116))    # Tower
        self.assertTrue(_is_excluded(210106))    # Small Crystal
        self.assertTrue(_is_excluded(110306))    # Incarnation
        self.assertFalse(_is_excluded(16114))    # Lora
        self.assertFalse(_is_excluded(1000101))  # Homunculus(Attack)


if __name__ == "__main__":
    unittest.main()
