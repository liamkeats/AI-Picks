import os, json, requests, datetime
from pathlib import Path
from dotenv import load_dotenv

# local imports (same folder)
from books import validate_books, prioritize_deeplink_books
from utils import pick_key, build_discord_message_grouped

load_dotenv("DiscordBot/token.env")

requested_books = ["draftkings","fanduel","betmgm","prizepicks","underdog","novig"]
books = validate_books(requested_books)
books = prioritize_deeplink_books(books, max_n=6)

ODDIBLE_URL = "https://api.dev.smartbettor.ai/api/oddible/trending"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": os.getenv("ODDIBLE_API_KEY")
}

def fetch_trending(leagues, num_picks=20, risk="moderate", sportsbooks=None, player_props=None):
    payload = {
        "leagues": leagues,
        "num_picks": num_picks,
        "sportsbooks": sportsbooks or ["draftkings"],
        "risk": risk
    }
    if player_props is not None:
        payload["player_props"] = bool(player_props)
    resp = requests.post(ODDIBLE_URL, json=payload, headers=HEADERS, timeout=20)
    try:
        data = resp.json()
    except Exception:
        data = {"status": "error", "raw": resp.text}
    return resp.status_code, resp.headers, data

def debug_dump(label: str, data: dict, save_json: bool = True):
    d = data.get("data") or {}
    picks = d.get("picks") or []
    print(f"\n=== DEBUG: {label} ===")
    print(f"Total picks returned: {len(picks)}")
    if not picks:
        print("No picks in response.")
        return

    uniq = set()
    for i, p in enumerate(picks, 1):
        away = p.get("away_team_abbreviation") or p.get("away_team")
        home = p.get("home_team_abbreviation") or p.get("home_team")
        market = p.get("market") or ""

        outcome_name = (p.get("outcome_name") or "").strip()
        player = (p.get("outcome_description") or "").strip()
        line = p.get("outcome_point")
        lower_market = market.lower()

        # Build a readable "name" for debug output
        if "player" in lower_market and player:
            # "T.J. McConnell Under 14.5"
            if line is not None:
                name = f"{player} {outcome_name} {line}"
            else:
                name = f"{player} {outcome_name}"
        elif line is not None:
            if outcome_name:
                name = f"{outcome_name} {line}"
            else:
                name = str(line)
        else:
            name = outcome_name or market or "Pick"

        odds = p.get("bestOdds")
        wins = p.get("hit_rate_wins")
        total = p.get("hit_rate_total")
        pct = p.get("hit_rate_percentage")

        k = pick_key(p)
        uniq.add(k)

        print(
            f"{i:02d}. {away}@{home} | {market} | {name} | "
            f"odds={odds} | hit={wins}/{total} ({pct}%)"
        )

    print(f"Unique picks by (home,away,market,outcome): {len(uniq)}")

    if save_json:
        Path("data").mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path("data") / f"oddible_{label.lower().replace(' ','_')}_{ts}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved full JSON → {out_path}")

if __name__ == "__main__":
    print("Using sportsbooks:", books)

    # NBA (main markets)
    nba_status, nba_headers, nba_data = fetch_trending(
        leagues=["NBA"], num_picks=20, risk="moderate", sportsbooks=books
    )
    print("\n=== NBA ===")
    print("Status:", nba_status, "| Remaining:", nba_headers.get("X-RateLimit-Remaining"))
    debug_dump("NBA", nba_data)
    print("\n----- DISCORD GROUPED MESSAGE (NBA) -----\n")
    print(build_discord_message_grouped(nba_data, "🏀 NBA – Top Insights"))

    # NFL
    nfl_status, nfl_headers, nfl_data = fetch_trending(
        leagues=["NFL"], num_picks=20, risk="moderate", sportsbooks=books
    )
    print("\n=== NFL ===")
    print("Status:", nfl_status, "| Remaining:", nfl_headers.get("X-RateLimit-Remaining"))
    debug_dump("NFL", nfl_data)
    print("\n----- DISCORD GROUPED MESSAGE (NFL) -----\n")
    print(build_discord_message_grouped(nfl_data, "🏈 NFL – Top Insights"))

    # (Optional) NBA player props to see if variety increases
    props_status, props_headers, props_data = fetch_trending(
        leagues=["NBA"], num_picks=20, risk="moderate", sportsbooks=books, player_props=True
    )
    print("\n=== NBA (player_props=True) ===")
    print("Status:", props_status, "| Remaining:", props_headers.get("X-RateLimit-Remaining"))
    debug_dump("NBA_Props", props_data)
    print("\n----- DISCORD GROUPED MESSAGE (NBA PROPS) -----\n")
    print(build_discord_message_grouped(props_data, "🏀 NBA – Player Props Insights"))
