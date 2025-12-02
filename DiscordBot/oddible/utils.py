import json
from typing import Dict, Tuple, Optional, List
from collections import defaultdict
import discord

NBA_TEAMS = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHO": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}

# Simple helper so we can go "Utah Jazz" -> "UTA"
NBA_NAME_TO_ABBR = {name.lower(): abbr for abbr, name in NBA_TEAMS.items()}

# Books we prefer for "Bet now" CTAs (deeplinks)
# NOTE: keys are lower-case because parse_deeplinks() lowercases them.
DEEPLINK_PRIORITY = [
    # Your featured books first
    "chalkboard",
    "underdog",
    "betr",
    "sleeper",
    "dabble",
    "boom",
    "novig",
    "rebet",
    "onyx",

    # Then the rest of the “normal” books
    "draftkings",
    "fanduel",
    "betmgm",
    "espnbet",
    "betrivers",
    "fanatics",
    "hardrockbet",
    "ballybet",
    "prophetx",
    "prizepicks",
]

# ---------------- Display settings for groups ----------------

GROUP_ORDER = [
    "spread",
    "totals",
    "moneyline",
    "player_props",
    "other",
]

GROUP_LABELS = {
    "spread": "⭐ Spread Picks",
    "totals": "🔥 Totals Picks",
    "moneyline": "💰 Moneyline Picks",
    "player_props": "🎯 Player Props",
    "other": "📦 Other Picks",
}

GROUP_COLOURS = {
    "spread": discord.Colour.blue(),
    "totals": discord.Colour.green(),
    "moneyline": discord.Colour.gold(),
    "player_props": discord.Colour.purple(),
    "other": discord.Colour.dark_grey(),
}

# ---------- Deeplink helpers ----------


def parse_deeplinks(deep_links_str: str) -> Dict[str, str]:
    """
    Oddible returns deepLinks as a JSON string. Safely parse into dict {book: url}.
    """
    if not deep_links_str:
        return {}
    try:
        data = json.loads(deep_links_str)
        return {k.lower(): v for k, v in data.items() if isinstance(v, str) and v}
    except Exception:
        return {}

def pick_best_deeplink(deep_links: Dict[str, str], priority=None) -> Optional[Tuple[str, str]]:
    """
    Pick the best available deeplink by priority list. Returns (book, url) or None.
    """
    order = priority or DEEPLINK_PRIORITY
    for book in order:
        url = deep_links.get(book)
        if url:
            return book, url
    # fallback: first available
    for book, url in deep_links.items():
        if url:
            return book, url
    return None

def fill_placeholders(url: str, state: str = "ny", wager_amount: Optional[int] = None) -> str:
    """
    Replace placeholders like {state} and {wagerAmount} when present.
    """
    if not url:
        return url
    url = url.replace("{state}", state)
    if wager_amount is not None:
        url = url.replace("{wagerAmount}", str(wager_amount))
    return url

def format_deeplink_block(
    deep_links: Dict[str, str],
    state: str = "ny",
    max_books: int = 3,
) -> str:
    """
    Convert {book: url} into:
      'Bet: [Underdog](...) · [Sleeper](...) · [Draftkings](...)'
    showing up to max_books, in DEEPLINK_PRIORITY order.
    """
    if not deep_links:
        return ""

    # Respect DEEPLINK_PRIORITY order
    ordered_books: List[str] = []
    for b in DEEPLINK_PRIORITY:
        if b in deep_links:
            ordered_books.append(b)

    # Add any books not in DEEPLINK_PRIORITY at the end
    for b in deep_links.keys():
        if b not in ordered_books:
            ordered_books.append(b)

    selected = ordered_books[:max_books]
    if not selected:
        return ""

    parts: List[str] = []
    for book in selected:
        raw_url = deep_links.get(book)
        if not raw_url:
            continue
        url = fill_placeholders(raw_url, state)
        parts.append(f"[{book.title()}]({url})")  # masked link, no big preview

    if not parts:
        return ""

    return "Bet: " + " · ".join(parts)


