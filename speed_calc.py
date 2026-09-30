"""Speed math — pure functions, no discord imports (planning_doc.md).

Field 1 (no rune_spd given): both units assumed on Swift, compare
    race_spd = ceil(base * (1 + tower + swift + lead))
Field 2 (mon1_rune_spd given): the entered rune_spd already includes the Swift
    set bonus as the game displays it, so only tower + lead scale the base and
    the game's single ceil is modelled by correcting that displayed value
    (swcalc.cz mechanics):

    combat      = ceil(base * (1 + tower + lead) + rune_spd - swift_correction)
    correction  = 1 - (base * 0.25) % 1        (0 when base * 0.25 is whole)
    mon2 needed = smallest integer rune_spd whose combat speed reaches mon1's

    The game applies one ceil over the *exact* Swift fraction (25% of base —
    e.g. 101 -> 25.25), while the displayed rune speed already carries that
    fraction rounded up (+26 in that example). Adding the raw value would count
    the remainder twice, so the remainder is removed first. Bases where
    base * 0.25 is a whole number (e.g. Lora 120 -> 30) are unaffected.

Passives (Chilling +39, Elsharion +25) are applied to the *real* totals that
decide winner/diff/needed, but are invisible in the displayed numbers: the
displayed needed rune spd for a passive monster is raw_needed - passive, per
planning_doc.md ("the bonus should be invisible in the output results").
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from config import PASSIVE_NOTE, PASSIVE_SPD, SWIFT_BONUS, TOWER_BONUS


def passive_bonus(name: str) -> int:
    return PASSIVE_SPD.get(name, 0)


@dataclass(frozen=True)
class RaceResult:
    mon1_name: str
    mon2_name: str
    mon1_lead: int
    mon2_lead: int
    mon1_race: int        # displayed race spd (passive excluded)
    mon2_race: int        # displayed race spd (passive excluded)
    mon1_base: int
    mon2_base: int
    diff: int             # real diff, passive included (mon1 - mon2)
    winner: str           # "mon1" | "mon2" | "tie"
    passive_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NeededResult:
    mon1_name: str
    mon2_name: str
    mon1_lead: int
    mon2_lead: int
    rune1: int
    total1: int           # real mon1 combat speed (passive included)
    raw_needed: int       # rune spd mon2 needs vs real mon1 total, pre-hiding
    needed: int           # displayed rune spd (passive hidden)
    passive_notes: list[str] = field(default_factory=list)

    @property
    def already_faster(self) -> bool:
        return self.needed <= 0


def _race_spd(base: int, lead: int) -> int:
    """Field-1 speed: ceil(base * (1 + tower + swift + lead/100))."""
    return math.ceil(base * (1.0 + TOWER_BONUS + SWIFT_BONUS + lead / 100.0))


def _swift_correction(base: int) -> float:
    """Amount to remove from a displayed rune SPD to match the game's rounding.

    The game ceils once over the exact Swift fraction (25% of base); an entered
    rune SPD already contains that fraction rounded up, so the leftover has to
    be subtracted to avoid counting it twice.
    """
    frac = (base * SWIFT_BONUS) % 1.0
    return (1.0 - frac) if frac > 0.0 else 0.0


def _combat_spd(base: int, lead: int, rune_spd: float) -> int:
    """Field-2 combat speed: ceil(base*(1+tower+lead) + rune_spd - correction).

    ``rune_spd`` is the *displayed* rune speed (Swift set bonus included).
    """
    return math.ceil(
        base * (1.0 + TOWER_BONUS + lead / 100.0) + rune_spd - _swift_correction(base)
    )


def compare_race(
    mon1_name: str, mon1_base: int, mon1_lead: int,
    mon2_name: str, mon2_base: int, mon2_lead: int,
) -> RaceResult:
    """Field 1: which unit races faster and by how much."""
    p1, p2 = passive_bonus(mon1_name), passive_bonus(mon2_name)
    r1, r2 = _race_spd(mon1_base, mon1_lead), _race_spd(mon2_base, mon2_lead)
    eff1, eff2 = r1 + p1, r2 + p2
    diff = eff1 - eff2
    winner = "tie" if diff == 0 else ("mon1" if diff > 0 else "mon2")
    notes = [PASSIVE_NOTE[n] for n in (mon1_name, mon2_name) if n in PASSIVE_NOTE]
    return RaceResult(
        mon1_name=mon1_name, mon2_name=mon2_name,
        mon1_lead=mon1_lead, mon2_lead=mon2_lead,
        mon1_race=r1, mon2_race=r2, mon1_base=mon1_base, mon2_base=mon2_base,
        diff=diff, winner=winner, passive_notes=notes,
    )


def _min_rune_spd(base: int, lead: int, target: int) -> int:
    """Smallest integer rune spd whose combat speed reaches ``target``."""
    seed = target - base * (1.0 + TOWER_BONUS + lead / 100.0)
    n = max(0, math.ceil(seed))
    # settle exactly (also absorbs floating-point noise around the ceil edge)
    while n > 0 and _combat_spd(base, lead, n - 1) >= target:
        n -= 1
    while _combat_spd(base, lead, n) < target:
        n += 1
    return n


def needed_rune_spd(
    mon1_name: str, mon1_base: int, mon1_lead: int, rune1: int,
    mon2_name: str, mon2_base: int, mon2_lead: int,
) -> NeededResult:
    """Field 2: what rune spd does mon2 need to catch/outspeed mon1?"""
    p1, p2 = passive_bonus(mon1_name), passive_bonus(mon2_name)
    total1 = _combat_spd(mon1_base, mon1_lead, rune1) + p1   # real mon1 total
    # displayed value: the rune spd mon2 actually needs, its own passive
    # included (doc: "+220 chilling")
    needed = _min_rune_spd(mon2_base, mon2_lead, total1 - p2)
    # same figure with the passive treated as invisible (doc: "+259 chilling")
    raw_needed = needed + p2
    notes = [PASSIVE_NOTE[n] for n in (mon1_name, mon2_name) if n in PASSIVE_NOTE]
    return NeededResult(
        mon1_name=mon1_name, mon2_name=mon2_name,
        mon1_lead=mon1_lead, mon2_lead=mon2_lead,
        rune1=rune1, total1=total1,
        raw_needed=raw_needed, needed=needed, passive_notes=notes,
    )
