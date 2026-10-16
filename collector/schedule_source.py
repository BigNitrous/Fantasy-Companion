"""This week's NFL slate from ESPN's public scoreboard: who plays which day,
and who is on a bye. Used to split the week into days and to catch a starter
who has no game."""

from __future__ import annotations
from datetime import datetime

import requests

SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
TIMEOUT = 30
ABBR = {"WAS": "WSH", "LA": "LAR", "JAC": "JAX"}


def _ab(a: str) -> str:
    a = (a or "").upper()
    return ABBR.get(a, a)


def slate(week: int, season: int) -> dict:
    """{"bye": {team}, "day": {team: 'Thu'}, "kickoff": {team: 'Sun 12:00 PM'}, "opp": {team: opponent},
    "final": {team}, "started": {team whose game has kicked off or finished}} or {} if unavailable."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Chicago")
    except Exception:
        tz = None
    try:
        r = requests.get(SITE, params={"week": week, "seasontype": 2, "dates": season}, timeout=TIMEOUT)
        r.raise_for_status()
        d = r.json()
    except Exception:
        return {}
    if (d.get("week") or {}).get("number") != week:
        return {}
    out = {"bye": {_ab(t.get("abbreviation")) for t in (d.get("week") or {}).get("teamsOnBye", [])},
           "day": {}, "kickoff": {}, "final": set(), "started": set(), "opp": {}}
    for e in d.get("events", []):
        try:
            when = datetime.strptime(e["date"], "%Y-%m-%dT%H:%MZ")
            from datetime import timezone
            when = when.replace(tzinfo=timezone.utc)
            if tz:
                when = when.astimezone(tz)
            comp = e["competitions"][0]
            stype = e.get("status", {}).get("type", {})
            final = stype.get("completed") is True
            started = final or stype.get("state") in ("in", "post")
            abbrs = [_ab(c["team"]["abbreviation"]) for c in comp["competitors"]]
            if len(abbrs) == 2:
                out["opp"][abbrs[0]], out["opp"][abbrs[1]] = abbrs[1], abbrs[0]
            for c in comp["competitors"]:
                ab = _ab(c["team"]["abbreviation"])
                out["day"][ab] = when.strftime("%a")
                out["kickoff"][ab] = when.strftime("%a %-I:%M %p")
                if final:
                    out["final"].add(ab)
                if started:
                    out["started"].add(ab)
        except Exception:
            continue
    return out if out["day"] else {}
