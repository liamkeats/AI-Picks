# Canonical sportsbook slugs your bot supports (as Oddible expects them)
BOOKS_ALL = [
    "betopenly","betonlineag","betmgm","betrivers","betus","bovada","williamhill_us",
    "draftkings","fanduel","lowvig","mybookieag","ballybet","betanysports","betparx",
    "espnbet","fliff","hardrockbet","windcreek","prizepicks","underdog","onexbet",
    "sport888","betclic","betfair_ex_eu","betsson","betvictor","coolbet","everygame",
    "gtbets","livescorebet_eu","marathonbet","matchbook","nordicbet","pinnacle",
    "suprabets","tipico_de","unibet_eu","williamhill","betfair_ex_uk","betfair_sb_uk",
    "betway","boylesports","casumo","coral","grosvenor","ladbrokes_uk","leovegas",
    "livescorebet","paddypower","skybet","smarkets","unibet_uk","virginbet",
    "betfair_ex_au","betr_au","betright","ladbrokes_au","neds","playup","pointsbetau",
    "sportsbet","tab","tabtouch","topsport","unibet","fanatics","bet365_us","novig",
    "prophetx","wynnbet","superbook"
]

# Books we can deep link in embeds (so users can click straight into a pre-filled slip)
BOOKS_WITH_DEEPLINKS = {
    "betmgm","betrivers","draftkings","fanduel","ballybet","espnbet","hardrockbet",
    "prizepicks","underdog","fanatics","novig","prophetx"
}

# Optional regional groups (tweak as you like)
BOOKS_US = [
    "draftkings","fanduel","betmgm","caesars","espnbet","betrivers","hardrockbet",
    "betparx","fanatics","bet365_us","wynnbet","superbook","novig","prophetx"
]
# If you want Canada or EU presets later, add them here.

def normalize_book(name: str) -> str:
    """
    Lowercase + strip spaces/underscores to attempt a best-effort match.
    Returns the canonical slug if we recognize it, else ''.
    """
    if not name:
        return ""
    raw = name.lower().replace(" ", "").replace("-", "").replace("__", "_")
    # quick direct hits first
    if name.lower() in BOOKS_ALL:
        return name.lower()
    # relaxed matching (add any aliases you want here)
    aliases = {
        "dk": "draftkings",
        "fd": "fanduel",
        "mgm": "betmgm",
        "espn": "espnbet",
        "bet365": "bet365_us",
        "prize picks": "prizepicks",
    }
    return aliases.get(raw, name.lower() if name.lower() in BOOKS_ALL else "")

def validate_books(selected: list[str] | None, fallback: list[str] | None = None) -> list[str]:
    """
    Validate a user/dev-provided list against BOOKS_ALL.
    If empty/None or all invalid, fall back to the provided fallback or a sane default.
    """
    if not selected:
        selected = []
    cleaned = []
    for b in selected:
        nb = normalize_book(b)
        if nb and nb in BOOKS_ALL:
            cleaned.append(nb)
    if cleaned:
        return cleaned
    # default fallback: prioritize deeplink-able books commonly used
    return (fallback or ["draftkings","fanduel","betmgm"])

def prioritize_deeplink_books(books: list[str], max_n: int | None = None) -> list[str]:
    """
    Reorders a list so deeplink-capable books come first.
    Optionally cap the length with max_n.
    """
    deeplink_first = sorted(books, key=lambda b: (b not in BOOKS_WITH_DEEPLINKS, b))
    return deeplink_first[:max_n] if max_n else deeplink_first
