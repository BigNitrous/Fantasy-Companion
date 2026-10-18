"""Several projections side by side, and the number the dashboard uses.

- ESPN: ESPN's own projection (Mike Clay's projections help power ESPN's game).
- Sleeper: Sleeper's projections, which are RotoWire's (every record says
  company "rotowire"). Sleeper publishes projected stats, so they're scored
  here with your league's own rules, not Sleeper's defaults.
- Usage (opportunity): nflverse/ffopportunity's expected fantasy points from
  his last few games, i.e. what his targets, carries and throws were worth.
  Shown for context only; it tested worse than either projection.

The dashboard's number is the plain average of ESPN and Sleeper. Backtest on
this league, weeks 1-5 of 2026: the average missed by 5.99 pts per player vs
6.05 for ESPN alone; fitted weights were unstable week to week, so equal
weights (Clemen 1989, Armstrong 2001). Disagreement between the two did not
predict bigger misses, so a split is shown as information, not as risk.

Everything degrades to ESPN alone if Sleeper or nflverse can't be reached.
"""

from __future__ import annotations
import csv
import io

import requests

from . import usage as U

SLEEPER = "https://api.sleeper.com/projections/nfl/{season}/{week}"
EP = "https://github.com/ffverse/ffopportunity/releases/download/latest-data/ep_weekly_{season}.csv"
TIMEOUT = 60
SPLIT = 3.0             # points apart before the sources are called split
USAGE_GAMES = 4         # games averaged for the usage number

# Standard ESPN PPR; the league's own settings override these by ESPN abbreviation.
DEFAULT = {"PY": 0.04, "PTD": 4, "INTT": -2, "RY": 0.1, "RTD": 6, "REC": 1, "REY": 0.1, "RETD": 6, "FUML": -2,
           "2PC": 2, "2PR": 2, "2PRE": 2, "FG0": 3, "FG40": 4, "FG50": 5, "FG60": 6, "PAT": 1, "FGM": -1,
           "SK": 1, "INT": 2, "FR": 2, "SF": 2, "BLKK": 2, "INTTD": 6, "KRTD": 6,
           "PA0": 5, "PA1": 4, "PA7": 3, "PA14": 1, "PA18": 0, "PA22": 0, "PA28": -1, "PA35": -3, "PA46": -5,
           "YA100": 5, "YA199": 3, "YA299": 2, "YA349": 0, "YA399": -1, "YA449": -3, "YA499": -5, "YA549": -6, "YA550": -7}
SKILL_KEYS = {"PY": "pass_yd", "PTD": "pass_td", "INTT": "pass_int", "RY": "rush_yd", "RTD": "rush_td", "REC": "rec",
              "REY": "rec_yd", "RETD": "rec_td", "FUML": "fum_lost", "2PC": "pass_2pt", "2PR": "rush_2pt", "2PRE": "rec_2pt"}
# (start of the next tier, tier): projected points/yards allowed are averages, so 17.5 counts in the 14-17 tier.
PA_TIERS = [(1, "PA0"), (7, "PA1"), (14, "PA7"), (18, "PA14"), (22, "PA18"), (28, "PA22"), (35, "PA28"), (46, "PA35")]
YA_TIERS = [(100, "YA100"), (200, "YA199"), (300, "YA299"), (350, "YA349"), (400, "YA399"), (450, "YA449"),
            (500, "YA499"), (550, "YA549")]


def rules(scoring) -> dict:
    """{ESPN abbreviation: points} from the league settings, on top of standard PPR."""
    out = dict(DEFAULT)
    for s in scoring or []:
        if isinstance(s, dict) and s.get("abbr") in out and isinstance(s.get("points"), (int, float)):
            out[s["abbr"]] = float(s["points"])
    return out


def points(st: dict, pos: str, r: dict) -> float:
    """League points for one player's projected stats (Sleeper stat keys)."""
    g = lambda k: float(st.get(k) or 0)
    if pos == "K":
        fifty = g("fgm_50_59") if "fgm_50_59" in st else g("fgm_50p")
        return (r["FG0"] * (g("fgm_0_19") + g("fgm_20_29") + g("fgm_30_39")) + r["FG40"] * g("fgm_40_49")
                + r["FG50"] * fifty + r["FG60"] * g("fgm_60p") + r["PAT"] * g("xpm") + r["FGM"] * g("fgmiss"))
    if pos == "DEF":
        pa, ya = g("pts_allow"), g("yds_allow")
        pa_pts = next((r[k] for top, k in PA_TIERS if pa < top), r["PA46"])
        ya_pts = next((r[k] for top, k in YA_TIERS if ya < top), r["YA550"])
        return (r["SK"] * g("sack") + r["INT"] * g("int") + r["FR"] * g("fum_rec") + r["SF"] * g("safe")
                + r["BLKK"] * g("blk_kick") + r["INTTD"] * g("def_td") + r["KRTD"] * g("def_st_td") + pa_pts + ya_pts)
    return sum(r[abbr] * g(key) for abbr, key in SKILL_KEYS.items())


