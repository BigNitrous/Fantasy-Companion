"""League settings. Everything comes from environment variables so no
credentials ever live in the repo."""

import os

LEAGUE_ID = os.environ.get("LEAGUE_ID", "")
TEAM_NAME = os.environ.get("TEAM_NAME", "")          # your team, exact ESPN name
SEASON = int(os.environ.get("SEASON", "2026"))
SCORING = os.environ.get("SCORING", "ppr")           # ppr | half | standard

# Only needed for private leagues. Grab from browser cookies on fantasy.espn.com.
ESPN_S2 = os.environ.get("ESPN_S2") or None
ESPN_SWID = os.environ.get("ESPN_SWID") or None

# How many free agents to pull and rank for the waiver section.
FREE_AGENT_POOL = int(os.environ.get("FREE_AGENT_POOL", "60"))

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "site")


def is_configured() -> bool:
    return bool(LEAGUE_ID)
