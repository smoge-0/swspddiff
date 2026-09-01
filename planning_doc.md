**Speed diff discord bot**

Discord bot to compare speeds between units.

The bot should take the following inputs:

/mon1
/mon1_lead
/mon1_rune_spd (optional)
/mon2
/mon2_lead

and return the following information

1. which unit is faster and what the speed diff is
2. if mon1spd defined, determine what spd mon2 needs to be to outspeed mon1

The list of units to choose from should be a dropdown generated from swarfarm api, and should autopopulate dynamically as the monster is typed in.

The speed calculation needs to take into account two factors:

1. the difference between the two unit base speeds
(unit base speeds should be bas)
2. the difference between leads
3. tower (15% of base)

Example cases:
/mon1 = Lora (120 base)
/mon1_lead = 24
/mon1_rune_spd = 220
/mon2 = Triton (116 base)
/mon2_lead = 24

calculations:
# user input fields
mon1_lead_bonus = 0.24
mon2_lead_bonus = 0.24
# static fields
swift_bonus = 0.25
tower_bonus = 0.15
# swarfarm generated base speeds
mon1_base = 120
mon2_base = 116
# calculations
**roundUp (base * (1 + tower_bonus + swift_bonus + lead_bonus))**
mon1_spd = roundUp(120 * (1+0.15+0.24+0.25)) = roundUp(196.8) = 197
mon2_spd = 116 * (1+0.15+0.24+0.25) = roundUp(190.24) = 191
spd_diff = 197-191 = 6 (lora races +6)

# calculations for field 2 (always assume swift)

mon1_bonus_spd = roundup(mon1_base * (tower_bonus + lead_bonus)) = 120 * (0.24+0.15) = 46.8 (47)
mon1_total_spd = mon1_bonus_spd + mon1_rune_spd + mon1_base = 47 + 220 + 120 = 387

mon2_bonus_spd = roundup(mon2_base * (tower_bonus + lead_bonus + swift_bonus)) = 116 * (0.24+0.15) = 45.24 (46)
mon2_spd_needed = mon1_total_spd 
mon2_total_spd = mon2_bonus_spd + mon2_rune_spd + mon2_base
mon2_rune_spd = mon2_total_spd - mon2_bonus_spd - mon2_base = 387 - 46 - 116 =  225

Note: the +6 and -6 should be green or red depending on whether it's positive or negative
output:
24 lead Lora (+6)  vs 24 lead Triton (-6)
24 lead +220 Lora outspeeds 24 lead +225 triton

Special Cases:
If chilling is included in either mon1 or mon2, it has an extra spd bonus from passive (+39 spd),
and include a note "Chilling gains +39 spd from two buffs."
This bonus should be invisible in the output results. 
e.g. +259 chilling should be shown as +220 chilling in results

Similar for elsharion but +25 spd instead of +39
