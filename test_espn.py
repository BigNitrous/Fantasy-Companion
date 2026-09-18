#!/usr/bin/env python3
"""Test the ESPN connection locally in a few seconds.

    python test_espn.py

Reads LEAGUE_ID / TEAM_NAME / ESPN_S2 / ESPN_SWID from a .env file in this
folder (copy .env.example to .env and fill it in), or from your shell
environment if they're already exported. Prints exactly what the dashboard
would say, so you can fix cookies without waiting on GitHub Actions.
"""

import sys
import warnings

# Apple's python3 is built against LibreSSL; urllib3 warns about it on every
# import. Harmless here, so keep the output readable.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # keep tracebacks in order with prints
    from collector import config, espn_source, sleeper_source  # config loads .env

    print(f"LEAGUE_ID : {config.LEAGUE_ID or '(empty)'}")
    print(f"TEAM_NAME : {config.TEAM_NAME or '(empty)'}")
    print(f"ESPN_S2   : {len(config.ESPN_S2 or '')} chars"
          + ("  (was pasted twice; using the first copy. Fix the value in .env / GitHub secrets)" if config.ESPN_S2_DOUBLED else ""))
    print(f"ESPN_SWID : {config.ESPN_SWID or '(empty)'}")
    print()

    problems = espn_source.validate_credentials()
    if problems:
        print("Problems found before contacting ESPN:")
        for p in problems:
            print(f"  - {p}")
        return 1

    week = sleeper_source.current_week()
    print(f"Contacting ESPN for week {week}...")
    try:
        data = espn_source.fetch(week)
    except espn_source.ESPNSetupError as e:
        print(f"NOT CONNECTED: {e}")
        return 1
    except Exception as e:
        print(f"BUG (not a config problem): {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return 2

    print(f"CONNECTED. League: {data['league_name']}")
    print(f"Team: {data['team_name']} ({data['record']}), {len(data['roster'])} players")
    if data.get("team_note"):
        print(f"NOTE: {data['team_note']}")
    print(f"Opponent this week: {data['opponent_name'] or '(none found)'}")
    print(f"Free agents pulled: {len(data['free_agents'])}")
    print()
    for p in data["roster"]:
        flag = "" if p["injury"] in ("ACTIVE", "NORMAL") else f"  [{p['injury']}]"
        proj = f"{p['projected']:.1f}" if isinstance(p["projected"], (int, float)) else "n/a"
        print(f"  {p['slot']:<6} {p['name']:<24} {p['position']:<4} {p['team']:<4} proj {proj}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
