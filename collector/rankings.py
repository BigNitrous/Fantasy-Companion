"""Weekly position rankings across the whole league player pool.

Score = 0.65 * this week's ESPN projection + 0.35 * last season's PPR
points per game. The projection carries the matchup and injury context;
the per-game rate keeps a slow start from hiding a proven player.
"""

from __future__ import annotations
from . import history

POSITIONS = ["QB", "RB", "WR", "TE", "D/ST", "K"]
W_PROJ, W_HIST = 0.65, 0.35


def _proj(p: dict) -> float:
    v = p.get("projected")
    return float(v) if isinstance(v, (int, float)) else 0.0


def build(pool: list[dict], hist: dict, my_names: set[str], top_n: int = 30) -> dict:
    """pool: every player in the league (all rosters + free agents), with
    an 'owner' key naming the fantasy team or '' for free agents."""
    ranked: dict[str, list[dict]] = {pos: [] for pos in POSITIONS}
    seen: set[str] = set()

    for p in pool:
        pos = p.get("position")
        if pos not in ranked or p["name"] in seen:
            continue
        seen.add(p["name"])
        h = history.lookup(hist, p["name"], pos, p.get("team", ""))
        ppg = h["ppg"] if h else 0.0
        total = h["points"] if h else 0.0
        proj = _proj(p)
        score = W_PROJ * proj + W_HIST * ppg
        ranked[pos].append({
            **p,
            "proj": round(proj, 1),
            "ppg_2025": round(ppg, 1),
            "pts_2025": round(total, 1),
            "score": round(score, 2),
            "mine": p["name"] in my_names,
        })

    for pos in ranked:
        ranked[pos].sort(key=lambda r: r["score"], reverse=True)
        for i, r in enumerate(ranked[pos], 1):
            r["rank"] = i
        ranked[pos] = ranked[pos][:top_n]

    return ranked
