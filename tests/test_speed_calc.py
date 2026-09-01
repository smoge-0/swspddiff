"""Unit tests for the speed math (planning_doc.md worked examples)."""

import unittest

from speed_calc import compare_race, needed_rune_spd, passive_bonus


class CompareRaceTests(unittest.TestCase):
    def test_doc_example_lora_vs_triton(self):
        # Lora 120 / 24 lead vs Triton 116 / 24 lead -> 197 vs 191, diff +6
        res = compare_race("Lora", 120, 24, "Triton", 116, 24)
        self.assertEqual(res.mon1_race, 197)
        self.assertEqual(res.mon2_race, 191)
        self.assertEqual(res.diff, 6)
        self.assertEqual(res.winner, "mon1")
        self.assertEqual(res.passive_notes, [])

    def test_doc_example_reversed(self):
        res = compare_race("Triton", 116, 24, "Lora", 120, 24)
        self.assertEqual(res.diff, -6)
        self.assertEqual(res.winner, "mon2")

    def test_no_lead(self):
        res = compare_race("Lora", 120, 0, "Triton", 116, 0)
        self.assertEqual(res.mon1_race, 168)  # ceil(120*1.4)
        self.assertEqual(res.mon2_race, 163)  # ceil(116*1.4)
        self.assertEqual(res.diff, 5)

    def test_tie(self):
        res = compare_race("Lora", 120, 24, "Lora", 120, 24)
        self.assertEqual(res.diff, 0)
        self.assertEqual(res.winner, "tie")

    def test_chilling_field1_passive_on_real_totals(self):
        # Chilling race 166 (ceil 101*1.64); +39 passive -> 205 vs Triton 191
        res = compare_race("Chilling", 101, 24, "Triton", 116, 24)
        self.assertEqual(res.mon1_race, 166)  # displayed, passive hidden
        self.assertEqual(res.mon2_race, 191)
        self.assertEqual(res.diff, 14)        # real totals (166+39) - 191
        self.assertEqual(res.winner, "mon1")
        self.assertEqual(res.passive_notes, ["Chilling gains +39 spd from two buffs."])

    def test_elsharion_field1(self):
        res = compare_race("Elsharion", 100, 24, "Triton", 116, 24)
        # race 164 (ceil 100*1.64); +25 passive -> 189 vs 191
        self.assertEqual(res.mon1_race, 164)
        self.assertEqual(res.diff, -2)
        self.assertEqual(res.winner, "mon2")
        self.assertEqual(res.passive_notes, ["Elsharion gains +25 spd."])


class NeededRuneSpdTests(unittest.TestCase):
    def test_doc_example(self):
        # Lora 120, 24 lead, +220 -> total 387; Triton 116, 24 lead needs 225
        res = needed_rune_spd("Lora", 120, 24, 220, "Triton", 116, 24)
        self.assertEqual(res.bonus1, 47)   # ceil(120*0.39)
        self.assertEqual(res.bonus2, 46)   # ceil(116*0.39)
        self.assertEqual(res.total1, 387)
        self.assertEqual(res.raw_needed, 225)
        self.assertEqual(res.needed, 225)
        self.assertFalse(res.already_faster)

    def test_doc_chilling_example_259_shown_as_220(self):
        # mon1 Lora +233 (total 400); Chilling (101) raw 259, displayed 220
        res = needed_rune_spd("Lora", 120, 24, 233, "Chilling", 101, 24)
        self.assertEqual(res.bonus2, 40)   # ceil(101*0.39)
        self.assertEqual(res.total1, 400)
        self.assertEqual(res.raw_needed, 259)
        self.assertEqual(res.needed, 220)  # passive hidden in the output
        self.assertEqual(res.passive_notes, ["Chilling gains +39 spd from two buffs."])

    def test_elsharion(self):
        res = needed_rune_spd("Lora", 120, 24, 233, "Elsharion", 100, 24)
        self.assertEqual(res.bonus2, 39)   # ceil(100*0.39)
        self.assertEqual(res.raw_needed, 261)
        self.assertEqual(res.needed, 236)  # 261 - 25
        self.assertEqual(res.passive_notes, ["Elsharion gains +25 spd."])

    def test_mon1_with_passive_raises_need(self):
        # mon1 Chilling: real total includes +39 -> mon2 needs more
        res = needed_rune_spd("Chilling", 101, 24, 220, "Triton", 116, 24)
        self.assertEqual(res.total1, 101 + 40 + 220 + 39)
        self.assertEqual(res.needed, res.raw_needed)  # Triton has no passive
        self.assertEqual(res.raw_needed, 101 + 40 + 220 + 39 - 116 - 46)

    def test_already_faster_unruned(self):
        # Lora 0 lead +0 (total 138) vs Triton 24 lead -> negative needed
        res = needed_rune_spd("Lora", 120, 0, 0, "Triton", 116, 24)
        self.assertEqual(res.total1, 120 + 18)  # ceil(120*0.15)
        self.assertEqual(res.raw_needed, 138 - 116 - 46)
        self.assertLess(res.needed, 0)
        self.assertTrue(res.already_faster)

    def test_pure_tower_bonus_rounding(self):
        res = needed_rune_spd("Lora", 120, 0, 100, "Triton", 116, 0)
        self.assertEqual(res.bonus1, 18)   # ceil(120*0.15)
        self.assertEqual(res.bonus2, 18)   # ceil(116*0.15)
        self.assertEqual(res.total1, 120 + 18 + 100)


class PassiveBonusTests(unittest.TestCase):
    def test_lookup(self):
        self.assertEqual(passive_bonus("Chilling"), 39)
        self.assertEqual(passive_bonus("Elsharion"), 25)
        self.assertEqual(passive_bonus("Lora"), 0)


if __name__ == "__main__":
    unittest.main()
