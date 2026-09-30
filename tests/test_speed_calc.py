"""Unit tests for the speed math (planning_doc.md worked examples)."""

import unittest

from speed_calc import (
    _combat_spd,
    _swift_correction,
    compare_race,
    needed_rune_spd,
    passive_bonus,
)


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
        self.assertEqual(res.total1, 387)
        self.assertEqual(res.raw_needed, 225)
        self.assertEqual(res.needed, 225)
        self.assertFalse(res.already_faster)

    def test_chilling_passive_hidden_in_display(self):
        # mon1 Lora +233 (total 400): Chilling's own +39 is counted for the real
        # requirement but hidden from the shown figure
        res = needed_rune_spd("Lora", 120, 24, 233, "Chilling", 101, 24)
        self.assertEqual(res.total1, 400)
        self.assertEqual(res.needed, 221)      # displayed (passive counted)
        self.assertEqual(res.raw_needed, 260)  # same, passive treated invisible
        self.assertEqual(res.passive_notes, ["Chilling gains +39 spd from two buffs."])

    def test_elsharion(self):
        # Elsharion base 100 has no Swift fraction -> linear model coincides
        res = needed_rune_spd("Lora", 120, 24, 233, "Elsharion", 100, 24)
        self.assertEqual(res.raw_needed, 261)
        self.assertEqual(res.needed, 236)      # 261 - 25
        self.assertEqual(res.passive_notes, ["Elsharion gains +25 spd."])

    def test_mon1_with_passive_raises_need(self):
        # mon1 Chilling (base 101): real total includes +39 and the swift fix
        res = needed_rune_spd("Chilling", 101, 24, 220, "Triton", 116, 24)
        self.assertEqual(res.total1, 399)      # ceil(101*1.39 + 220 - 0.75) + 39
        self.assertEqual(res.needed, 237)

    def test_already_faster_unruned(self):
        # Lora 0 lead +0 (total 138) vs Triton 24 lead
        res = needed_rune_spd("Lora", 120, 0, 0, "Triton", 116, 24)
        self.assertEqual(res.total1, 138)
        self.assertEqual(res.needed, 0)
        self.assertTrue(res.already_faster)

    def test_pure_tower_bonus_only(self):
        res = needed_rune_spd("Lora", 120, 0, 100, "Triton", 116, 0)
        self.assertEqual(res.total1, 238)      # ceil(120*1.15 + 100)


class SwiftCorrectionTests(unittest.TestCase):
    def test_correction_values(self):
        # fractional swift: 101 * 0.25 = 25.25 -> 0.75 ; 106 * 0.25 = 26.5 -> 0.5
        self.assertAlmostEqual(_swift_correction(101), 0.75)
        self.assertAlmostEqual(_swift_correction(106), 0.5)
        # whole-number swift fractions need no correction
        self.assertEqual(_swift_correction(120), 0.0)   # 30.0
        self.assertEqual(_swift_correction(116), 0.0)   # 29.0
        self.assertEqual(_swift_correction(100), 0.0)   # 25.0

    def test_combat_spd_matches_doc_and_game(self):
        # doc's Lora example: integer swift fraction -> unchanged
        self.assertEqual(_combat_spd(120, 24, 220), 387)
        # Chilling: single ceil over the exact 25.25 fraction
        self.assertEqual(_combat_spd(101, 10, 220), 346)

    def test_chilling_vs_fiona_regression(self):
        # reported case: 10 lead +220 Chilling vs 28 lead Fiona
        race = compare_race("Chilling", 101, 10, "Fiona", 106, 28)
        self.assertEqual(race.mon1_race, 152)
        self.assertEqual(race.mon2_race, 179)
        self.assertEqual(race.diff, 12)          # 152 + 39 passive - 179
        res = needed_rune_spd("Chilling", 101, 10, 220, "Fiona", 106, 28)
        self.assertEqual(res.total1, 385)        # was 386 before the fix
        self.assertEqual(res.needed, 233)        # was 234 before the fix
        self.assertEqual(res.raw_needed, 233)    # Fiona has no passive


class PassiveBonusTests(unittest.TestCase):
    def test_lookup(self):
        self.assertEqual(passive_bonus("Chilling"), 39)
        self.assertEqual(passive_bonus("Elsharion"), 25)
        self.assertEqual(passive_bonus("Lora"), 0)


if __name__ == "__main__":
    unittest.main()