# ---------- Hit-rate & dedupe helpers ----------

def hitrate_text(p: dict) -> str:
    wins = p.get("hit_rate_wins")
    total = p.get("hit_rate_total")
    pct = p.get("hit_rate_percentage")
    if not isinstance(total, (int, float)) or not total:
        return ""
    try:
        iwins, itotal = int(wins), int(total)
    except Exception:
        return ""
    # For tiny samples, call it out
    if itotal < 8:
        ipct = int(pct) if isinstance(pct, (int, float)) else None
        return (
            f"hit rate: {ipct}% ({iwins}/{itotal}) • small sample"
            if ipct is not None else
            f"hit rate: ({iwins}/{itotal}) • small sample"
        )
    # Cosmetic cap to avoid “too perfect” optics while keeping sample size visible
    ipct = int(pct) if isinstance(pct, (int, float)) else None
    shown_pct = min(ipct, 95) if ipct is not None else None
    return (
        f"hit rate: {shown_pct}% ({iwins}/{itotal})"
        if shown_pct is not None else
        f"hit rate: ({iwins}/{itotal})"
    )

def pick_key(p: dict) -> tuple:
    """
    Identify the “same bet idea” to dedupe *exact* duplicates.
    Make this fine-grained enough that different players / lines don't collide.
    """
    return (
        p.get("home_team"),
        p.get("away_team"),
        p.get("market"),
        p.get("outcome_name"),            # Over / Under / team name
        p.get("outcome_point"),           # the line (e.g. 12.5)
        (p.get("outcome_description") or "").strip(),  # player name for props
    )


def pick_score(p: dict) -> Tuple[float, float]:
    """
    Score a pick for ranking: higher hit rate first, then better odds.
    Returns (hit_rate_pct, odds).
    """
    pct = p.get("hit_rate_percentage")
    odds = p.get("bestOdds")

    try:
        pct_val = float(pct) if pct is not None else 0.0
    except Exception:
        pct_val = 0.0

    try:
        odds_val = float(odds) if odds is not None else 1.0
    except Exception:
        odds_val = 1.0

    return pct_val, odds_val


def dedupe_and_diversify(picks: List[dict], max_out: int = 3) -> List[dict]:
    """
    Prefer unique matchups/markets; drop near-duplicates.
    """
    seen = set()
    out: List[dict] = []
    for p in picks:
        k = pick_key(p)
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
        if len(out) >= max_out:
            break
    return out

