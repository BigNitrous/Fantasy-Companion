"""What each offense actually does: who gets the ball, and who is throwing it.

Pulls three nflverse CSVs with plain requests (so it runs on any Python, no
nflreadpy needed): weekly player stats, snap counts and weekly team stats.
For every skill player it works out, over the last few games he played:
snap share, target share, carry share, targets and carries per game, plus
last week's line. For every team: pass and run volume and the quarterback.

Everything degrades to an empty result if nflverse is unreachable.
"""

from __future__ import annotations
import csv
import io
import re
from collections import Counter

import requests

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
TIMEOUT = 90
WINDOW = 4                      # most recent games a player appeared in
SKILL = ("QB", "RB", "WR", "TE", "FB")
# Every source spells a few teams differently; ESPN's spelling is the target.
TEAM_FIX = {"LA": "LAR", "WAS": "WSH", "JAC": "JAX", "ARZ": "ARI", "BLT": "BAL",
            "CLV": "CLE", "HST": "HOU", "SD": "LAC", "OAK": "LV", "STL": "LAR"}
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv)\b\.?", re.I)


def norm(name) -> str:
    """Loose name key: 'Travis Etienne Jr.' and 'Travis Etienne' compare equal."""
    return re.sub(r"[^a-z]", "", _SUFFIX.sub("", (name or "").lower()))


