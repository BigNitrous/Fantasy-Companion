"""Last season's fantasy production from nflverse.

nflverse computes PPR points for skill positions but leaves kickers and
defenses at zero, so those are scored here using ESPN's default rules.
"""

from __future__ import annotations

# nflverse -> ESPN team abbreviations where they differ
TEAM_FIX = {"LA": "LAR", "WAS": "WSH"}

# ESPN default D/ST points-allowed tiers (per game)
_PA_TIERS = [(0, 5), (6, 4), (13, 3), (17, 1), (27, 0), (34, -1), (45, -3), (999, -5)]


def _pa_points(pts: int) -> int:
    for ceiling, val in _PA_TIERS:
        if pts <= ceiling:
            return val
    return -5


def _kicker_points(row: dict) -> float:
    fg0 = (row.get("fg_made_0_19") or 0) + (row.get("fg_made_20_29") or 0) + (row.get("fg_made_30_39") or 0)
    fg40 = row.get("fg_made_40_49") or 0
    fg50 = (row.get("fg_made_50_59") or 0) + (row.get("fg_made_60_") or 0)
    pat = row.get("pat_made") or 0
    missed = row.get("fg_missed") or 0
    return 3 * fg0 + 4 * fg40 + 5 * fg50 + 1 * pat - 1 * missed


def load(season: int) -> dict:
    """Returns {name_lower: {name, position, team, points, games, ppg}}.
    D/ST entries are keyed by ESPN team abbreviation, e.g. 'dst:SF'."""
    try:
        import nflreadpy as nfl
        import polars as pl
    except ImportError:
        return {}

    out = {}

    try:
        df = nfl.load_player_stats(seasons=[season], summary_level="reg")
        for r in df.iter_rows(named=True):
            pos = r.get("position") or ""
            if pos not in ("QB", "RB", "WR", "TE", "K"):
                continue
            name = r.get("player_display_name") or ""
            games = r.get("games") or 0
            pts = _kicker_points(r) if pos == "K" else (r.get("fantasy_points_ppr") or 0.0)
            if games <= 0 or pts <= 0:
                continue
            team = TEAM_FIX.get(r.get("recent_team") or "", r.get("recent_team") or "")
            out[name.lower()] = {
                "name": name, "position": pos, "team": team,
                "points": round(float(pts), 1), "games": int(games),
                "ppg": round(float(pts) / games, 1),
            }
    except Exception:
        pass

    # Team defense: aggregate stats plus points allowed from the schedule.
    try:
        ts = nfl.load_team_stats(seasons=[season], summary_level="reg")
        sched = nfl.load_schedules(seasons=[season]).filter(pl.col("game_type") == "REG")
        allowed: dict[str, list[int]] = {}
        for g in sched.iter_rows(named=True):
            if g.get("home_score") is None:
                continue
            allowed.setdefault(g["home_team"], []).append(int(g["away_score"]))
            allowed.setdefault(g["away_team"], []).append(int(g["home_score"]))
        for r in ts.iter_rows(named=True):
            t = r.get("team")
            games = r.get("games") or 0
            if not t or games <= 0:
                continue
            pa = sum(_pa_points(p) for p in allowed.get(t, []))
            pts = (
                1 * (r.get("def_sacks") or 0)
                + 2 * (r.get("def_interceptions") or 0)
                + 2 * (r.get("fumble_recovery_opp") or 0)
                + 6 * (r.get("def_tds") or 0)
                + 6 * (r.get("special_teams_tds") or 0)
                + 2 * (r.get("def_safeties") or 0)
                + 2 * ((r.get("def_punt_blocks") or 0) + (r.get("def_fg_blocks") or 0) + (r.get("def_pat_blocks") or 0))
                + pa
            )
            espn_t = TEAM_FIX.get(t, t)
            out[f"dst:{espn_t}"] = {
                "name": f"{espn_t} D/ST", "position": "D/ST", "team": espn_t,
                "points": round(float(pts), 1), "games": int(games),
                "ppg": round(float(pts) / games, 1),
            }
    except Exception:
        pass

    return out


def lookup(hist: dict, name: str, position: str, team: str) -> dict | None:
    if position == "D/ST":
        return hist.get(f"dst:{team}")
    return hist.get((name or "").strip().lower())
