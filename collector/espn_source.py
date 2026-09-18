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


class ESPNSetupError(Exception):
    """A problem we can explain in plain English on the dashboard."""


def validate_credentials() -> list[str]:
    """Returns a list of human-readable problems, empty if things look right.
    Cookies are optional here: a public league works without them, and a
    private one gets a specific message from fetch() when ESPN says so."""
    problems = []
    if not config.LEAGUE_ID:
        problems.append("LEAGUE_ID secret is empty.")
    elif not config.LEAGUE_ID.isdigit():
        problems.append(f"LEAGUE_ID should be digits only, got '{config.LEAGUE_ID}'.")

    s2, swid = config.ESPN_S2 or "", config.ESPN_SWID or ""
    if bool(s2) != bool(swid):
        problems.append("ESPN_S2 and ESPN_SWID must both be set (or both empty for a public league).")
    if s2:
        if len(s2) < 100:
            problems.append(f"ESPN_S2 looks truncated ({len(s2)} chars; a real one is 200+). Re-copy the whole value.")
        if any(c in s2 for c in "\n\r "):
            problems.append("ESPN_S2 contains whitespace or a line break inside it.")
    if swid:
        if not (swid.startswith("{") and swid.endswith("}")):
            problems.append("ESPN_SWID must include the curly braces, e.g. {ABCD-1234-...}.")
        elif len(swid) < 30:
            problems.append(f"ESPN_SWID looks too short ({len(swid)} chars).")
    return problems


def fetch(week: int) -> dict:
    """Returns roster, opponent, and free agents. Raises ESPNSetupError with a
    plain-English reason so main.py can put it on the dashboard."""
    from espn_api.football import League
    from espn_api.requests.espn_requests import ESPNAccessDenied, ESPNInvalidLeague, ESPNUnknownError

    problems = validate_credentials()
    if problems:
        raise ESPNSetupError(" ".join(problems))

    try:
        league = League(
            league_id=int(config.LEAGUE_ID),
            year=config.SEASON,
            espn_s2=config.ESPN_S2,
            swid=config.ESPN_SWID,
        )
    except ESPNAccessDenied:
        if not (config.ESPN_S2 and config.ESPN_SWID):
            raise ESPNSetupError(
                f"League {config.LEAGUE_ID} is private, so ESPN needs your espn_s2 and SWID "
                "cookies. Copy them from fantasy.espn.com into the ESPN_S2 and ESPN_SWID secrets."
            )
        raise ESPNSetupError(
            "ESPN rejected the cookies. They're either expired or from a different "
            "ESPN account than the one in this league. Log in at fantasy.espn.com and "
            "re-copy espn_s2 and SWID."
        )
    except ESPNInvalidLeague:
        raise ESPNSetupError(
            f"ESPN says league {config.LEAGUE_ID} doesn't exist for {config.SEASON}. "
            "Check LEAGUE_ID against the number in your league URL."
        )
    except ValueError as e:
        if "header" in str(e).lower():
            raise ESPNSetupError(
                "A cookie value contains a line break. Edit the ESPN_S2 and ESPN_SWID "
                "secrets and delete any blank line at the end."
            )
        raise ESPNSetupError(f"Unexpected value error: {e}")
    except ESPNUnknownError as e:
        raise ESPNSetupError(f"ESPN returned an unexpected response: {e}")

    my_team = None
    if config.TEAM_NAME:
        for t in league.teams:
            if config.TEAM_NAME.lower() in t.team_name.lower():
                my_team = t
                break
    team_note = ""
    if my_team is None:
        my_team = league.teams[0]
        names = ", ".join(t.team_name for t in league.teams)
        team_note = (f"TEAM_NAME '{config.TEAM_NAME}' didn't match any team, so showing "
                     f"{my_team.team_name}. Teams in this league: {names}.") if config.TEAM_NAME else ""

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
        "team_note": team_note,
    }
