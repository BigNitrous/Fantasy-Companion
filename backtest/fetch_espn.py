"""One-off: save ESPN's projected and actual points for every finished week.

Runs in GitHub Actions (the only place with the league cookies). Writes
backtest/data/espn_players.csv (every rostered player in every lineup, each
week, with ESPN's projection and the points he scored) and
backtest/data/espn_matchups.csv. Prints counts only, never credentials.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collector import config  # noqa: E402

from espn_api.football import League  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def g(o, name, default=""):
    v = getattr(o, name, default)
    return default if v is None else v


def main() -> int:
    league = League(league_id=int(config.LEAGUE_ID), year=config.SEASON,
                    espn_s2=config.ESPN_S2, swid=config.ESPN_SWID)
    last = int(os.environ.get("THROUGH_WEEK") or (league.current_week - 1))
    os.makedirs(OUT, exist_ok=True)
    players, games = [], []
    mine = (config.TEAM_NAME or "").lower()
    for week in range(1, last + 1):
        try:
            boxes = league.box_scores(week)
        except Exception as e:
            print(f"week {week}: box scores failed ({type(e).__name__})")
            continue
        n = 0
        for b in boxes:
            home, away = g(b, "home_team", None), g(b, "away_team", None)
            if not home or not away or isinstance(home, int) or isinstance(away, int):
                continue
            games.append({"week": week, "home": home.team_name, "away": away.team_name,
                          "home_score": g(b, "home_score", ""), "away_score": g(b, "away_score", ""),
                          "home_projected": g(b, "home_projected", ""), "away_projected": g(b, "away_projected", "")})
            for side, team, opp in (("home", home, away), ("away", away, home)):
                for p in g(b, f"{side}_lineup", []) or []:
                    players.append({
                        "week": week, "fantasy_team": team.team_name, "fantasy_opp": opp.team_name,
                        "is_mine": int(bool(mine) and mine in team.team_name.lower()),
                        "slot": g(p, "slot_position"), "name": g(p, "name"), "espn_id": g(p, "playerId"),
                        "position": g(p, "position"), "pro_team": g(p, "proTeam"),
                        "pro_opponent": g(p, "pro_opponent"),
                        "projected": g(p, "projected_points", ""), "actual": g(p, "points", ""),
                        "game_played": g(p, "game_played", ""), "bye": int(bool(g(p, "on_bye_week", False))),
                        "injury_status": g(p, "injuryStatus"), "active_status": g(p, "active_status"),
                    })
                    n += 1
        print(f"week {week}: {len(boxes)} matchups, {n} player rows")

    for name, rows in (("espn_players.csv", players), ("espn_matchups.csv", games)):
        if not rows:
            continue
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"wrote {len(players)} player rows and {len(games)} matchups through week {last}")
    return 0 if players else 1


if __name__ == "__main__":
    sys.exit(main())
