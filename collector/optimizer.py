"""Finds the lineup with the most expected points and lists the swaps to get there.

Players are valued with collector/expect.py, the same numbers the confidence
meter uses, so a recommended swap never lowers the meter. A starter who might
not play is credited with a bench backup whose game kicks off at or after his
(you'd swap at inactives); without one he counts at his chance to play.
Specific slots are filled before FLEX, which is optimal for fixed values; the
handful of uncertain players are tried in and out to find the best lineup.
"""

from __future__ import annotations
from itertools import combinations

from . import expect

FLEX_LIKE = {"FLEX", "RB/WR/TE", "RB/WR", "WR/TE", "OP"}
FLEX_ELIGIBLE = {
    "FLEX": {"RB", "WR", "TE"}, "RB/WR/TE": {"RB", "WR", "TE"},
    "RB/WR": {"RB", "WR"}, "WR/TE": {"WR", "TE"},
    "OP": {"QB", "RB", "WR", "TE"},
}
BENCH = {"BE", "IR", ""}
UNAVAILABLE = {"OUT", "IR", "SUSPENSION", "INJURY_RESERVE", "DOUBTFUL"}


def _proj(p: dict) -> float:
    v = p.get("projected")
    return float(v) if isinstance(v, (int, float)) else 0.0


def _playable(p: dict) -> bool:
    if (p.get("injury") or "").upper().replace(" ", "_") in UNAVAILABLE:
        return False
    if p.get("slot") == "IR":
        return False
    return True


LEAGUE_SLOTS = None     # starting slots from the league settings; set once per run


def set_league_slots(slots) -> None:
    """Use the league's real lineup slots instead of inferring them from the roster. Inferring
    makes a dropped kicker silently remove the K slot instead of leaving a hole to fill."""
    global LEAGUE_SLOTS
    LEAGUE_SLOTS = list(slots) if slots else None


def slot_structure(roster: list[dict]) -> list[str]:
    """Ordered list of starting slots, one entry per slot."""
    if LEAGUE_SLOTS:
        slots = list(LEAGUE_SLOTS)
    else:
        slots = [p.get("slot", "") for p in roster if p.get("slot") not in BENCH]
    order = ["QB", "RB", "WR", "TE", "FLEX", "RB/WR/TE", "RB/WR", "WR/TE", "OP", "D/ST", "K"]
    return sorted(slots, key=lambda s: order.index(s) if s in order else 99)


def eligible(slot: str) -> set:
    return FLEX_ELIGIBLE.get(slot) or {slot}


def evaluate(lineup: list[dict], roster: list[dict]):
    """(expected points, {starter: backup}) for a lineup drawn from roster."""
    starters = {e["player"]["name"] for e in lineup if e.get("player")}
    bench = [p for p in roster if p["name"] not in starters and _playable(p) and not p.get("locked")]
    backups = expect.backup_for(lineup, bench, eligible)
    total = sum(expect.value(e["player"], backups.get(e["player"]["name"])) for e in lineup if e.get("player"))
    return total, backups


def _fill(slots: list[str], pool: list[dict], key) -> list[dict]:
    used: set = set()
    out: list[dict] = []

    def take(ok: set, slot: str):
        cands = [p for p in pool if p["name"] not in used and p.get("position") in ok]
        best = max(cands, key=key) if cands else None
        if best:
            used.add(best["name"])
        out.append({"slot": slot, "player": best})

    for s in slots:                        # fixed slots first, flex last
        if s not in FLEX_LIKE:
            take({s}, s)
    for s in slots:
        if s in FLEX_LIKE:
            take(FLEX_ELIGIBLE[s], s)
    return out


MAX_UNCERTAIN = 6       # uncertain players tried in and out (2^6 lineups at most)


def optimize(roster: list[dict]) -> dict:
    slots = slot_structure(roster)
    if not slots:
        return {"lineup": [], "swaps": [], "gain": 0.0, "current_total": 0.0, "optimal_total": 0.0,
                "backups": {}, "current_backups": {}, "alternatives": []}

    # Once a game kicks off, its starters stay in their slots and its bench players stay benched.
    free = list(slots)
    fixed: list[dict] = []
    for p in roster:
        if p.get("locked") and p.get("starting") and p.get("slot") in free:
            free.remove(p["slot"])
            fixed.append({"slot": p["slot"], "player": p})
    pool = [p for p in roster if _playable(p) and not p.get("locked")]
    unc = sorted((p for p in pool if expect.uncertain(p)), key=expect.if_plays, reverse=True)[:MAX_UNCERTAIN]
    unc_names = {p["name"] for p in unc}
    sure = [p for p in pool if not expect.uncertain(p)]
    rank = {s: i for i, s in enumerate(slots)}
    current_starters = {p["name"] for p in roster if p.get("starting")}

    def key(p):
        return expect.if_plays(p) if p["name"] in unc_names else expect.mean(p)

    # Try every combination of uncertain players; evaluate each lineup with its backups.
    best, alt = None, {}
    for k in range(len(unc) + 1):
        for chosen in combinations(unc, k):
            lineup = sorted(fixed + _fill(free, sure + list(chosen), key), key=lambda e: rank.get(e["slot"], 99))
            total, backups = evaluate(lineup, roster)
            names = {e["player"]["name"] for e in lineup if e.get("player")}
            score = (round(total, 2), len(names & current_starters))     # ties keep your current lineup
            if best is None or score > best[0]:
                best = (score, lineup, total, backups, names)
            for u in names & unc_names:
                if u not in alt or total > alt[u][1]:
                    alt[u] = (lineup, total, backups)
    _, lineup, optimal_total, backups, optimal_starters = best

    current = [{"slot": p.get("slot", ""), "player": p} for p in roster if p.get("starting")]
    current_total, current_backups = evaluate(current, roster)

    def val_in(p, bk):
        return expect.value(p, bk.get(p["name"]))

    bench_in = [p for p in roster if p["name"] in optimal_starters - current_starters]
    starters_out = [p for p in roster if p["name"] in current_starters - optimal_starters]
    swaps = []
    # Pair them by position where possible so the advice reads naturally.
    remaining_out = list(starters_out)
    for p_in in sorted(bench_in, key=lambda p: val_in(p, backups), reverse=True):
        match = next((o for o in remaining_out if o.get("position") == p_in.get("position")), None)
        if match is None and remaining_out:
            match = remaining_out[0]
        g_in = val_in(p_in, backups)
        if match:
            remaining_out.remove(match)
            swaps.append({"in": p_in, "out": match, "gain": round(g_in - val_in(match, current_backups), 1)})
        else:
            swaps.append({"in": p_in, "out": None, "gain": round(g_in, 1)})

    # Uncertain players who'd start if they were sure to play, and what starting them is worth.
    alternatives = []
    for u in unc:
        if u["name"] in optimal_starters or u["name"] not in alt:
            continue
        a_lineup, a_total, a_backups = alt[u["name"]]
        alternatives.append({"player": u, "lineup": a_lineup, "total": round(a_total, 1),
                             "backup": a_backups.get(u["name"]), "cost": round(optimal_total - a_total, 1)})

    return {
        "lineup": lineup,
        "swaps": swaps,
        "gain": max(0.0, round(optimal_total - current_total, 1)),  # avoids -0.0 when already optimal
        "current_total": round(current_total, 1),
        "optimal_total": round(optimal_total, 1),
        "backups": {k: v["name"] for k, v in backups.items()},
        "current_backups": {k: v["name"] for k, v in current_backups.items()},
        "alternatives": alternatives,
    }