def team(t) -> str:
    t = (t or "").upper()
    return TEAM_FIX.get(t, t)


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _rows(kind: str, name: str) -> list:
    try:
        r = requests.get(f"{BASE}/{kind}/{name}.csv", timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        return list(csv.DictReader(io.StringIO(r.content.decode("utf-8"))))
    except Exception:
        return []


def _played(d: dict) -> bool:
    return d.get("snaps", 0) > 0 or (d.get("carries", 0) + d.get("targets", 0) + d.get("attempts", 0)) > 0


def load(season: int) -> dict:
    """Returns {"season", "stale", "through", "players": {key: [rec]}, "teams": {abbr: {...}}}
    or {} when the data isn't available."""
    stale = False
    stats = _rows("stats_player", f"stats_player_week_{season}")
    if not stats:                                  # before week 1 there is nothing yet
        season, stale = season - 1, True
        stats = _rows("stats_player", f"stats_player_week_{season}")
    team_rows = _rows("stats_team", f"stats_team_week_{season}")
    snaps = _rows("snap_counts", f"snap_counts_{season}")
    if not stats or not team_rows:
        return {}

    tw: dict = {}                                  # team -> week -> {att, car}
    for r in team_rows:
        if r.get("season_type", "REG") != "REG":
            continue
        tw.setdefault(team(r["team"]), {})[int(r["week"])] = {"att": _f(r["attempts"]), "car": _f(r["carries"])}

    pw: dict = {}                                  # (key, team) -> {name, position, weeks}

    def entry(name, pos, t):
        return pw.setdefault((norm(name), t), {"name": name, "position": pos, "team": t, "weeks": {}})

    for r in stats:
        if r.get("season_type", "REG") != "REG" or r.get("position") not in SKILL:
            continue
        e = entry(r["player_display_name"], r["position"], team(r["team"]))
        e["weeks"].setdefault(int(r["week"]), {}).update(
            carries=_f(r["carries"]), targets=_f(r["targets"]), tshare=_f(r["target_share"]),
            attempts=_f(r["attempts"]), receptions=_f(r["receptions"]),
            rec_yds=_f(r["receiving_yards"]), rush_yds=_f(r["rushing_yards"]),
            pts=_f(r["fantasy_points_ppr"]))
    for r in snaps:
        if r.get("game_type", "REG") != "REG" or r.get("position") not in SKILL:
            continue
        n = _f(r["offense_snaps"])
        if n <= 0:
            continue
        e = entry(r["player"], r["position"], team(r["team"]))
        e["weeks"].setdefault(int(r["week"]), {}).update(snaps=n, snap_pct=_f(r["offense_pct"]))

    # Who threw the ball each week, per team.
    qb_week: dict = {}
    for (_, t), e in pw.items():
        if e["position"] != "QB":
            continue
        for w, d in e["weeks"].items():
            if d.get("attempts", 0) > 0 and d["attempts"] >= qb_week.get(t, {}).get(w, ("", 0))[1]:
                qb_week.setdefault(t, {})[w] = (e["name"], d["attempts"])

    teams: dict = {}
    for t, weeks in tw.items():
        tl = sorted(weeks)[-WINDOW:]
        att, car = _mean(weeks[w]["att"] for w in tl), _mean(weeks[w]["car"] for w in tl)
        order = sorted(qb_week.get(t, {}))
        now = qb_week[t][order[-1]][0] if order else ""
        earlier = Counter(qb_week[t][w][0] for w in order[:-1])
        prev = earlier.most_common(1)[0][0] if earlier else ""
        teams[t] = {"att_pg": att, "car_pg": car, "pass_rate": att / (att + car) if att + car else 0.0,
                    "weeks": sorted(weeks), "qb": now, "qb_prev": prev}

    players: dict = {}
    for (k, t), e in pw.items():
        tweeks = teams.get(t, {}).get("weeks")
        if not tweeks:
            continue
        wk = sorted(w for w, d in e["weeks"].items() if _played(d))
        if not wk:
            continue
        last, wset = wk[-WINDOW:], set(wk)
        tl = tweeks[-WINDOW:]

        def car_share(w):
            tc = tw[t].get(w, {}).get("car", 0)
            return e["weeks"][w].get("carries", 0) / tc if tc else 0.0

        snap_w = [w for w in last if "snap_pct" in e["weeks"][w]]
        played_snap = [w for w in wk if "snap_pct" in e["weeks"][w]]
        trend = None
        if len(played_snap) >= 3:
            recent, base = played_snap[-2:], played_snap[:-2]
            trend = round((_mean(e["weeks"][w]["snap_pct"] for w in recent)
                           - _mean(e["weeks"][w]["snap_pct"] for w in base)) * 100)
        lw = e["weeks"].get(wk[-1], {})
        rec = {
            "name": e["name"], "position": e["position"], "team": t, "games": len(wk),
            "snap_pct": _mean(e["weeks"][w]["snap_pct"] for w in snap_w) if snap_w else None,
            "target_share": _mean(e["weeks"][w].get("tshare", 0.0) for w in last),
            "carry_share": _mean(car_share(w) for w in last),
            "targets_pg": _mean(e["weeks"][w].get("targets", 0.0) for w in last),
            "carries_pg": _mean(e["weeks"][w].get("carries", 0.0) for w in last),
            "att_pg": _mean(e["weeks"][w].get("attempts", 0.0) for w in last),
            "presence": sum(1 for w in tl if w in wset) / len(tl),
            "missed_latest": tweeks[-1] not in wset,
            "trend": trend,
            "last": {"week": wk[-1], "snap_pct": lw.get("snap_pct"), "targets": lw.get("targets", 0.0),
                     "receptions": lw.get("receptions", 0.0), "tshare": lw.get("tshare", 0.0),
                     "carries": lw.get("carries", 0.0), "pts": lw.get("pts", 0.0), "attempts": lw.get("attempts", 0.0),
                     "rec_yds": lw.get("rec_yds", 0.0), "rush_yds": lw.get("rush_yds", 0.0)},
        }
        players.setdefault(k, []).append(rec)

    sq: dict = {}
    for (_, t), e in pw.items():
        pts = [d.get("pts", 0.0) for d in e["weeks"].values() if _played(d)]
        if len(pts) >= 3 and _mean(pts) >= 6:
            m = _mean(pts)
            sq.setdefault(e["position"], []).extend((x - m) ** 2 * len(pts) / (len(pts) - 1) for x in pts)
    sigma = {pos: (sum(v) / len(v)) ** 0.5 for pos, v in sq.items() if len(v) >= 40}

    through = max((max(v) for v in tw.values() if v), default=0)
    return {"season": season, "stale": stale, "through": through, "players": players, "teams": teams, "sigma": sigma}


def find(us: dict, name: str, tm: str):
    """The usage record for a player, preferring the one on the right team."""
    recs = (us or {}).get("players", {}).get(norm(name)) or []
    tm = team(tm)
    for r in recs:
        if r["team"] == tm:
            return r
    return max(recs, key=lambda r: r["games"]) if len(recs) == 1 else None
