"""This week's expected points for one player.

The lineup optimizer, the waiver wire and the confidence meter all rank players
by these numbers, so a recommended move always raises the meter.

- mean(p): projection (ESPN + Sleeper average, role boost included) times the
  chance he plays, times LIMITED when a tagged player plays.
- A starter who might not play (Questionable, Day-to-day) can be covered by a
  bench player whose game kicks off at or after his: you start the questionable
  player and swap at inactives if he's out. backup_for() finds that player;
  with no such backup his value is simply mean(p).

Backtested on 2022-2026 injury reports and snap counts, and this league's 2026
weeks: fantasy-relevant Questionable players played 74% of the time (RB/WR/TE,
n=852) but QBs only 40% (n=123); Doubtful 1% (n=106). Questionable players
who played scored 80-84% of normal. Last week's usage jump predicted the
opposite of what it suggested (players regressed), so MOMENTUM_WEIGHT is 0.
"""

from __future__ import annotations

P_PLAY = {"ACTIVE": 1.0, "NORMAL": 1.0, "": 1.0, "PROBABLE": 0.95, "QUESTIONABLE": 0.74, "DAY_TO_DAY": 0.75,
          "DOUBTFUL": 0.02, "OUT": 0.0, "IR": 0.0, "INJURY_RESERVE": 0.0, "SUSPENSION": 0.0}
P_PLAY_QB = {"QUESTIONABLE": 0.40}           # questionable starting QBs sit far more often
LIMITED = {"QUESTIONABLE": 0.85, "DOUBTFUL": 0.85}   # share of the projection a tagged player scores when he plays
MOMENTUM_WEIGHT = 0.0       # was 0.2; backtest: -0.43 (95% range -0.66 to -0.19), so it's off
SURE = 0.9                  # at or above this, treat the player as certain to play
PPC, PPT = 0.60, {"RB": 1.5, "WR": 1.7, "TE": 1.6}     # points per carry / per target, PPR


def num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


def status(p: dict) -> str:
    return (p.get("injury") or "").upper().replace(" ", "_")


def p_play(p: dict) -> float:
    if p.get("bye"):
        return 0.0
    st = status(p)
    if p.get("position") == "QB" and st in P_PLAY_QB:
        return P_PLAY_QB[st]
    return P_PLAY.get(st, 1.0)


def momentum(p: dict) -> float:
    """Last week's usage against his own recent baseline, as points, times MOMENTUM_WEIGHT
    (0: the backtest found usage jumps regress, and the projections already react to them)."""
    u = p.get("usage") or {}
    last = u.get("last") or {}
    pos = p.get("position")
    if not last or u.get("games", 0) < 3 or pos not in ("RB", "WR", "TE"):
        return 0.0
    if pos == "RB":
        pts = (last["carries"] - u.get("carries_pg", 0.0)) * PPC + (last["targets"] - u.get("targets_pg", 0.0)) * PPT["RB"]
    else:
        pts = (last["targets"] - u.get("targets_pg", 0.0)) * PPT[pos]
    return max(-2.0, min(2.0, MOMENTUM_WEIGHT * pts))


def if_plays(p: dict) -> float:
    """Expected points given that he plays (a tagged player who plays scores less)."""
    proj = num(p.get("projected"))
    return (proj + momentum(p)) * LIMITED.get(status(p), 1.0) if proj > 0 else 0.0


def mean(p: dict) -> float:
    """Expected points with no backup plan: if_plays x chance he plays."""
    return if_plays(p) * p_play(p)


def uncertain(p: dict) -> bool:
    return 0.0 < p_play(p) < SURE


def can_cover(backup: dict, starter: dict) -> bool:
    """A backup can replace an inactive starter only if his game hasn't started by the
    time the starter is ruled out, i.e. it kicks off at the same time or later."""
    a, b = starter.get("kickoff_ts"), backup.get("kickoff_ts")
    return a is not None and b is not None and b >= a and not backup.get("locked")


def backup_for(lineup: list[dict], bench: list[dict], eligible) -> dict:
    """{starter name: backup player} for each uncertain starter that a bench player can
    cover. eligible(slot) -> set of positions. Each backup covers one starter; the
    least likely to play gets first pick."""
    out, used = {}, set()
    for e in sorted((e for e in lineup if e.get("player") and uncertain(e["player"]) and not e["player"].get("locked")),
                    key=lambda e: p_play(e["player"])):
        q, ok = e["player"], eligible(e["slot"])
        cands = [b for b in bench if b["name"] not in used and b.get("position") in ok
                 and p_play(b) >= SURE and mean(b) > 0 and can_cover(b, q)]
        if cands:
            best = max(cands, key=mean)
            used.add(best["name"])
            out[q["name"]] = best
    return out


def value(p: dict, backup: dict = None) -> float:
    """Expected points for a starter, crediting his backup if he's ruled out."""
    pp = p_play(p)
    return pp * if_plays(p) + (1.0 - pp) * (mean(backup) if backup else 0.0)
