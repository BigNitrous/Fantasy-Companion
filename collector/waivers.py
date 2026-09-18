"""Waiver wire from who's actually unclaimed in your league.

Every rankings site answers "who's good". This answers "who's available to
you, is he better than someone you'd drop, and who else is chasing him".
Three lists, all league-specific:

- adds: free agents who beat one of your players, best first, each paired
  with the drop that makes room and a one-line reason
- hot: Sleeper's most-added players across all leagues that are still
  unclaimed here -- the ones you'll have to beat rivals to
- just_dropped: players rivals cut in the last few days who are worth a
  look, since a drop is often a panic move

Scores use the same blend as rankings.py so numbers agree across sections.
"""

from __future__ import annotations
import re
from . import history
from .rankings import W_PROJ, W_HIST
from .optimizer import UNAVAILABLE

SKILL = ("QB", "RB", "WR", "TE")
STREAM = ("D/ST", "K")
STASHABLE = ("RB", "WR")   # depth only matters where injuries and flex slots make it matter
MIN_EDGE = 0.5        # score margin before we call a free agent an upgrade
STASH_EDGE = 15.0     # rest-of-season projection margin for a stash
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv)\b\.?", re.I)


def _key(name: str) -> str:
    """Sleeper and ESPN spell names slightly differently; compare loosely."""
    return re.sub(r"[^a-z]", "", _SUFFIX.sub("", (name or "").lower()))


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


def _healthy(p: dict) -> bool:
    return (p.get("injury") or "").upper().replace(" ", "_") not in UNAVAILABLE


def _scored(p: dict, hist: dict) -> dict:
    h = history.lookup(hist, p["name"], p.get("position", ""), p.get("team", ""))
    ppg = h["ppg"] if h else 0.0
    proj = _num(p.get("projected"))
    return {**p, "proj": round(proj, 1), "ppg_2025": round(ppg, 1),
            "ros": round(_num(p.get("ros_projected")), 1),
            "score": round(W_PROJ * proj + W_HIST * ppg, 2)}


def _droppable(roster: list[dict]) -> list[dict]:
    """Bench players you could cut, worst first. IR slots aren't roster spots."""
    out = [p for p in roster if not p.get("starting") and p.get("slot") != "IR"]
    out.sort(key=lambda p: (p["score"], p["ros"]))
    return out


def _drop_for(fa: dict, bench: list[dict]) -> dict | None:
    """Who goes to make room: the weakest bench player at the same position if
    the free agent beats him, otherwise the weakest skill-position bench player.
    Kickers and defenses only ever swap for their own kind."""
    same = [b for b in bench if b.get("position") == fa.get("position")]
    if fa["position"] in STREAM:
        return same[0] if same else None
    if same and same[0]["score"] < fa["score"]:
        return same[0]
    skill = [b for b in bench if b.get("position") in SKILL]
    return skill[0] if skill else None


def build(free_agents: list[dict], roster: list[dict], hist: dict, trending: list[dict],
          activity: list[dict], league: dict, needs: list[dict], team_name: str = "",
          limit: int = 12) -> dict:
    fas = [_scored(p, hist) for p in free_agents]
    mine = [_scored(p, hist) for p in roster]
    bench = _droppable(mine)
    need_pos = {n["position"] for n in needs or []}
    my_names = {_key(p["name"]) for p in roster}

    # Sleeper's most-added, restricted to players unclaimed in this league.
    fa_by_key = {_key(p["name"]): p for p in fas}
    hot = []
    for t in trending or []:
        p = fa_by_key.get(_key(t["name"]))
        if p:
            hot.append({**p, "count": t.get("count", 0)})
    hot_count = {_key(h["name"]): h["count"] for h in hot}

    # Rivals' recent drops that are still on the wire.
    just_dropped, seen = [], set()
    for a in activity or []:
        if a.get("action") != "DROPPED" or (team_name and a.get("team") == team_name):
            continue
        k = _key(a.get("player", ""))
        if k in seen or k in my_names:
            continue
        p = fa_by_key.get(k)
        if p:
            seen.add(k)
            just_dropped.append({**p, "dropped_by": a.get("team", ""), "when": a.get("when", "")})
    dropped_by = {_key(d["name"]): d["dropped_by"] for d in just_dropped}

    # Upgrades: does this free agent beat a starter, a bench player, or the
    # rest-of-season outlook of someone you'd cut?
    adds = []
    for fa in fas:
        pos = fa.get("position")
        if pos not in SKILL + STREAM or not _healthy(fa):
            continue
        drop = _drop_for(fa, bench)
        starters = [p for p in mine if p.get("starting") and p.get("position") == pos]
        worst = min(starters, key=lambda p: p["score"]) if starters else None
        verdict, reason = "", ""

        if pos in STREAM:
            if worst and not fa.get("bye") and fa["proj"] >= worst["proj"] + 1.0:
                verdict, reason = "stream", f"Projects {fa['proj']} vs {worst['proj']} for {worst['name']} this week"
                drop = drop or worst
        else:
            if worst and not fa.get("bye") and fa["score"] >= worst["score"] + MIN_EDGE:
                verdict, reason = "start", f"Would start over {worst['name']} this week"
            elif drop and drop.get("position") == pos and fa["score"] >= drop["score"] + MIN_EDGE:
                verdict, reason = "bench", f"Better right now than {drop['name']} on your bench"
            elif (pos in STASHABLE and drop and (fa["proj"] > 0 or fa.get("bye"))
                  and fa["ros"] >= drop["ros"] + STASH_EDGE):
                verdict, reason = "stash", f"{fa['ros']:.0f} projected rest of season vs {drop['ros']:.0f} for {drop['name']}"
        if not verdict:
            continue

        k = _key(fa["name"])
        adds.append({**fa, "verdict": verdict, "reason": reason,
                     "drop": drop["name"] if drop else "",
                     "need": pos in need_pos,
                     "hot": hot_count.get(k, 0),
                     "dropped_by": dropped_by.get(k, "")})

    order = {"start": 0, "stream": 1, "bench": 2, "stash": 3}
    adds.sort(key=lambda a: (order[a["verdict"]], -a["score"], -a["ros"]))
    hot.sort(key=lambda h: -h["count"])
    just_dropped.sort(key=lambda d: -d["ts"] if d.get("ts") else 0)

    drops = [{**b, "reason": f"{b['score']} score, {b['ros']:.0f} rest of season"
              + (f", rostered in {b['pct_owned']:.0f}% of leagues" if isinstance(b.get("pct_owned"), (int, float)) else "")}
             for b in bench[:5]]

    lg = league or {}
    if lg.get("faab"):
        spent = _num(lg.get("budget_spent"))
        priority = {"kind": "faab", "text": f"FAAB: ${_num(lg.get('budget')) - spent:.0f} of ${_num(lg.get('budget')):.0f} left"}
    elif lg.get("waiver_rank"):
        priority = {"kind": "rank", "text": f"Waiver priority {lg['waiver_rank']} of {lg.get('team_count', '?')}"}
    else:
        priority = {"kind": "", "text": ""}

    return {
        "priority": priority,
        "adds": adds[:limit],
        "hot": hot[:10],
        "just_dropped": just_dropped[:8],
        "drops": drops,
        "activity": (activity or [])[:15],
    }