def format_pick_line(p: dict) -> str:
    """
    Turn a pick dict into a clean one-liner for Discord text.

    Examples after this change:
      - Team total:
        "**UTA @ GSW** — **UTA Under 126.5 (Alternate Team Total)** • ..."
      - Game total:
        "**MIL @ CLE** — **Under 236.5 (Alternate Game Total)** • ..."
      - Player prop:
        "**IND @ DET** — **T.J. McConnell Under 14.5 (Player Points + Assists)** • ..."
      - Spread:
        "**NYK @ BOS** — **NYK +5.5 (Alternate Spread)** • ..."
    """
    # Header: keep abbreviations (UTA @ GSW, HOU @ PHO, etc.)
    away = p.get("away_team_abbreviation") or p.get("away_team") or "Away"
    home = p.get("home_team_abbreviation") or p.get("home_team") or "Home"

    market = (p.get("market") or "").strip()
    outcome_name = (p.get("outcome_name") or "").strip()   # "Over", "Under", or team name
    desc = (p.get("outcome_description") or "").strip()    # player name for props
    line = p.get("outcome_point")                          # numeric line, e.g. 14.5

    lower_market = market.lower()

    # ---------- try to detect which TEAM this pick is on ----------
    team_abbr: Optional[str] = None

    # 1) outcome_name might literally be the team name ("Utah Jazz" or "UTA")
    on_lower = outcome_name.lower()
    if on_lower in NBA_NAME_TO_ABBR:
        team_abbr = NBA_NAME_TO_ABBR[on_lower]
    elif outcome_name.upper() in NBA_TEAMS:
        team_abbr = outcome_name.upper()

    # 2) look inside the description / market for a team mention
    if not team_abbr:
        text_blobs = [desc, market]
        for text in text_blobs:
            if not text:
                continue
            tlow = text.lower()
            tup = text.upper()
            for abbr, fullname in NBA_TEAMS.items():
                if fullname.lower() in tlow or abbr in tup:
                    team_abbr = abbr
                    break
            if team_abbr:
                break

    # ---------- classify the pick type (only for formatting, not grouping) ----------
    is_player_market = "player" in lower_market
    is_team_total = "team total" in lower_market
    is_spread = any(term in lower_market for term in ["spread", "handicap", "ats"])

    # ---------- build the main description ----------
    if is_player_market and desc:
        # Player prop: "T.J. McConnell Under 14.5 (Player Points + Assists)"
        if line is not None and outcome_name:
            main = f"{desc} {outcome_name} {line} ({market})"
        elif outcome_name:
            main = f"{desc} {outcome_name} ({market})"
        else:
            main = f"{desc} ({market})"

    elif is_team_total and team_abbr:
        # Team total: "UTA Under 126.5 (Alternate Team Total)"
        if line is not None and outcome_name:
            main = f"{team_abbr} {outcome_name} {line} ({market})"
        elif outcome_name:
            main = f"{team_abbr} {outcome_name} ({market})"
        else:
            main = f"{team_abbr} ({market})"

    elif is_spread and team_abbr:
        # Spread: "NYK +5.5 (Alternate Spread)" or "NYK -2.5 (Spread)"
        if line is not None:
            main = f"{team_abbr} {line} ({market})"
        else:
            main = f"{team_abbr} ({market})"

    elif line is not None:
        # Generic totals / other line-based markets: keep your old behavior
        if outcome_name:
            main = f"{outcome_name} {line} ({market})"
        else:
            main = f"{market} {line}"
    else:
        # No line – just fall back to name / market
        main = outcome_name or market or "Pick"

    # ---------- right-hand side: odds + hit rate ----------
    odds = p.get("bestOdds")
    hr_txt = hitrate_text(p)

    header = f"**{away} @ {home}** — **{main}**"

    detail_bits = []
    if odds is not None:
        detail_bits.append(f"odds: **{odds}**")
    if hr_txt:
        detail_bits.append(hr_txt)

    if detail_bits:
        details = " • ".join(detail_bits)
        # two-line output: first line is the pick, second line is the details
        return f"{header}\n  • {details}"
    else:
        return header



# ---------- Market classification & grouping ----------

def classify_pick(p: dict) -> str:
    """
    Accurate classification:
    - player_props → stat-based markets
    - totals      → game/team totals
    - spread      → spreads/handicaps
    - moneyline   → ML
    - other       → everything else
    """
    market = (p.get("market") or "").lower()
    name = (p.get("outcome_name") or "").lower()

    # ----- PLAYER PROPS -----
    stat_terms = [
        "points","assists","rebounds","pra","steals","blocks",
        "threes","3pt","three pointers","made threes",
        "turnovers","yards","touchdowns","receptions",
        "completions","passing","rushing","receiving"
    ]
    if any(term in market for term in stat_terms):
        return "player_props"
    if any(term in name for term in stat_terms):
        return "player_props"

    # ----- SPREAD -----
    if "spread" in market or "handicap" in market or "ats" in market:
        return "spread"

    # ----- TOTALS (non-props) -----
    if "total" in market:
        return "totals"
    # plain “Over” / “Under” for game totals
    if name in ("over", "under"):
        return "totals"

    # ----- MONEYLINE -----
    if "moneyline" in market or market == "ml":
        return "moneyline"

    return "other"

