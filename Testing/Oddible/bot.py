import os
import sys
import requests
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

import requests
from requests.exceptions import RequestException, ReadTimeout, ConnectionError as ReqConnectionError


# ---------------- Project paths & imports ----------------

# This file: AI Picks Bot/Testing/Oddible/bot.py
# Root project: AI Picks Bot
BASE_DIR = Path(__file__).resolve().parents[2]      # -> AI Picks Bot
sys.path.append(str(BASE_DIR))

from DiscordBot.oddible.books import validate_books, prioritize_deeplink_books
from DiscordBot.oddible.utils import (
    dedupe_and_diversify,
    group_picks_by_type,
    select_group_picks,
    format_pick_line,
    parse_deeplinks,
    format_deeplink_block,
    GROUP_COLOURS,
    GROUP_LABELS,
    GROUP_ORDER,
)

# ---------------- Env & API setup ----------------

# Reuse your existing env file
load_dotenv(BASE_DIR / "DiscordBot" / "token.env")

DISCORD_TOKEN = os.getenv("TEST_DISCORD_TOKEN")
ODDIBLE_API_KEY = os.getenv("ODDIBLE_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("TEST_DISCORD_TOKEN is not set in DiscordBot/token.env")
if not ODDIBLE_API_KEY:
    raise RuntimeError("ODDIBLE_API_KEY is not set in DiscordBot/token.env")

ODDIBLE_URL = "https://api.dev.smartbettor.ai/api/oddible/trending"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": ODDIBLE_API_KEY,
}

requested_books = ["draftkings", "fanduel", "betmgm", "prizepicks", "underdog", "novig"]
books = validate_books(requested_books)
books = prioritize_deeplink_books(books, max_n=6)



def fetch_trending(leagues, num_picks=20, risk="moderate", sportsbooks=None, player_props=None):
    payload = {
        "leagues": leagues,
        "num_picks": num_picks,
        "sportsbooks": sportsbooks or ["draftkings"],
        "risk": risk,
    }
    if player_props is not None:
        payload["player_props"] = bool(player_props)

    try:
        # you can bump timeout if you want, but 20s is already kinda long
        resp = requests.post(ODDIBLE_URL, json=payload, headers=HEADERS, timeout=20)
        try:
            data = resp.json()
        except Exception:
            data = {"status": "error", "raw": resp.text}
        return resp.status_code, resp.headers, data

    except ReadTimeout:
        # Specific case: API too slow
        return 0, {}, {
            "status": "timeout",
            "message": "Request to Oddible timed out. The API may be slow or unavailable.",
        }
    except (ReqConnectionError, RequestException) as e:
        # Any other network-level problem
        return 0, {}, {
            "status": "error",
            "message": f"Network error talking to Oddible: {e}",
        }
# ---------------- Discord bot setup ----------------

intents = discord.Intents.default()
intents.message_content = True  # needed for prefix commands

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")
    print("Using sportsbooks:", books)
    print("------")


async def send_long_message(ctx, content: str):
    """Split long messages into 2000-char chunks for Discord."""
    if len(content) <= 2000:
        await ctx.send(content)
        return

    lines = content.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 2000:
            await ctx.send(chunk)
            chunk = line
        else:
            chunk = f"{chunk}\n{line}" if chunk else line
    if chunk:
        await ctx.send(chunk)

def build_pick_embed(p: dict, group_name: str, state: str = "ny") -> discord.Embed:
    """
    Turn a single Oddible pick into a card-style embed.
    Uses utils.format_pick_line() + multi-book deeplinks.
    """
    # Core text (2 lines: header + details)
    line = format_pick_line(p)
    parts = line.split("\n", 1)
    header = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    # Strip markdown ** from the title
    title = header.replace("**", "").strip()

    # Details (odds + hit rate)
    desc_lines = []
    if rest:
        desc_lines.append(rest.strip())

    # Deep links (multiple books, ordered by DEEPLINK_PRIORITY)
    deep_links = parse_deeplinks(p.get("deepLinks", ""))
    deeplink_block = format_deeplink_block(deep_links, state=state, max_books=3)
    if deeplink_block:
        desc_lines.append(deeplink_block)

    description = "\n".join(desc_lines) if desc_lines else None

    embed = discord.Embed(
        title=title,
        description=description,
        colour=GROUP_COLOURS.get(group_name, discord.Colour.blurple()),
    )

    footer_label = GROUP_LABELS.get(group_name, group_name.title())
    embed.set_footer(text=f"{footer_label} • Powered by Oddible")

    return embed


