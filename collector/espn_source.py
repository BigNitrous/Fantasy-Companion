"""Pulls your team out of ESPN.

Public leagues need nothing. Private leagues need the espn_s2 and SWID
cookies -- see the README for where to find them.
"""

from __future__ import annotations
from . import config

STARTER_SLOTS = {"QB", "RB", "WR", "TE", "FLEX", "RB/WR/TE", "D/ST", "K", "OP"}


def _player_dict(p, week):
    stats = getattr(p, "stats", {}) or {}
    wk = stats.get(week, {}) if isinstance(stats, dict) else {}
    opponent = ""
    sched = getattr(p, "schedule", {}) or {}
    if isinstance(sched, dict):
        game = sched.get(week) or sched.get(str(week))
        if isinstance(game, dict):
            opponent = game.get("team", "")
    return {
        "name": getattr(p, "name", "?"),
        "position": getattr(p, "position", ""),
        "team": getattr(p, "proTeam", ""),
        "slot": getattr(p, "lineupSlot", ""),
        "injury": (getattr(p, "injuryStatus", "") or "ACTIVE").upper(),
        "projected": wk.get("projected_points"),
        "actual": wk.get("points"),
        "pos_rank": getattr(p, "posRank", None),
        "pct_owned": getattr(p, "percent_owned", None),
        "pct_started": getattr(p, "percent_started", None),
        "opponent": opponent,
        "starting": getattr(p, "lineupSlot", "") in STARTER_SLOTS,
        "eligible": list(getattr(p, "eligibleSlots", []) or []),
    }


def fetch(week: int) -> dict:
    """Returns roster, opponent, and free agents. Raises on failure so the
    caller can decide whether to fall back."""
    from espn_api.football import League

    league = League(
        league_id=int(config.LEAGUE_ID),
        year=config.SEASON,
        espn_s2=config.ESPN_S2,
        swid=config.ESPN_SWID,
    )

    my_team = None
    if config.TEAM_NAME:
        for t in league.teams:
            if config.TEAM_NAME.lower() in t.team_name.lower():
                my_team = t
                break
    if my_team is None:
        # Fall back to whichever team the cookies belong to, else first team.
        my_team = league.teams[0]

    roster = [_player_dict(p, week) for p in my_team.roster]

    # Find this week's opponent from the schedule.
    opponent_name, opponent_roster = "", []
    try:
        idx = week - 1
        if 0 <= idx < len(my_team.schedule):
            opp = my_team.schedule[idx]
            opponent_name = opp.team_name
            opponent_roster = [_player_dict(p, week) for p in opp.roster]
    except Exception:
        pass

    # Every roster in the league, tagged with owner, for rankings and trades.
    league_pool = []
    for t in league.teams:
        for p in t.roster:
            d = _player_dict(p, week)
            d["owner"] = t.team_name
            league_pool.append(d)

    free_agents = []
    try:
        seen = set()
        fa_iter = list(league.free_agents(week=week, size=config.FREE_AGENT_POOL))
        for pos in ("D/ST", "K", "QB", "TE"):
            try:
                fa_iter += league.free_agents(week=week, size=15, position=pos)
            except Exception:
                pass
        for p in fa_iter:
            if p.name in seen:
                continue
            seen.add(p.name)
            d = _player_dict(p, week)
            d["owner"] = ""
            free_agents.append(d)
    except Exception:
        pass

    return {
        "team_name": my_team.team_name,
        "record": f"{my_team.wins}-{my_team.losses}",
        "roster": roster,
        "opponent_name": opponent_name,
        "opponent_roster": opponent_roster,
        "free_agents": free_agents,
        "league_pool": league_pool + free_agents,
        "league_name": getattr(league.settings, "name", ""),
    }
