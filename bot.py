"""Speed race Discord bot — /speedrace with autocomplete monster search.

Run:  ../sw_env/Scripts/python.exe bot.py
Requires DISCORD_TOKEN (env or .env); optional GUILD_ID for instant command sync.
"""

from __future__ import annotations

import logging
import sys
import threading

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID
from monsters import Roster, load_roster, refresh_from_swarfarm
from speed_calc import compare_race, needed_rune_spd

log = logging.getLogger("speedrace")

GREEN, RED, AMBER, RESET = "\u001b[32m", "\u001b[31m", "\u001b[33m", "\u001b[0m"


def _ansi(text: str, color: str) -> str:
    code = {"green": GREEN, "red": RED, "amber": AMBER}[color]
    return f"{code}{text}{RESET}"


def _block(line: str) -> str:
    return f"```ansi\n{line}\n```"


def _diff_token(diff: int) -> str:
    return f"+{diff}" if diff > 0 else str(diff)


def _fmt_mon(lead: int, name: str) -> str:
    return f"{lead} lead {name}"


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

_roster: Roster = load_roster()


def _background_refresh() -> None:
    """Hybrid swarfarm refresh; never blocks commands, never crashes."""
    global _roster
    try:
        added = refresh_from_swarfarm()
        if added > 0:
            _roster = load_roster()
            log.info("roster refreshed from swarfarm cache (%d monsters)", len(_roster))
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("background swarfarm refresh failed: %s", exc)


async def monster_autocomplete(
    interaction: discord.Interaction, current: str,
) -> list[app_commands.Choice[str]]:
    hits = _roster.search(current, limit=25)
    return [
        app_commands.Choice(
            name=f"{m.name} ({m.element}, {m.speed} SPD)",
            value=str(m.com2us_id),
        )
        for m in hits
    ]


@bot.event
async def on_ready() -> None:
    log.info("logged in as %s", bot.user)
    guild = discord.Object(id=GUILD_ID) if GUILD_ID else None
    try:
        synced = await bot.tree.sync(guild=guild)
        log.info("synced %d command(s)%s", len(synced), " (guild)" if guild else "")
    except discord.DiscordException as exc:
        log.warning("command sync failed (retry later): %s", exc)
    threading.Thread(target=_background_refresh, daemon=True).start()


@bot.tree.command(
    name="speedrace",
    description="Compare two units' speeds (both assumed on Swift, Tower 15% included)",
)
@app_commands.describe(
    mon1="First unit — start typing to search",
    mon2="Second unit — start typing to search",
    mon1_lead="mon1 leader skill SPD % (e.g. 24)",
    mon2_lead="mon2 leader skill SPD % (e.g. 24)",
    mon1_rune_spd="mon1 rune SPD incl. Swift set (optional) — computes what mon2 needs",
)
@app_commands.autocomplete(mon1=monster_autocomplete, mon2=monster_autocomplete)
async def speedrace(
    interaction: discord.Interaction,
    mon1: str,
    mon2: str,
    mon1_lead: int,
    mon2_lead: int,
    mon1_rune_spd: int | None = None,
) -> None:
    await interaction.response.defer()

    if not 0 <= mon1_lead <= 100 or not 0 <= mon2_lead <= 100:
        await interaction.followup.send("Lead skills must be between 0 and 100.", ephemeral=True)
        return
    if mon1_rune_spd is not None and mon1_rune_spd < 0:
        await interaction.followup.send("Rune SPD can't be negative.", ephemeral=True)
        return

    m1 = _roster.resolve(mon1)
    m2 = _roster.resolve(mon2)
    if m1 is None or m2 is None:
        missing = [q for q, m in ((mon1, m1), (mon2, m2)) if m is None]
        await interaction.followup.send(
            f"Couldn't find: {', '.join(missing)}. Pick from the autocomplete dropdown.",
            ephemeral=True,
        )
        return

    if mon1_rune_spd is None:
        embed = _build_race_embed(m1, m2, mon1_lead, mon2_lead)
    else:
        embed = _build_needed_embed(m1, m2, mon1_lead, mon2_lead, mon1_rune_spd)
    await interaction.followup.send(embed=embed)


def _race_line(m1, m2, lead1: int, lead2: int) -> str:
    """Doc output line 1: '24 lead Lora (+6)  vs  24 lead Triton (-6)'."""
    res = compare_race(m1.name, m1.speed, lead1, m2.name, m2.speed, lead2)
    p1, p2 = _fmt_mon(lead1, m1.name), _fmt_mon(lead2, m2.name)
    token1, token2 = _diff_token(res.diff), _diff_token(-res.diff)
    c1 = "green" if res.diff > 0 else ("red" if res.diff < 0 else "amber")
    c2 = "red" if res.diff > 0 else ("green" if res.diff < 0 else "amber")
    return f"{p1} ({_ansi(token1, c1)})  vs  {p2} ({_ansi(token2, c2)})"


def _build_race_embed(m1, m2, lead1: int, lead2: int) -> discord.Embed:
    res = compare_race(m1.name, m1.speed, lead1, m2.name, m2.speed, lead2)
    color = discord.Color.green() if res.winner == "mon1" \
        else discord.Color.red() if res.winner == "mon2" else discord.Color.dark_gray()
    embed = discord.Embed(title="⚡ Speed Race", color=color)
    embed.description = _block(_race_line(m1, m2, lead1, lead2))
    for note in res.passive_notes:
        embed.add_field(name="Passive", value=note, inline=False)
    return embed


def _build_needed_embed(m1, m2, lead1: int, lead2: int, rune1: int) -> discord.Embed:
    res = needed_rune_spd(m1.name, m1.speed, lead1, rune1, m2.name, m2.speed, lead2)
    # Doc output line 2: '24 lead +220 Lora outspeeds 24 lead +225 Triton'
    needed_line = (f"{lead1} lead +{rune1} {m1.name}  outspeeds  "
                   f"{lead2} lead +{res.needed} {m2.name}")
    color = discord.Color.green()
    embed = discord.Embed(title="⚡ Speed Check", color=color)
    embed.description = _block(f"{_race_line(m1, m2, lead1, lead2)}\n{needed_line}")
    for note in res.passive_notes:
        embed.add_field(name="Passive", value=note, inline=False)
    return embed


def main() -> None:
    if not DISCORD_TOKEN:
        sys.exit("DISCORD_TOKEN is not set (use env var or .env)")
    logging.basicConfig(level=logging.INFO)
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
