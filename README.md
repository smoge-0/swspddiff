# Speed Race Discord bot

Discord bot to compare speeds between units, per `planning_doc.md`.

## Setup

```bash
# 1. Token: create a bot at https://discord.com/developers and copy the token
echo "DISCORD_TOKEN=your_token_here" > .env

# optional: guild id for instant (guild-scoped) command sync
echo "GUILD_ID=123456789012345678" >> .env

# 2. Run (uses the parent repo venv; only dependency is discord.py >= 2.7)
../sw_env/Scripts/python.exe bot.py
```

Invite the bot with the `applications.commands` scope. After it logs in it
registers the `/speedrace` command (guild-scoped if `GUILD_ID` is set, else
globally — global sync can take up to an hour to propagate).

## Usage

`/speedrace` with parameters:

| parameter       | required | meaning                                        |
|-----------------|----------|------------------------------------------------|
| `mon1`          | yes      | unit — autocomplete dropdown as you type       |
| `mon2`          | yes      | unit — autocomplete dropdown as you type       |
| `mon1_lead`     | yes      | mon1 leader skill SPD % (e.g. 24)              |
| `mon2_lead`     | yes      | mon2 leader skill SPD % (e.g. 24)              |
| `mon1_rune_spd` | no       | mon1 rune SPD incl. Swift set — when given, the bot reports what rune SPD mon2 needs to catch/outspeed mon1 |

Discord autocomplete works on command parameters, so the two monsters live on
one command (the "dropdown" is the autocomplete suggestion list).

### Field 1 — race comparison (no `mon1_rune_spd`)

Both units assumed on Swift, Tower 15% included:

```
race_spd = roundUp(base * (1 + 0.15 + 0.25 + lead/100))
```

Output, e.g. `24 lead Lora (+6) vs 24 lead Triton (-6)` with +6 green / -6 red
(tie shown uncolored — the attacker moves first on ties).

### Field 2 — needed SPD (when `mon1_rune_spd` given)

The rune SPD value already includes the Swift set bonus, so only Tower + lead
scale the base:

```
bonus     = roundUp(base * (0.15 + lead/100))
mon1 total = base + bonus + rune_spd
mon2 needs = mon1 total - mon2 base - mon2 bonus     (to tie)
           + 1                                       (to strictly outspeed)
```

Output, e.g. `24 lead +220 Lora outspeeds 24 lead +225 Triton`, plus a detail
line stating the total and the +1 for a strict outspeed.

### Special cases (Chilling / Elsharion)

Chilling gains +39 SPD and Elsharion +25 SPD from passives. The bonus counts in
the real totals that decide the winner / required SPD, but is **hidden** from
the displayed numbers — e.g. a raw `+259` need for Chilling is shown as `+220`
— and a note is appended ("Chilling gains +39 spd from two buffs.").

## Data sources (hybrid)

- **Primary:** `../sw_data.db` — level-40 base speeds (itself generated from
  the swarfarm API via `save_monster_list.py`); offline and instant.
- **Refresh:** on startup (when the `data/swarfarm_monsters.json` cache is
  older than 7 days) the bot paginates `https://swarfarm.com/api/v2/monsters/`
  in a background thread and **adds** monsters missing locally — existing
  entries are never overridden. Swarfarm being down never blocks the bot.
- Korean names in the db are translated via `../mapping.json` (family name for
  unawakened forms, individual name for awakened forms). Non-playable entities
  (towers, crystals, incarnations, bosses) are excluded; homunculi are kept.

## Run with Docker (optional)

Requires Docker with Compose v2. The image only contains the bot code; the
monster database and name mapping are mounted read-only from the parent repo,
so the container always uses the same data as your host (no rebuild needed
when `sw_data.db` is refreshed). See [`PROXMOX.md`](PROXMOX.md) for a full
step-by-step deploy on a Proxmox Debian LXC container.

```bash
cd speedrace_bot
echo "DISCORD_TOKEN=..." > .env          # same .env as the bare run
docker compose up -d --build             # build + start in background
docker compose logs -f                   # follow logs
docker compose down                      # stop (data volume is kept)
docker compose down -v                   # stop and delete the swarfarm cache
```

Container layout:

| path | what |
|---|---|
| `/app/speedrace_bot` | bot code (baked into the image) |
| `/app/sw_data.db`, `/app/mapping.json` | mounted read-only from `../` |
| `/app/speedrace_bot/data` | swarfarm cache (named volume `speedrace-data`, survives restarts) |

## Tests

```bash
../sw_env/Scripts/python.exe -m unittest discover -s tests -t .
```
