"""League settings. Everything comes from environment variables so no
credentials ever live in the repo."""

import os


def _load_dotenv(path: str = ".env") -> None:
    """Loads KEY=VALUE lines from a .env in the working directory so local runs
    don't need `export`. Real environment variables always win, and Actions
    never has a .env, so the secrets there are unaffected."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv()

LEAGUE_ID = os.environ.get("LEAGUE_ID", "").strip()
TEAM_NAME = os.environ.get("TEAM_NAME", "").strip()  # your team, exact ESPN name
SEASON = int(os.environ.get("SEASON", "2026"))
SCORING = os.environ.get("SCORING", "ppr")           # ppr | half | standard

# Only needed for private leagues. Grab from browser cookies on fantasy.espn.com.
# .strip() matters: pasting a cookie into a GitHub secret often carries a
# trailing newline, and a newline inside an HTTP header raises ValueError.
ESPN_S2 = (os.environ.get("ESPN_S2") or "").strip() or None
ESPN_SWID = (os.environ.get("ESPN_SWID") or "").strip() or None

# A cookie pasted twice back to back is an easy slip when copying from
# DevTools. Use the single copy and let main.py / test_espn.py mention it.
ESPN_S2_DOUBLED = False
if ESPN_S2 and len(ESPN_S2) >= 200 and len(ESPN_S2) % 2 == 0:
    _half = len(ESPN_S2) // 2
    if ESPN_S2[:_half] == ESPN_S2[_half:]:
        ESPN_S2, ESPN_S2_DOUBLED = ESPN_S2[:_half], True

# How many free agents to pull and rank for the waiver section.
FREE_AGENT_POOL = int(os.environ.get("FREE_AGENT_POOL", "60"))

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "site")


def is_configured() -> bool:
    return bool(LEAGUE_ID)
