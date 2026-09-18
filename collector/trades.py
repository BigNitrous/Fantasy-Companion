"""Trade targets.

Logic, in plain terms:
- The league's typical starter at each position is the median score among
  everyone currently in a starting slot at that position.
- You *need* a position when your best starter there is below that median.
- You have a *chip* when a bench player of yours is above it.
- A *target* is a player on another team where that team has more
  above-median players at the position than starting slots -- surplus
  they can afford to move.
- *Buy low* flags proven players (strong 2025 rate) whose projection this
  week is soft, which is often when their owner is most willing to deal.
"""

from __future__ import annotations
from statistics import median
from . import optimizer, rankings

_POS = rankings.POSITIONS


def _median_starter(pool: list[dict], pos: str) -> float:
    vals = [p["score"] for p in pool if p.get("position") == pos and p.get("starting") and p.get("owner")]
    return median(vals) if vals else 0.0


def build(pool: list[dict], my_team: str, my_roster_slots: list[str]) -> dict:
    mine = [p for p in pool if p.get("owner") == my_team]
    others = [p for p in pool if p.get("owner") and p.get("owner") != my_team]

    med = {pos: _median_starter(pool, pos) for pos in _POS}

    # Needs and chips
    needs, chips = [], []
    for pos in _POS:
        my_starters = [p for p in mine if p["position"] == pos and p.get("starting")]
        best = max((p["score"] for p in my_starters), default=0.0)
        if my_starters and best < med[pos]:
            gap = round(med[pos] - best, 1)
            if gap >= 0.1:  # a gap that rounds to zero isn't a hole
                needs.append({"position": pos, "best": round(best, 1), "median": round(med[pos], 1), "gap": gap})
        for p in mine:
            if p["position"] == pos and not p.get("starting") and p["score"] > med[pos]:
                chips.append({**p, "median": round(med[pos], 1)})
    needs.sort(key=lambda n: -n["gap"])
    chips.sort(key=lambda c: -c["score"])

    # Starting slot counts per position, inferred from my roster
    slots = my_roster_slots
    slot_count = {pos: sum(1 for s in slots if s == pos) for pos in _POS}
    flex_slots = sum(1 for s in slots if s in optimizer.FLEX_LIKE)

    # Targets: players at my need positions on teams with surplus there
    targets = []
    need_pos = [n["position"] for n in needs] or ["RB", "WR"]  # default to the scarce ones
    by_owner: dict[str, list[dict]] = {}
    for p in others:
        by_owner.setdefault(p["owner"], []).append(p)

    for owner, plist in by_owner.items():
        for pos in need_pos:
            above = sorted([p for p in plist if p["position"] == pos and p["score"] > med[pos]],
                           key=lambda p: -p["score"])
            allowance = slot_count.get(pos, 1) + (1 if pos in ("RB", "WR", "TE") and flex_slots else 0)
            surplus = above[allowance:] if len(above) > allowance else []
            for p in surplus:
                targets.append({**p, "reason": f"{owner} has {len(above)} above-median {pos}s for {allowance} starting slot{'s' if allowance != 1 else ''}"})
    targets.sort(key=lambda t: -t["score"])

    # Buy low: proven last year, soft projection now
    buy_low = []
    for p in others:
        if p.get("ppg_2025", 0) >= 12 and p.get("proj", 0) < 0.7 * p["ppg_2025"] and p["position"] in ("QB", "RB", "WR", "TE"):
            buy_low.append({**p, "reason": f"averaged {p['ppg_2025']} last season, projected {p['proj']} this week"})
    buy_low.sort(key=lambda b: -(b["ppg_2025"] - b["proj"]))

    return {
        "needs": needs,
        "chips": chips[:6],
        "targets": targets[:12],
        "buy_low": buy_low[:8],
        "medians": {k: round(v, 1) for k, v in med.items()},
    }
