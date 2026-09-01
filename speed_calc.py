"""Speed math — pure functions, no discord imports (planning_doc.md).

Field 1 (no rune_spd given): both units assumed on Swift, compare
    race_spd = ceil(base * (1 + tower + swift + lead))
Field 2 (mon1_rune_spd given): the rune_spd value already includes the swift
    set bonus, so only tower + lead scale the base:
    bonus = ceil(base * (tower + lead))
    total = base + bonus + rune_spd
    mon2 needed = mon1 total - mon2 base - mon2 bonus

Passives (Chilling +39, Elsharion +25) are applied to the *real* totals that
decide winner/diff/needed, but are invisible in the displayed numbers: the
displayed needed rune spd for a passive monster is raw_needed - passive
(doc: "+259 chilling should be shown as +220 chilling in results").
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
    total1: int           # real mon1 total (passive included)
    bonus1: int
    bonus2: int
    raw_needed: int       # rune spd mon2 needs vs real mon1 total, pre-hiding
    needed: int           # displayed rune spd (passive hidden)
    passive_notes: list[str] = field(default_factory=list)

    @property
    def already_faster(self) -> bool:
        return self.needed <= 0


def _race_spd(base: int, lead: int) -> int:
    """Field-1 speed: ceil(base * (1 + tower + swift + lead/100))."""
    return math.ceil(base * (1.0 + TOWER_BONUS + SWIFT_BONUS + lead / 100.0))


def _bonus(base: int, lead: int) -> int:
    """Field-2 % bonus: ceil(base * (tower + lead/100)); swift inside rune_spd."""
    return math.ceil(base * (TOWER_BONUS + lead / 100.0))


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


def needed_rune_spd(
    mon1_name: str, mon1_base: int, mon1_lead: int, rune1: int,
    mon2_name: str, mon2_base: int, mon2_lead: int,
) -> NeededResult:
    """Field 2: what rune spd does mon2 need to catch/outspeed mon1?"""
    p1, p2 = passive_bonus(mon1_name), passive_bonus(mon2_name)
    bonus1 = _bonus(mon1_base, mon1_lead)
    bonus2 = _bonus(mon2_base, mon2_lead)
    total1 = mon1_base + bonus1 + rune1 + p1          # real mon1 total
    raw_needed = total1 - mon2_base - bonus2          # mon2 rune spd vs that
    needed = raw_needed - p2                          # hidden-passive display
    notes = [PASSIVE_NOTE[n] for n in (mon1_name, mon2_name) if n in PASSIVE_NOTE]
    return NeededResult(
        mon1_name=mon1_name, mon2_name=mon2_name,
        mon1_lead=mon1_lead, mon2_lead=mon2_lead,
        rune1=rune1, total1=total1, bonus1=bonus1, bonus2=bonus2,
        raw_needed=raw_needed, needed=needed, passive_notes=notes,
    )
