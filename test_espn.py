#!/usr/bin/env python3
"""Smoke test for the ESPN connection.

Loads .env if present (same keys as .env.example; exported variables win),
connects to the league, lists every team so you can confirm TEAM_NAME, then
prints your roster through the same espn_source.fetch() path main.py uses.

    python3 test_espn.py

Exit 0 on success, 1 on any failure.
"""

import os
import sys
import traceback
import warnings

# Apple's python3 is built against LibreSSL; urllib3 warns about it on every
# import. Harmless here, so keep the output readable.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader so local runs don't need `export`. No dependency."""
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


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # keep tracebacks in order with prints
    load_dotenv()
    from collector import config  # reads env at import, so .env must load first

    if not config.is_configured():
        print("FAIL: LEAGUE_ID is not set.")
        print("      Copy .env.example to .env and fill it in, or export LEAGUE_ID.")
        return 1

    has_cookies = bool(config.ESPN_S2 and config.ESPN_SWID)
    print(f"League ID : {config.LEAGUE_ID}")
    print(f"Season    : {config.SEASON}")
    print(f"Team name : {config.TEAM_NAME or '(not set: will use first team)'}")
    print(f"Cookies   : {'set' if has_cookies else 'not set (public league only)'}")
    print()

    try:
        from espn_api.football import League
        league = League(
            league_id=int(config.LEAGUE_ID),
            year=config.SEASON,
            espn_s2=config.ESPN_S2,
            swid=config.ESPN_SWID,
        )
    except Exception as e:
        msg = str(e)
        if "espn_s2 and swid are required" in msg and not has_cookies:
            print(f"FAIL: league {config.LEAGUE_ID} is private. ESPN needs your espn_s2 and SWID cookies.")
            print("      Copy them from fantasy.espn.com (README step 3) into ESPN_S2 and ESPN_SWID in .env.")
            return 1
        if "does not exist" in msg:
            print(f"FAIL: ESPN says league {config.LEAGUE_ID} does not exist for {config.SEASON}. Check LEAGUE_ID/SEASON.")
            return 1
        print(f"FAIL: could not connect to ESPN: {e}")
        traceback.print_exc(limit=2)
        return 1

    week = int(getattr(league, "current_week", 1) or 1)
    print(f"Connected: {league.settings.name} (week {week}, {len(league.teams)} teams)")
    for t in league.teams:
        marker = " <- you" if config.TEAM_NAME and config.TEAM_NAME.lower() in t.team_name.lower() else ""
        print(f"  {t.team_name} ({t.wins}-{t.losses}){marker}")
    print()

    try:
        from collector import espn_source
        data = espn_source.fetch(week)
    except Exception as e:
        print(f"FAIL: connected, but fetching the roster failed: {e}")
        traceback.print_exc(limit=2)
        return 1

    print(f"Roster: {data['team_name']} ({data['record']})")
    if data["opponent_name"]:
        print(f"Week {week} opponent: {data['opponent_name']}")
    print()
    print(f"  {'Slot':<9}{'Pos':<5}{'Player':<26}{'Team':<5}{'Proj':>6}  {'Status'}")
    print(f"  {'-' * 9}{'-' * 5}{'-' * 26}{'-' * 5}{'-' * 6}  {'-' * 8}")
    starters = [p for p in data["roster"] if p["starting"]]
    bench = [p for p in data["roster"] if not p["starting"]]
    for p in starters + bench:
        proj = f"{p['projected']:.1f}" if p["projected"] is not None else "-"
        status = "" if p["injury"] in ("ACTIVE", "NORMAL", "") else p["injury"]  # same rule as brief.py
        print(f"  {p['slot']:<9}{p['position']:<5}{p['name']:<26}{p['team']:<5}{proj:>6}  {status}")
    print()
    print(f"OK: {len(data['roster'])} players ({len(starters)} starting, {len(bench)} bench), "
          f"{len(data['free_agents'])} free agents pulled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