def sleeper_week(season: int, week: int, scoring=None) -> dict:
    """{sleeper player id (or 'DEF:KC'): league points} for this week, or {} if unavailable."""
    pos = [("position[]", p) for p in ("QB", "RB", "WR", "TE", "K", "DEF")]
    try:
        r = requests.get(SLEEPER.format(season=season, week=week), params=[("season_type", "regular")] + pos,
                         timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}
    rl, out = rules(scoring), {}
    for d in data or []:
        st, pl = d.get("stats") or {}, d.get("player") or {}
        p = pl.get("position") or ""
        if not st or p not in ("QB", "RB", "WR", "TE", "K", "DEF"):
            continue
        key = f"DEF:{U.team(d.get('player_id'))}" if p == "DEF" else str(d.get("player_id"))
        out[key] = round(points(st, p, rl), 2)
    return out


def usage_points(season: int, week: int) -> dict:
    """{gsis id: average expected fantasy points over his last few games before `week`}."""
    try:
        r = requests.get(EP.format(season=season), timeout=TIMEOUT)
        r.raise_for_status()
        rows = csv.DictReader(io.StringIO(r.content.decode("utf-8")))
    except Exception:
        return {}
    games: dict = {}
    for row in rows:
        try:
            w = int(row["week"])
            if w < week:
                games.setdefault(row["player_id"], []).append((w, float(row["total_fantasy_points_exp"] or 0)))
        except (KeyError, ValueError):
            continue
    out = {}
    for pid, gs in games.items():
        last = [x for _, x in sorted(gs)[-USAGE_GAMES:]]
        if len(last) >= 2:
            out[pid] = round(sum(last) / len(last), 1)
    return out


class Index:
    """Finds a Sleeper id (and NFL gsis id) for an ESPN player: by ESPN id, else name and team."""

    def __init__(self, sleeper_players: dict):
        self.by_espn, self.by_name, self.gsis = {}, {}, {}
        for sid, p in (sleeper_players or {}).items():
            if p.get("espn_id"):
                self.by_espn[str(p["espn_id"])] = sid
            if p.get("full_name"):
                self.by_name[(U.norm(p["full_name"]), U.team(p.get("team")))] = sid
            if p.get("gsis_id"):
                self.gsis[sid] = str(p["gsis_id"]).strip()

    def sleeper_id(self, p: dict) -> str:
        if p.get("position") == "D/ST":
            return f"DEF:{U.team(p.get('team'))}"
        return (self.by_espn.get(str(p.get("espn_id") or "")) or
                self.by_name.get((U.norm(p.get("name")), U.team(p.get("team")))) or "")


def apply(lists, sleeper_proj: dict, usage_pts: dict, index: Index) -> int:
    """Sets each player's 'projected' to the blend and keeps every source's number.
    Returns how many players got a Sleeper number."""
    n, seen = 0, set()
    for players in lists:
        for p in players:
            if id(p) in seen or "sources" in p:
                continue
            seen.add(id(p))
            espn = p.get("projected")
            espn = float(espn) if isinstance(espn, (int, float)) else 0.0
            sid = index.sleeper_id(p)
            sl = sleeper_proj.get(sid)
            p["projected_espn"] = espn
            p["sources"] = {"ESPN": round(espn, 1)}
            if isinstance(sl, (int, float)):
                p["sources"]["Sleeper"] = round(sl, 1)
                n += 1
            # Average the two when both expect him to play. ESPN at 0 means out, bye or IR: keep 0.
            blend = (espn + sl) / 2 if espn > 0 and isinstance(sl, (int, float)) and sl > 0 else espn
            p["projected"] = round(blend, 2)
            p["projected_blend"] = round(blend, 2)
            p["split"] = bool(espn > 0 and isinstance(sl, (int, float)) and sl > 0 and abs(espn - sl) >= SPLIT)
            u = usage_pts.get(index.gsis.get(sid, ""))
            if u is not None and p.get("position") in ("QB", "RB", "WR", "TE"):
                p["usage_pts"] = u
    return n


def line(p: dict) -> str:
    """'ESPN 12.3 · Sleeper 11.8 → 12.1 (split) · usage 10.9/g' for a player, or ''."""
    s = p.get("sources") or {}
    if len(s) < 2:
        return ""
    txt = " · ".join(f"{k} {v:.1f}" for k, v in s.items()) + f" → {p.get('projected_blend', 0):.1f}"
    if p.get("split"):
        hi = max(s, key=s.get)
        txt += f" (sources split, {hi} higher)"
    if p.get("usage_pts") is not None:
        txt += f" · usage {p['usage_pts']:.1f}/g"
    return txt
