from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException, ReadTimeout, ConnectionError as ReqConnectionError

from .books import validate_books, prioritize_deeplink_books
from .utils import (
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

# ---------------- Env & API setup (same idea as test bot) ----------------
# This file: DiscordBot/oddible/oddible_cog.py
# Root DiscordBot folder is one level up.
BASE_DIR = Path(__file__).resolve().parents[1]  # -> DiscordBot
load_dotenv(BASE_DIR / "token.env")  # make sure ODDIBLE_API_KEY is loaded

ODDIBLE_API_KEY = os.getenv("ODDIBLE_API_KEY")
if not ODDIBLE_API_KEY:
    # Same behaviour as your test bot: fail loudly so you notice config issue.
    raise RuntimeError("ODDIBLE_API_KEY is not set in DiscordBot/token.env")

ODDIBLE_URL = "https://api.dev.smartbettor.ai/api/oddible/trending"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": ODDIBLE_API_KEY,
}

# Validate & prioritise books once (same list you used in the test bot)
requested_books = ["draftkings", "fanduel", "betmgm", "prizepicks", "underdog", "novig"]
books = validate_books(requested_books)
books = prioritize_deeplink_books(books, max_n=6)


# ---------------- Core HTTP + helpers (ported from test bot) ----------------

def fetch_trending(
    leagues: List[str],
    num_picks: int = 20,
    risk: str = "moderate",
    sportsbooks: List[str] | None = None,
    player_props: bool | None = None,
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    """
    Call Oddible's /trending endpoint and return (status_code, headers, json_data).
    Mirrors the logic from Testing/Oddible/bot.py.
    """
    payload: Dict[str, Any] = {
        "leagues": leagues,
        "num_picks": num_picks,
        "sportsbooks": sportsbooks or ["draftkings"],
        "risk": risk,
    }
    if player_props is not None:
        payload["player_props"] = bool(player_props)

    try:
        resp = requests.post(ODDIBLE_URL, json=payload, headers=HEADERS, timeout=20)
        try:
            data = resp.json()
        except Exception:
            data = {"status": "error", "raw": resp.text}
        return resp.status_code, dict(resp.headers), data

    except ReadTimeout:
        return 0, {}, {
            "status": "timeout",
            "message": "Request to Oddible timed out. The API may be slow or unavailable.",
        }
    except (ReqConnectionError, RequestException) as e:
        return 0, {}, {
            "status": "error",
            "message": f"Network error talking to Oddible: {e}",
        }


def build_oddible_promo_embed() -> discord.Embed:
    """
    Bottom promo embed: 'Oddible 7 Days FREE'
    (Same content/colour as your JSON and test bot.)
    """
    embed = discord.Embed(
        title="Oddible 7 Days FREE ",
        description="👆\nClaim your free week & make SMARTER picks!",
        url="https://oddible.onelink.me/zB8n/aipicks",
        colour=discord.Colour(16753152),  # 0xFFA200
    )

    embed.set_footer(
        text=(
            "The Oddible app is an all in one platform to research picks, "
            "track your profits, share with friends, and more! It provides "
            "comprehensive analysis of each pick, grading it from Bad to Great. "
            "It also provides a leaderboard based on users real time results to "
            "see and follow the best bettors."
        )
    )

    return embed


async def send_long_message(ctx: commands.Context, content: str):
    """Split long messages into 2000-char chunks, then send promo embed."""
    if content and len(content) <= 2000:
        await ctx.send(content)
    else:
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

    # Always send the promo embed at the very bottom
    promo_embed = build_oddible_promo_embed()
    await ctx.send(embed=promo_embed)


def build_pick_embed(p: dict, group_name: str, state: str = "ny") -> discord.Embed:
    """
    Turn a single Oddible pick into a card-style embed.
    Uses utils.format_pick_line() + multi-book deeplinks.
    """
    line = format_pick_line(p)
    parts = line.split("\n", 1)
    header = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    # Strip markdown ** from the title
    title = header.replace("**", "").strip()

    # Details (odds + hit rate)
    desc_lines: List[str] = []
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
) -> Dict[str, List[discord.Embed]]:
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

    grouped_embeds: Dict[str, List[discord.Embed]] = {}

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
    """
    Send the grouped embeds exactly like your test bot:
    - One text line: "Top insights..."
    - For each group: header embed + pick embeds in one message
    - Then the Oddible promo embed.
    """
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

        await ctx.send(embeds=[header_embed] + embeds_for_group)

    # After sending all groups, send the bottom promo card
    promo_embed = build_oddible_promo_embed()
    await ctx.send(embed=promo_embed)


# ---------------- Cog wrapper around that logic ----------------

class OddibleCog(commands.Cog):
    """
    Cog providing !nba, !nfl, !nbaprops using Oddible,
    with the SAME behaviour as Testing/Oddible/bot.py.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # reuse validated/prioritised books
        self.books = books

    async def _run_oddible_command(
        self,
        ctx: commands.Context,
        league_label: str,
        leagues: List[str],
        player_props: bool | None = None,
    ):
        # Delete the user's command message (!nba / !nfl / !nbaprops)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        await ctx.send(f"Fetching **{league_label}** picks from Oddible...")

        status, headers, data = fetch_trending(
            leagues=leagues,
            num_picks=20,
            risk="moderate",
            sportsbooks=self.books,
            player_props=player_props,
        )

        if status != 200:
            msg = data.get("message") or data.get("raw") or f"HTTP {status}"
            await ctx.send(f"⚠️ Oddible error: {msg}")
            return

        await send_trending_as_embeds(ctx, league_label, data)

    # ---- Commands ----

    @commands.command(name="nba")
    async def nba_cmd(self, ctx: commands.Context):
        """Get NBA main-market picks from Oddible."""
        await self._run_oddible_command(
            ctx,
            league_label="NBA",
            leagues=["NBA"],
            player_props=None,
        )

    @commands.command(name="nfl")
    async def nfl_cmd(self, ctx: commands.Context):
        """Get NFL main-market picks from Oddible."""
        await self._run_oddible_command(
            ctx,
            league_label="NFL",
            leagues=["NFL"],
            player_props=None,
        )

    @commands.command(name="nbaprops")
    async def nbaprops_cmd(self, ctx: commands.Context):
        """Get NBA player props from Oddible."""
        await self._run_oddible_command(
            ctx,
            league_label="NBA Player Props",
            leagues=["NBA"],
            player_props=True,
        )
