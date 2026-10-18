"""One-off: save Sleeper's and NFL.com's weekly projections, plus the league's scoring rules.

Writes backtest/data/sleeper_proj.csv, nfl_proj.csv, league_scoring.json and
probe.txt (which endpoints answered). Prints counts only, never credentials.
"""

import csv
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collector import config  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
WEEKS = range(1, int(os.environ.get("THROUGH_WEEK", "6")) + 1)
UA = {"User-Agent": "Mozilla/5.0 (fantasy-companion backtest)"}
probe = []


def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=60, **kw)
        probe.append(f"{r.status_code} {len(r.content):>8} {url.split('?')[0]}")
        return r
    except Exception as e:
        probe.append(f"ERR {type(e).__name__} {url.split('?')[0]}")
        return None


def sleeper():
    rows = []
    pos = [("position[]", p) for p in ("QB", "RB", "WR", "TE", "K", "DEF")]
    for w in WEEKS:
        data = None
        for host in ("https://api.sleeper.com", "https://api.sleeper.app"):
            r = get(f"{host}/projections/nfl/2026/{w}", params=[("season_type", "regular")] + pos)
            if r is not None and r.status_code == 200:
                data = r.json()
                break
        for d in data or []:
            st, pl = d.get("stats") or {}, d.get("player") or {}
            rows.append({"week": w, "sleeper_id": d.get("player_id"), "company": d.get("company", ""),
                         "name": f"{pl.get('first_name', '')} {pl.get('last_name', '')}".strip(),
                         "position": pl.get("position", ""), "team": d.get("team") or pl.get("team", ""),
                         "pts_ppr": st.get("pts_ppr", ""), "pts_half_ppr": st.get("pts_half_ppr", ""),
                         "pts_std": st.get("pts_std", ""), "stats": json.dumps(st, separators=(",", ":"))})
        print(f"sleeper week {w}: {sum(1 for x in rows if x['week'] == w)} players")
    return rows


def nfl():
    rows = []
    for w in WEEKS:
        r = get("https://api.fantasy.nfl.com/v1/players/stats",
                params={"statType": "weekProjectedStats", "season": 2026, "week": w, "format": "json"})
        if r is None or r.status_code != 200:
            continue
        try:
            players = r.json().get("players") or []
        except ValueError:
            players = []
        for p in players:
            rows.append({"week": w, "nfl_id": p.get("id"), "gsis_id": p.get("gsisPlayerId", ""),
                         "esb_id": p.get("esbid", ""), "name": p.get("name", ""), "position": p.get("position", ""),
                         "team": p.get("teamAbbr", ""), "proj_pts": p.get("weekProjectedPts", ""),
                         "stats": json.dumps(p.get("stats") or {}, separators=(",", ":"))})
        print(f"nfl week {w}: {sum(1 for x in rows if x['week'] == w)} players")
    if not rows:   # API gone? Note whether the public projections page answers, for the write-up.
        get("https://fantasy.nfl.com/research/projections",
            params={"position": "O", "statCategory": "projectedStats", "statSeason": 2026,
                    "statType": "weekProjectedStats", "statWeek": 6})
    return rows


def scoring():
    try:
        from espn_api.football import League
        lg = League(league_id=int(config.LEAGUE_ID), year=config.SEASON, espn_s2=config.ESPN_S2, swid=config.ESPN_SWID)
        return {"scoring_format": getattr(lg.settings, "scoring_format", None)}
    except Exception as e:
        return {"error": type(e).__name__}


def save(name, rows):
    if rows:
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("sleeper_proj.csv", sleeper())
    save("nfl_proj.csv", nfl())
    with open(os.path.join(OUT, "league_scoring.json"), "w") as f:
        json.dump(scoring(), f, indent=1, default=str)
    with open(os.path.join(OUT, "probe.txt"), "w") as f:
        f.write("\n".join(probe) + "\n")
    print("\n".join(probe[:4] + probe[-3:]))
