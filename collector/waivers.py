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

Pickup decisions use this week's lineup, not a blended score: each candidate
add/drop pair is judged by re-running the lineup optimizer with that swap made,
so the waiver wire and the lineup section always agree. The rules are
antisymmetric (see _judge): if "add X, drop Y" qualifies, "add Y, drop X" can't
on the same data, so following the advice never makes the next build undo it.
The blended score (same as rankings.py) is still shown, but decides nothing.
"""

from __future__ import annotations
import re
from collections import Counter
from . import expect, history, optimizer
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


def _week(p: dict) -> float:
    """This week's expected points as the lineup optimizer and the meter see them
    (0 if he can't play for you this week)."""
    if not optimizer._playable(p) or p.get("bye") or (p.get("locked") and not p.get("starting")):
        return 0.0
    return expect.mean(p)


def _droppable(roster: list[dict]) -> list[dict]:
    """Bench players you could cut, least valuable first. IR slots aren't roster spots, and
    a player whose game has kicked off can't be dropped until it's over."""
    out = [p for p in roster if not p.get("starting") and p.get("slot") != "IR" and not p.get("locked")]
    out.sort(key=lambda p: (p["ros"], _week(p)))
    return out


def _judge(fa: dict, drop, roster: list[dict], base_total: float, base_lineup: set, fills: bool = False):
    """Scores one add/drop pair. Returns (verdict, week_gain, ros_gain, displaced starters).

    week_gain is the change in your best lineup's projection with the swap made, and
    ros_gain the change in rest-of-season projection. Both flip sign exactly when the
    pair is reversed, which is what keeps the advice from undoing itself:
      fill   (his slot is empty in your best lineup) week_gain >= MIN_EDGE
      start  week_gain >= MIN_EDGE and ros_gain > -STASH_EDGE
      stream (K, D/ST) week_gain >= 1.0
      bench  week_gain >= 0, same position, this week >= his by MIN_EDGE, ros_gain > -STASH_EDGE
      stash  ros_gain >= STASH_EDGE and week_gain >= 0
    """
    gone = drop["name"] if drop else None
    after = [p for p in roster if p["name"] != gone] + [fa]
    opt = optimizer.optimize(after)
    gain = opt["optimal_total"] - base_total
    new_lineup = {e["player"]["name"] for e in opt["lineup"] if e.get("player")}
    displaced = [n for n in base_lineup - new_lineup if n != gone]
    ros_gain = fa["ros"] - (drop["ros"] if drop else 0.0)
    pos = fa.get("position")
    eps = 0.05                                     # rounding noise in projected totals
    if fills:
        return ("fill" if gain >= MIN_EDGE - eps else ""), gain, ros_gain, displaced
    if pos in STREAM:
        return ("stream" if gain >= 1.0 - eps else ""), gain, ros_gain, displaced
    if gain >= MIN_EDGE - eps and ros_gain > -STASH_EDGE:
        return "start", gain, ros_gain, displaced
    if (gain >= -eps and drop and drop.get("position") == pos and ros_gain > -STASH_EDGE
            and _week(fa) >= _week(drop) + MIN_EDGE):
        return "bench", gain, ros_gain, displaced
    if (pos in STASHABLE and drop and gain >= -eps and ros_gain >= STASH_EDGE
            and (fa["proj"] > 0 or fa.get("bye"))):
        return "stash", gain, ros_gain, displaced
    return "", gain, ros_gain, displaced


def build(free_agents: list[dict], roster: list[dict], hist: dict, trending: list[dict],
          activity: list[dict], league: dict, needs: list[dict], team_name: str = "",
          limit: int = 12) -> dict:
    fas = [_scored(p, hist) for p in free_agents]
    mine = [_scored(p, hist) for p in roster]
    bench = _droppable(mine)
    # A slot is empty only if your best lineup can't fill it (not just because nobody is set there).
    base = optimizer.optimize(mine)
    base_total = base["optimal_total"]
    base_lineup = {e["player"]["name"] for e in base["lineup"] if e.get("player")}
    empty = {e["slot"] for e in base["lineup"] if not e.get("player") and e["slot"] in SKILL + STREAM}
    room = bool((league or {}).get("roster_limit")) and len(roster) < league["roster_limit"]
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

    # Upgrades: try each free agent against every player you could drop, keep the best pair.
    rank = {"fill": -1, "start": 0, "stream": 1, "bench": 2, "stash": 3}
    adds = []
    for fa in fas:
        pos = fa.get("position")
        if pos not in SKILL + STREAM or not _healthy(fa):
            continue
        fills = pos in empty
        if fills:               # an empty slot: anyone on the bench can make room
            options = [b for b in bench if b.get("position") in SKILL + STREAM]
        elif pos in STREAM:     # kickers and defenses only swap for their own kind, starter included
            options = [p for p in mine if p.get("position") == pos and p.get("slot") != "IR" and not p.get("locked")]
        else:
            options = [b for b in bench if b.get("position") in SKILL]
        if room:
            options = [None] + options          # an open roster spot: add without dropping anyone

        best = None
        for d in options:
            v, gain, ros_gain, displaced = _judge(fa, d, mine, base_total, base_lineup, fills)
            if not v:
                continue
            key = (rank[v], -round(gain, 1), -ros_gain)
            if best is None or key < best[0]:
                best = (key, v, d, gain, ros_gain, displaced)
        if best is None:
            continue
        _, verdict, drop, gain, ros_gain, displaced = best
        if verdict == "fill":
            reason = f"Fills your empty {pos} slot (+{gain:.1f})"
        elif verdict == "start":
            reason = (f"Would start over {', '.join(displaced)} this week (+{gain:.1f})" if displaced
                      else f"Raises your best lineup by +{gain:.1f} this week")
        elif verdict == "stream":
            reason = f"Projects {fa['proj']} vs {drop['proj']} for {drop['name']} this week" if drop \
                else f"Raises your best lineup by +{gain:.1f} this week"
        elif verdict == "bench":
            reason = f"Projects {_week(fa):.1f} vs {_week(drop):.1f} for {drop['name']} this week"
        else:
            vs = f"{drop['ros']:.0f} for {drop['name']}" if drop else "an open roster spot"
            reason = f"{fa['ros']:.0f} projected rest of season vs {vs}"
        if fa.get("locked"):
            reason += ". His game this week has already kicked off"
        if (fa.get("boost") or 0) >= 1.0:
            reason += f". Inherits a bigger role: +{fa['boost']} ({fa.get('boost_why', '')})"

        k = _key(fa["name"])
        adds.append({**fa, "verdict": verdict, "reason": reason,
                     "drop": drop["name"] if drop else "",
                     "gain": round(gain, 1), "ros_gain": round(ros_gain, 1),
                     "need": pos in need_pos,
                     "hot": hot_count.get(k, 0),
                     "dropped_by": dropped_by.get(k, "")})

    order = {"fill": -1, "start": 0, "stream": 1, "bench": 2, "stash": 3}
    # Best this-week gain first within each verdict; rest of season breaks ties.
    adds.sort(key=lambda a: (order[a["verdict"]], -(a["proj"] if a["verdict"] == "fill" else a["gain"]), -a["ros_gain"]))
    kept, fills = [], Counter()
    for a in adds:                         # every free kicker fills an empty K slot; the best few are enough
        if a["verdict"] == "fill":
            fills[a["position"]] += 1
            if fills[a["position"]] > 3:
                continue
        kept.append(a)
    adds = kept
    hot.sort(key=lambda h: -h["count"])
    just_dropped.sort(key=lambda d: -d["ts"] if d.get("ts") else 0)

    drops = [{**b, "reason": f"{_week(b):.1f} this week, {b['ros']:.0f} rest of season"
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