def group_picks_by_type(picks: List[dict]) -> Dict[str, List[dict]]:
    """Return a dict of buckets: {spread: [...], totals: [...], ...}"""
    groups: Dict[str, List[dict]] = defaultdict(list)
    for p in picks:
        g = classify_pick(p)
        groups[g].append(p)
    return groups

def select_group_picks(
    group_name: str, bucket: List[dict], max_per_group: int
) -> List[dict]:
    """
    Choose up to max_per_group picks from this group with group-specific dedupe rules:

    - totals:      at most one pick per game (away/home).
    - player_props: at most one pick per player.
    - others:      fall back to generic dedupe_and_diversify.
    """
    # --- PLAYER PROPS: 1 per player ---
    if group_name == "player_props":
        by_player: Dict[str, dict] = {}
        for p in bucket:
            player = (p.get("outcome_description") or "").strip()
            # fall back to outcome_name if description is missing
            if not player:
                player = (p.get("outcome_name") or "").strip()
            key = player.lower()
            if not key:
                # If somehow no name, treat it as unique
                key = repr((
                    p.get("home_team"),
                    p.get("away_team"),
                    p.get("market"),
                    p.get("outcome_name") or p.get("outcome_point"),
                ))

            # Keep the best pick per player
            if key not in by_player or pick_score(p) > pick_score(by_player[key]):
                by_player[key] = p

        unique = list(by_player.values())
        unique.sort(key=pick_score, reverse=True)
        return unique[:max_per_group]

    # --- TOTALS: 1 per game (away/home) ---
    if group_name == "totals":
        by_game: Dict[Tuple[str, str], dict] = {}
        for p in bucket:
            away = (p.get("away_team_abbreviation") or p.get("away_team") or "").strip()
            home = (p.get("home_team_abbreviation") or p.get("home_team") or "").strip()
            key = (away, home)

            # Keep the best pick per game
            if key not in by_game or pick_score(p) > pick_score(by_game[key]):
                by_game[key] = p

        unique = list(by_game.values())
        unique.sort(key=pick_score, reverse=True)
        return unique[:max_per_group]

    # --- Everything else: generic behavior (your existing dedupe logic) ---
    return dedupe_and_diversify(bucket, max_out=max_per_group)


def build_discord_message_grouped(
    raw_json: dict,
    title: str = "🏀 NBA – Top Insights (Powered by Oddible)",
    max_per_group: int = 3,
    state: str = "ny"
) -> str:
    """
    Build a clean Discord-ready message grouped by:
    spread, totals, moneyline, player props, other.
    """
    data = raw_json.get("data") or {}
    picks = data.get("picks") or []

    if not picks:
        return f"**{title}**\nNo picks available."

    # STEP 1: dedupe across ALL picks once
    deduped = dedupe_and_diversify(picks, max_out=len(picks))  # effectively "unique list"

    # STEP 2: then group them
    groups = group_picks_by_type(deduped)

    msg = f"**{title}**\n"

    ordered_sections = [
        ("spread", "⭐ Spread Picks"),
        ("totals", "🔥 Totals Picks"),
        ("moneyline", "💰 Moneyline Picks"),
        ("player_props", "🎯 Player Props"),
        ("other", "📦 Other Picks"),
    ]

    for gkey, header in ordered_sections:
        bucket = groups.get(gkey, [])
        if not bucket:
            continue

        # NEW: group-aware dedupe/selection
        bucket = select_group_picks(gkey, bucket, max_per_group)
        if not bucket:
            continue

        msg += f"\n__**{header}**__\n"

        for p in bucket:
            line = format_pick_line(p)

            # DeepLink handling – show multiple books in priority order
            dl = parse_deeplinks(p.get("deepLinks", ""))
            deeplink_block = format_deeplink_block(dl, state=state, max_books=3)

            if deeplink_block:
                line += f" • {deeplink_block}"

            msg += f"• {line}\n"


    return msg