def build_grouped_pick_embeds(
    raw_json: dict,
    max_per_group: int = 3,
    state: str = "ny",
) -> dict:
    """
    From the Oddible /trending response, return:
      { "spread": [embed1, embed2, ...], "totals": [...], ... }
    where each embed is a single pick card.
    """
    data = raw_json.get("data") or {}
    picks = data.get("picks") or []
    if not picks:
        return {}

    # Global dedupe first
    deduped = dedupe_and_diversify(picks, max_out=len(picks))

    # Bucket by type (spread / totals / moneyline / player_props / other)
    groups = group_picks_by_type(deduped)

    grouped_embeds: dict = {}

    for gkey in GROUP_ORDER:
        bucket = groups.get(gkey, [])
        if not bucket:
            continue

        # Apply group-specific selection rules & cap per group
        bucket = select_group_picks(gkey, bucket, max_per_group)
        if not bucket:
            continue

        embeds = [build_pick_embed(p, gkey, state=state) for p in bucket]
        if embeds:
            grouped_embeds[gkey] = embeds

    return grouped_embeds


async def send_trending_as_embeds(
    ctx: commands.Context,
    league_label: str,
    raw_json: dict,
    state: str = "ny",
):
    grouped = build_grouped_pick_embeds(raw_json, max_per_group=3, state=state)

    if not grouped:
        await ctx.send(f"No picks available for **{league_label}** right now.")
        return

    # Top header text (like Outlier's "Top insights for ..." line)
    await ctx.send(f"Top insights 📈 for **{league_label}** tonight 👇")

    # For each group, send a header embed + its pick embeds (all in one message)
    for gkey in GROUP_ORDER:
        embeds_for_group = grouped.get(gkey)
        if not embeds_for_group:
            continue

        header_title = GROUP_LABELS.get(gkey, gkey.title())
        header_colour = GROUP_COLOURS.get(gkey, discord.Colour.blurple())

        header_embed = discord.Embed(
            title=header_title,
            description="",
            colour=header_colour,
        )

        # One message per group: [header] + the pick cards
        await ctx.send(embeds=[header_embed] + embeds_for_group)


async def send_grouped_embed(ctx, content: str):
    """
    Take the markdown string from build_discord_message_grouped()
    and send it as a clean Discord embed.

    If it's too long for a single embed description, fall back to
    the existing send_long_message() splitter.
    """
    # Split off the first line (title) from the rest
    lines = content.split("\n", 1)
    title_line = lines[0].strip()
    body = lines[1] if len(lines) > 1 else ""

    # Strip **bold** from the title if present
    if title_line.startswith("**") and title_line.endswith("**"):
        embed_title = title_line[2:-2].strip()
    else:
        embed_title = title_line

    body = body.strip()

    # If it fits inside one embed, send it nicely
    # (Discord limit is 4096; leaving a little margin)
    if body and len(body) <= 4000:
        embed = discord.Embed(
            title=embed_title,
            description=body,
            colour=discord.Colour.blurple(),
        )
        await ctx.send(embed=embed)
        return

    # Fallback: use the old plain-text chunking
    await send_long_message(ctx, content)


# ---------------- Commands ----------------

@bot.command(name="nba")
async def nba_cmd(ctx: commands.Context):
    """Get NBA main-market picks from Oddible."""
    await ctx.send("Fetching **NBA** picks from Oddible...")

    status, headers, data = fetch_trending(
        leagues=["NBA"],
        num_picks=20,
        risk="moderate",
        sportsbooks=books,
        player_props=None,
    )

    if status != 200:
        msg = data.get("message") or data.get("raw") or f"HTTP {status}"
        await ctx.send(f"⚠️ Oddible error: {msg}")
        return

    await send_trending_as_embeds(ctx, "NBA", data)


@bot.command(name="nfl")
async def nfl_cmd(ctx: commands.Context):
    """Get NFL main-market picks from Oddible."""
    await ctx.send("Fetching **NFL** picks from Oddible...")

    status, headers, data = fetch_trending(
        leagues=["NFL"],
        num_picks=20,
        risk="moderate",
        sportsbooks=books,
        player_props=None,
    )

    if status != 200:
        msg = data.get("message") or data.get("raw") or f"HTTP {status}"
        await ctx.send(f"⚠️ Oddible error: {msg}")
        return

    await send_trending_as_embeds(ctx, "NFL", data)


@bot.command(name="nbaprops")
async def nbaprops_cmd(ctx: commands.Context):
    """Get NBA player props from Oddible."""
    await ctx.send("Fetching **NBA player props** from Oddible...")

    status, headers, data = fetch_trending(
        leagues=["NBA"],
        num_picks=20,
        risk="moderate",
        sportsbooks=books,
        player_props=True,
    )

    if status != 200:
        msg = data.get("message") or data.get("raw") or f"HTTP {status}"
        await ctx.send(f"⚠️ Oddible error: {msg}")
        return

    await send_trending_as_embeds(ctx, "NBA Player Props", data)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
