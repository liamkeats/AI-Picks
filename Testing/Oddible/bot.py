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
from DiscordBot.oddible.utils import build_discord_message_grouped


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

    # Handle network / API errors
    if status != 200:
        msg = data.get("message") or data.get("raw") or f"HTTP {status}"
        await ctx.send(f"⚠️ Oddible error: {msg}")
        return

    msg = build_discord_message_grouped(data, "🏀 NBA – Top Insights")
    await send_long_message(ctx, msg)



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

    msg = build_discord_message_grouped(data, "🏈 NFL – Top Insights")
    await send_long_message(ctx, msg)

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

    msg = build_discord_message_grouped(data, "🏀 NBA – Player Props Insights")
    await send_long_message(ctx, msg)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
