"""Finds the highest-projected legal lineup and lists the swaps to get there.

Slot structure is read off your current roster rather than configured, so
it adapts to whatever your league uses. Specific slots are filled before
FLEX, which is optimal when every slot scores the same.
"""

from __future__ import annotations

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


def slot_structure(roster: list[dict]) -> list[str]:
    """Ordered list of starting slots, one entry per slot."""
    slots = [p.get("slot", "") for p in roster if p.get("slot") not in BENCH]
    order = ["QB", "RB", "WR", "TE", "FLEX", "RB/WR/TE", "RB/WR", "WR/TE", "OP", "D/ST", "K"]
    return sorted(slots, key=lambda s: order.index(s) if s in order else 99)


def optimize(roster: list[dict]) -> dict:
    slots = slot_structure(roster)
    if not slots:
        return {"lineup": [], "swaps": [], "gain": 0.0, "current_total": 0.0, "optimal_total": 0.0}

    pool = [p for p in roster if _playable(p)]
    used: set[str] = set()
    lineup: list[dict] = []

    def take(eligible: set[str], slot: str):
        cands = [p for p in pool if p["name"] not in used and p.get("position") in eligible]
        if not cands:
            lineup.append({"slot": slot, "player": None})
            return
        best = max(cands, key=_proj)
        used.add(best["name"])
        lineup.append({"slot": slot, "player": best})

    # Fixed slots first, flex last.
    for s in slots:
        if s not in FLEX_LIKE:
            take({s}, s)
    for s in slots:
        if s in FLEX_LIKE:
            take(FLEX_ELIGIBLE[s], s)

    current_starters = {p["name"] for p in roster if p.get("starting")}
    optimal_starters = {e["player"]["name"] for e in lineup if e["player"]}

    current_total = sum(_proj(p) for p in roster if p.get("starting"))
    optimal_total = sum(_proj(e["player"]) for e in lineup if e["player"])

    bench_in = [p for p in roster if p["name"] in optimal_starters - current_starters]
    starters_out = [p for p in roster if p["name"] in current_starters - optimal_starters]

    swaps = []
    # Pair them by position where possible so the advice reads naturally.
    remaining_out = list(starters_out)
    for p_in in sorted(bench_in, key=_proj, reverse=True):
        match = next((o for o in remaining_out if o.get("position") == p_in.get("position")), None)
        if match is None and remaining_out:
            match = remaining_out[0]
        if match:
            remaining_out.remove(match)
            swaps.append({"in": p_in, "out": match, "gain": round(_proj(p_in) - _proj(match), 1)})
        else:
            swaps.append({"in": p_in, "out": None, "gain": round(_proj(p_in), 1)})

    return {
        "lineup": lineup,
        "swaps": swaps,
        "gain": max(0.0, round(optimal_total - current_total, 1)),  # avoids -0.0 when already optimal
        "current_total": round(current_total, 1),
        "optimal_total": round(optimal_total, 1),
    }
