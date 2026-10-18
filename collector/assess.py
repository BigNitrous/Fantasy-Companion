"""The routine assessment: how the week is likely to go, and what to do about it.

Everything here is arithmetic on numbers already on the dashboard, so it is
reproducible and you can see why it says what it says.

Week confidence is the chance your lineup outscores this week's opponent.
Each player is a distribution: mean = projection x chance to play, spread
= the measured week-to-week variation of his position (nflverse, this
season), with the extra variance of a player who may not suit up. Team means
and variances add up; the gap between you and the opponent over the combined
spread gives a win probability. Day scores use the same method on the
starters who play that day, against a typical starter at each position.

Player outlook is the chance that player outscores a typical starter at his
position this week. A bye or an out player is 0.

All of it is a projection, not a promise: one game of football is noisy and
the projections come from ESPN. The score tells you how much to trust the
lineup, not what will happen.
"""

from __future__ import annotations
import math
from datetime import datetime

from . import expect, optimizer
from .usage import team as _team

SIGMA_FALLBACK = {"QB": 7.6, "RB": 7.4, "WR": 8.0, "TE": 7.4, "K": 5.6, "D/ST": 5.4}   # K, D/ST measured, 2026 wks 1-5
P_PLAY, PPC, PPT = expect.P_PLAY, expect.PPC, expect.PPT          # shared with the optimizer
DAY_ORDER = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"]
POSITIONS = ("QB", "RB", "WR", "TE", "K", "D/ST")
MODES = {
    "checkup": ("Tuesday check-up", "Before waivers: who to add and what to change"),
    "gameday": ("Game-day report", "Every player on your roster, weighed"),
    "midweek": ("Weekly outlook", "Where your lineup stands"),
}


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


_status = expect.status


def _pct(x) -> str:
    return f"{x * 100:.0f}%"


def band(score: int) -> str:
    for floor, label in ((75, "Strong favorite"), (60, "Favored"), (52, "Slight edge"), (48, "Toss-up"),
                         (40, "Slight underdog"), (25, "Underdog")):
        if score >= floor:
            return label
    return "Long shot"


def pick_mode(now: datetime, forced: str = "") -> str:
    """Tuesday is the pre-waiver check-up, Sunday is game day, anything else is a general outlook."""
    if forced in MODES:
        return forced
    return {1: "checkup", 6: "gameday"}.get(now.weekday(), "midweek")


class Ctx:
    def __init__(self, data: dict, slate: dict, sigma: dict):
        self.slate = slate or {}
        self.bye = set(self.slate.get("bye", ()))
        self.sigma = {**SIGMA_FALLBACK, **(sigma or {})}
        teams: dict = {}
        for p in data.get("league_pool", []):
            if p.get("owner"):
                teams.setdefault(p["owner"], []).append(p)
        by, totals = {}, []
        for owner, ros in teams.items():
            lineup = optimizer.optimize(ros).get("lineup") or []
            tot = 0.0
            for e in lineup:
                pl = e.get("player")
                if pl:
                    x = expect.if_plays(pl) * self.p_play(pl)
                    by.setdefault(pl["position"], []).append(x)
                    tot += x
            if lineup:
                totals.append(tot)
        self.bench = {pos: sum(xs) / len(xs) for pos, xs in by.items() if xs}
        self.league_avg = sum(totals) / len(totals) if totals else 0.0

    def p_play(self, p: dict) -> float:
        if _team(p.get("team")) in self.bye:
            return 0.0
        return expect.p_play(p)

    def sd(self, pos: str) -> float:
        return self.sigma.get(pos, 7.5)


_momentum = expect.momentum


def _story(p: dict, pp: float, mom: float):
    """(last-week line, baseline line, signals, trend) for a player card."""
    u = p.get("usage") or {}
    last = u.get("last") or {}
    pos = p.get("position")
    sigs, lastline, avgline = [], "", ""
    snap = last.get("snap_pct")
    if last:
        sn = f", {_pct(snap)} snaps" if snap is not None else ""
        if pos == "QB":
            lastline = f"Wk {last['week']}: {last['attempts']:.0f} att, {last['pts']:.1f} pts"
        elif pos == "RB":
            lastline = (f"Wk {last['week']}: {last['carries']:.0f} car, {last['targets']:.0f} tgt "
                        f"({last['receptions']:.0f} rec){sn}, {last['pts']:.1f} pts")
        else:
            lastline = (f"Wk {last['week']}: {last['targets']:.0f} tgt ({_pct(last['tshare'])} share), "
                        f"{last['receptions']:.0f} rec{sn}, {last['pts']:.1f} pts")
    if u.get("games"):
        sn = f", {_pct(u['snap_pct'])} snaps" if u.get("snap_pct") is not None else ""
        if pos == "QB":
            avgline = f"{u.get('qb_att_pg', 0):.0f} team att/g"
        elif pos == "RB":
            avgline = f"Last {min(u['games'], 4)} games: {u['carries_pg']:.1f} car/g, {u['targets_pg']:.1f} tgt/g{sn}"
        else:
            avgline = f"Last {min(u['games'], 4)} games: {u['targets_pg']:.1f} tgt/g ({_pct(u['target_share'])} share){sn}"

    # usage signals
    if last and pos in ("WR", "TE") and u.get("games", 0) >= 3:
        d = last["tshare"] - u["target_share"]
        if abs(d) >= 0.05:
            sigs.append(("+" if d > 0 else "-",
                         f"Target share {_pct(last['tshare'])} last week vs {_pct(u['target_share'])} recent average "
                         f"({last['targets']:.0f} target{'' if round(last['targets']) == 1 else 's'}, "
                         f"{last['receptions']:.0f} catch{'' if round(last['receptions']) == 1 else 'es'})"))
    if last and pos == "RB" and u.get("games", 0) >= 3:
        a, b = last["carries"] + last["targets"], u["carries_pg"] + u["targets_pg"]
        if abs(a - b) >= 3:
            sigs.append(("+" if a > b else "-", f"{a:.0f} touches last week vs {b:.1f} recent average"))
    tr = u.get("trend")
    if tr is not None and abs(tr) >= 10:
        sigs.append(("+" if tr > 0 else "-", f"Snap share {'up' if tr > 0 else 'down'} {abs(tr)} points over his last 2 games"))
    if u.get("snap_pct") is not None and pos in ("RB", "WR", "TE"):
        if u["snap_pct"] >= 0.75:
            sigs.append(("+", f"Full-time role ({_pct(u['snap_pct'])} of snaps)"))
        elif u["snap_pct"] < 0.5:
            sigs.append(("-", f"Part-time role ({_pct(u['snap_pct'])} of snaps)"))
    if p.get("boost"):
        g = p.get("boost_gain") or {}
        sigs.append(("+", f"Role boost +{p['boost']} pts (about {g.get('carries', 0)} more carries, "
                          f"{g.get('targets', 0)} more targets): {p.get('boost_why', '')}"))
    if p.get("if_out"):
        sigs.append(("i", f"If {p.get('if_out_why', '')} is ruled out: another +{p['if_out']} pts"))
    # health
    if pp == 0 and _num(p.get("projected_espn")) == 0:
        sigs.append(("-", "No game this week or not expected to play"))
    elif 0 < pp < 1:
        sigs.append(("-", f"{_status(p).replace('_', ' ').title()}: about {_pct(pp)} chance to play"))
    elif pp == 0:
        sigs.append(("-", f"{_status(p).replace('_', ' ').title() or 'Out'}: not expected to play"))
    if p.get("qb_note"):
        sigs.append(("-", f"QB situation: {p['qb_note']}"))
    n = p.get("news") or p.get("boost_news")
    if n and n.get("tag") in ("role", "injury"):
        sigs.append(("i", f"News: {n['headline']}"))

    snaps = tr or 0
    up = mom >= 0.4 or snaps >= 10
    down = mom <= -0.4 or snaps <= -10
    trend = "up" if up and not down else "down" if down and not up else "flat"
    return lastline, avgline, sigs, trend


def card(p: dict, ctx: Ctx) -> dict:
    pos = p.get("position")
    proj, pp = _num(p.get("projected")), ctx.p_play(p)
    mom = _momentum(p) if proj > 0 and pp > 0 else 0.0
    lastline, avgline, sigs, trend = _story(p, pp, mom)
    s = ctx.sd(pos)
    a = expect.if_plays(p)                         # projection when he plays (x LIMITED if tagged)
    mu = pp * a                                    # = expect.mean(p)
    var = pp * s * s + pp * (1 - pp) * a * a
    bench = ctx.bench.get(pos, proj)
    outlook = 0 if (proj <= 0 or pp == 0) else round(100 * _phi((mu - bench) / math.sqrt(max(var, 1e-6))))
    if proj <= 0 or pp == 0:
        label = "Not playing"
    else:
        label = "Strong" if outlook >= 70 else "Solid" if outlook >= 50 else "Shaky" if outlook >= 35 else "Weak"
    return {"name": p["name"], "position": pos, "team": p.get("team"), "slot": p.get("slot", ""),
            "starting": bool(p.get("starting")), "proj_espn": p.get("projected_espn", p.get("projected")),
            "proj": proj, "mom": round(mom, 1), "expected": round(mu, 1), "bench": round(bench, 1),
            "p_play": pp, "outlook": outlook, "label": label, "trend": trend, "last": lastline, "avg": avgline,
            "signals": sigs, "news": p.get("news") or p.get("boost_news"), "role": (p.get("usage") or {}).get("text", ""),
            "sources": p.get("sources") or {}, "split": bool(p.get("split")), "usage_pts": p.get("usage_pts"),
            "boost": p.get("boost") or 0.0, "_a": a, "_mu": mu, "_var": var}


def _covered(c: dict, backup: dict, ctx: "Ctx") -> dict:
    """The card's lineup contribution when a bench backup steps in if he's inactive. His own
    outlook is unchanged; only the lineup mean and variance (a two-outcome mix) move."""
    if not backup:
        return c
    pp, a, sa = c["p_play"], c["_a"], ctx.sd(c["position"])
    b, sb = expect.mean(backup), ctx.sd(backup.get("position"))
    mu = pp * a + (1 - pp) * b
    var = pp * (sa * sa + a * a) + (1 - pp) * (sb * sb + b * b) - mu * mu
    return {**c, "backup": backup["name"], "backup_proj": round(b, 1), "expected": round(mu, 1), "_mu": mu, "_var": var}


def _lineup_cards(lineup: list, backups: dict, pool: dict, ctx: "Ctx") -> list:
    """Cards for a lineup's starters, each credited with his backup if he has one."""
    out = []
    for e in lineup:
        p = e.get("player")
        if p and p["name"] in pool:
            out.append(_covered(pool[p["name"]], backups.get(p["name"]), ctx))
    return out


def _totals(cards: list) -> tuple:
    return sum(c["_mu"] for c in cards), sum(c["_var"] for c in cards)


def _win(mine: tuple, opp: tuple) -> float:
    sd = math.sqrt(max(mine[1] + opp[1], 1e-6))
    return _phi((mine[0] - opp[0]) / sd)


def _days(starters: list, ctx: Ctx) -> list:
    groups: dict = {}
    for c in starters:
        day = ctx.slate.get("day", {}).get(_team(c["team"]), "Bye" if _team(c["team"]) in ctx.bye else "")
        if day:
            groups.setdefault(day, []).append(c)
    out = []
    for day in sorted(groups, key=lambda d: DAY_ORDER.index(d) if d in DAY_ORDER else 99):
        cs = groups[day]
        mu, var = _totals(cs)
        ref = sum(ctx.bench.get(c["position"], 0.0) for c in cs)
        score = 0 if day == "Bye" else round(100 * _phi((mu - ref) / math.sqrt(max(var, 1e-6))))
        out.append({"day": day, "n": len(cs), "expected": round(mu, 1), "vs_typical": round(mu - ref, 1), "score": score,
                    "names": [c["name"] for c in sorted(cs, key=lambda c: -c["_mu"])[:3]]})
    return out


def _contingency(roster: list, cards: dict, backups: dict, ctx: "Ctx") -> list:
    """For each starter who might not play: his backup, or the fact that he has none
    (nobody on the bench kicks off at or after his game)."""
    by_name = {p["name"]: p for p in roster}
    out = []
    for p in roster:
        c = cards.get(p["name"])
        if not p.get("starting") or not c or not (0 < c["p_play"] < 1) or p.get("locked"):
            continue
        bk = by_name.get(backups.get(p["name"], ""))
        out.append({"starter": p["name"], "status": _status(p).replace("_", " ").title(), "p_play": c["p_play"],
                    "day": ctx.slate.get("day", {}).get(_team(p.get("team")), ""),
                    "backup": bk["name"] if bk else "", "backup_proj": round(expect.mean(bk), 1) if bk else 0.0,
                    "starter_proj": round(c["proj"], 1)})
    return out


def build(data: dict, slate: dict, sigma: dict, mode: str, now: datetime) -> dict:
    roster = data.get("roster", [])
    if not roster:
        return {}
    ctx = Ctx(data, slate, sigma)
    cards = {p["name"]: card(p, ctx) for p in roster}

    # Your lineup as set, with a backup for any starter who might not play (both managers
    # are assumed to check inactives and swap when a later-kicking backup is on the bench).
    def as_set(r):
        return [{"slot": p.get("slot", ""), "player": p} for p in r if p.get("starting")]
    cur_lineup = as_set(roster)
    cur_bk = optimizer.evaluate(cur_lineup, roster)[1]
    starters = _lineup_cards(cur_lineup, cur_bk, cards, ctx)
    opp_r = data.get("opponent_roster", [])
    opp_lineup = as_set(opp_r)
    opp_cards = _lineup_cards(opp_lineup, optimizer.evaluate(opp_lineup, opp_r)[1],
                              {p["name"]: card(p, ctx) for p in opp_r}, ctx)

    mine, opp = _totals(starters), _totals(opp_cards)
    win = _win(mine, opp) if opp_cards else None

    opt = data.get("optimizer") or {}

    # --- actions ---------------------------------------------------------------
    actions = []
    for s in (opt.get("swaps") or []):
        if s["gain"] < 0.5:
            continue
        out_p, in_p = s.get("out"), s["in"]
        broken = bool(out_p) and (cards.get(out_p["name"], {}).get("p_play", 1) == 0 or _num(out_p.get("projected")) <= 0)
        actions.append({"kind": "fix" if broken else "swap", "gain": s["gain"], "in": in_p["name"],
                        "out": out_p["name"] if out_p else "", "title": f"Start {in_p['name']} over {out_p['name'] if out_p else 'an empty slot'}",
                        "detail": ("Starter is not expected to play. " if broken else "") + f"+{s['gain']} projected points."})

    base_total = optimizer.optimize(roster)["optimal_total"]
    picks = []
    for fa in ((data.get("waivers") or {}).get("adds") or [])[:10]:
        # Same number the waiver card shows: best lineup with the add AND the drop made.
        if "gain" in fa:
            gain = fa["gain"]
        else:
            gone = fa.get("drop")
            gain = round(optimizer.optimize([p for p in roster if p["name"] != gone] + [fa])["optimal_total"]
                         - base_total, 1)
        picks.append((gain, fa))
    picks.sort(key=lambda t: (-t[0], t[1].get("verdict") != "stash"))
    used_drops, used_pos = set(), set()
    for gain, fa in picks:
        if gain < 0.5 and not (fa.get("verdict") == "stash" and (fa.get("need") or fa.get("boost") or fa.get("hot"))):
            continue
        if fa.get("drop") and fa["drop"] in used_drops:      # one claim per roster spot
            continue
        if fa.get("verdict") in ("fill", "stream"):
            if fa.get("position") in used_pos:
                continue
            used_pos.add(fa.get("position"))
        used_drops.add(fa.get("drop"))
        bits = [fa.get("reason", "")]
        if fa.get("boost"):
            bits.append(f"Role boost +{fa['boost']}: {fa.get('boost_why', '')}")
        if fa.get("hot"):
            bits.append(f"{fa['hot']:,} adds in 48h")
        if fa.get("dropped_by"):
            bits.append(f"dropped by {fa['dropped_by']}")
        actions.append({"kind": "fix" if fa.get("verdict") == "fill" else "pickup", "_fa": fa, "gain": gain, "in": fa["name"], "out": fa.get("drop", ""), "verdict": fa.get("verdict", ""),
                        "position": fa.get("position"), "team": fa.get("team"),
                        "title": f"Add {fa['name']}" + (f", drop {fa['drop']}" if fa.get("drop") else ""),
                        "detail": (f"+{gain} this week. " if gain >= 0.5 else "") + "; ".join(b for b in bits if b)})
        if sum(1 for a in actions if a.get("_fa") is not None) >= 3:
            break

    cont = _contingency(roster, cards, {k: v["name"] for k, v in cur_bk.items()}, ctx)
    for c in cont:
        if c["backup"]:
            detail = (f"About {_pct(c['p_play'])} to play. If he's inactive, start {c['backup']} "
                      f"({c['backup_proj']}); his game kicks off at the same time or later.")
        else:
            when = f" ({_DAY_NAME.get(c['day'], c['day'])})" if c["day"] else ""
            detail = (f"About {_pct(c['p_play'])} to play{when}. Nobody on your bench plays after his game, "
                      f"so if he's ruled out late the slot scores 0. The meter counts him at {_pct(c['p_play'])}.")
        actions.append({"kind": "watch", "gain": 0.0, "in": c["backup"], "out": c["starter"],
                        "title": f"{c['starter']} is {c['status'].lower()}", "detail": detail})

    order = {"fix": 0, "swap": 1, "pickup": 2, "watch": 3}
    actions.sort(key=lambda a: (order[a["kind"]], -a["gain"]))

    best = None
    if opt.get("lineup"):
        extra = [a["_fa"] for a in actions if a.get("_fa") is not None]
        gone = {fa.get("drop") for fa in extra if fa.get("drop")}
        opt2 = optimizer.optimize([p for p in roster if p["name"] not in gone] + extra) if extra else opt
        pool_cards = dict(cards)
        for fa in extra:
            pool_cards[fa["name"]] = card(fa, ctx)
        roster2 = [p for p in roster if p["name"] not in gone] + extra
        best_cards = _lineup_cards(opt2["lineup"], optimizer.evaluate(opt2["lineup"], roster2)[1], pool_cards, ctx)
        best = {"expected": round(_totals(best_cards)[0], 1), "win": _win(_totals(best_cards), opp) if opp_cards else None}

    # Questionable players the meter is weighing: starters counted at their play chance (or
    # covered by a backup), and benched ones who'd start if sure to play, with what that's worth.
    risks = [{"name": c["starter"], "status": c["status"], "p_play": c["p_play"], "day": c["day"],
              "backup": c["backup"]} for c in cont]
    alternatives = []
    if opt.get("lineup") and opp_cards:
        rec_names = {e["player"]["name"] for e in opt["lineup"] if e.get("player")}
        rec_cards = _lineup_cards(opt["lineup"], optimizer.evaluate(opt["lineup"], roster)[1], cards, ctx)
        rec_win = _win(_totals(rec_cards), opp)
        for alt in opt.get("alternatives") or []:
            u = alt["player"]
            if u.get("starting"):           # already covered by his risk line and the swap action
                continue
            names = {e["player"]["name"] for e in alt["lineup"] if e.get("player")}
            a_cards = _lineup_cards(alt["lineup"], optimizer.evaluate(alt["lineup"], roster)[1], cards, ctx)
            alternatives.append({"name": u["name"], "status": _status(u).replace("_", " ").title(),
                                 "p_play": ctx.p_play(u), "day": ctx.slate.get("day", {}).get(_team(u.get("team")), ""),
                                 "backup": (alt.get("backup") or {}).get("name", ""),
                                 "instead": sorted(rec_names - names), "win": _win(_totals(a_cards), opp),
                                 "rec_win": rec_win, "expected": round(_totals(a_cards)[0], 1)})

    title, sub = MODES.get(mode, MODES["midweek"])
    score = round(100 * win) if win is not None else None
    return {
        "mode": mode, "title": title, "sub": sub, "week": data.get("week"), "generated": now.strftime("%Y-%m-%d %H:%M"),
        "score": score, "label": band(score) if score is not None else "",
        "mine": round(mine[0], 1), "opp": round(opp[0], 1) if opp_cards else None,
        "margin": round(mine[0] - opp[0], 1) if opp_cards else None,
        "spread": round(math.sqrt(mine[1] + opp[1]), 1),
        "optimal": best, "days": _days(starters, ctx), "risks": risks, "alternatives": alternatives,
        "actions": [{k: v for k, v in a.items() if k != "_fa"} for a in actions],
        "cards": [{k: v for k, v in cards[p["name"]].items() if not k.startswith("_")} for p in roster],
        "benchmarks": {k: round(v, 1) for k, v in ctx.bench.items()}, "league_avg": round(ctx.league_avg, 1),
    }


_DAY_NAME = {"Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday", "Mon": "Monday night",
             "Tue": "Tuesday", "Wed": "Wednesday"}
_ARROW = {"up": "rising", "down": "falling", "flat": "steady"}
_SIGN = {"+": "+", "-": "-", "i": "*"}


def risk_lines(a: dict) -> list:
    """(label, text) pairs saying how the meter counts players who might not play."""
    out = []
    for r in a.get("risks") or []:
        day = _DAY_NAME.get(r["day"], r["day"])
        if r["backup"]:
            out.append((r["name"], f"{r['status']}: counted at {_pct(r['p_play'])} to play, with "
                                   f"{r['backup']} covering if he's inactive."))
        else:
            out.append((r["name"], f"{r['status']}{', ' + day if day else ''}: counted at {_pct(r['p_play'])} to play. "
                                   f"Nobody on your bench plays after his game, so a late scratch scores 0."))
    for x in a.get("alternatives") or []:
        day = _DAY_NAME.get(x["day"], x["day"])
        over = " and ".join(x["instead"]) or "your current starter"
        why = (f"{x['backup']} would cover him if he's inactive." if x["backup"] else
               f"Nobody on your bench plays after his {day + ' game' if day else 'game'}, "
               f"so he counts at {_pct(x['p_play'])}.")
        out.append((f"Starting {x['name']} over {over}",
                    f"{round(100 * x['win'])}% to win instead of {round(100 * x['rec_win'])}%. "
                    f"He's {x['status'].lower()}. {why}"))
    return out


def markdown(a: dict, data: dict) -> str:
    """The assessment as plain markdown: for you, and for the Claude routine that writes the narrative."""
    if not a:
        return ""
    team = data.get("team_name", "my team")
    out = [f"# {a['title']} - Week {a['week']} - {team}", f"Generated {a['generated']} Central. {a['sub']}.", ""]
    opp_name = data.get("opponent_name") or "this week's opponent"
    if a.get("score") is not None:
        out += [f"## Confidence: {a['score']}/100 ({a['label']})",
                f"Chance my lineup beats {opp_name}: {a['score']}%. "
                f"Projected {a['mine']} vs {a['opp']} (margin {a['margin']:+}, typical swing +/-{a['spread']})."]
        if a.get("optimal") and a["optimal"].get("win") is not None:
            out.append(f"With the recommended lineup changes: {a['optimal']['expected']} projected, "
                       f"{round(100 * a['optimal']['win'])}% to win.")
        for label, text in risk_lines(a):
            out.append(f"- Injury risk, {label}: {text}")
    out.append("")
    if a["actions"]:
        out.append("## Do this")
        for i, x in enumerate(a["actions"], 1):
            out.append(f"{i}. [{x['kind'].upper()}] {x['title']}. {x['detail']}")
        out.append("")
    else:
        out += ["## Do this", "Nothing. Lineup is optimal and no waiver pickup improves it.", ""]
    if a["days"]:
        out.append("## By day (chance this day's starters beat a typical lineup's output)")
        for d in a["days"]:
            if d["day"] == "Bye":
                out.append(f"- Bye: {d['n']} starter(s) have no game ({', '.join(d['names'])})")
            else:
                out.append(f"- {d['day']}: {d['n']} starter(s), {d['expected']} projected, {d['vs_typical']:+} vs typical, "
                           f"{d['score']}% ({', '.join(d['names'])})")
        out.append("")
    out += ["## Every player on my roster",
            "Outlook = chance the player outscores the average starter at his position in this league this week (0 if not playing). "
            "Projection = average of ESPN and Sleeper (RotoWire), both in this league's scoring, plus a small role boost when a "
            "teammate is out. Expected = projection x chance to play (x 0.85 if he's tagged, since tagged players who play "
            "score less).", ""]
    for c in sorted(a["cards"], key=lambda c: (not c["starting"], -c["outlook"])):
        where = f"starting at {c['slot']}" if c["starting"] else ("IR" if c["slot"] == "IR" else "bench")
        src = c.get("sources") or {}
        espn = (" / ".join(f"{k} {v:.1f}" for k, v in src.items()) + (" (sources split)" if c.get("split") else "") + ", "
                if len(src) >= 2 else f"ESPN {c['proj_espn']:.1f}, " if isinstance(c["proj_espn"], (int, float)) else "")
        if c.get("usage_pts") is not None:
            espn += f"usage {c['usage_pts']:.1f}/g, "
        out.append(f"### {c['name']} ({c['position']}, {c['team']}) - {where} - outlook {c['outlook']} ({c['label']}, {_ARROW[c['trend']]})")
        out.append(f"- {espn}adjusted {c['proj']:.1f}, expected {c['expected']:.1f} vs typical {c['position']} starter {c['bench']:.1f}")
        if c["role"]:
            out.append(f"- Role: {c['role']}")
        if c["last"]:
            out.append(f"- {c['last']}")
        if c["avg"]:
            out.append(f"- {c['avg']}")
        for sign, text in c["signals"]:
            out.append(f"- ({_SIGN[sign]}) {text}")
        n = c.get("news")
        if n and n.get("link"):
            out.append(f"- Link: {n['link']}")
        out.append("")
    out += ["---", "Caveat: projections are the average of ESPN's and Sleeper's (RotoWire), and the confidence is arithmetic on "
                   "them. Matchup strength is only what those projections already include."]
    return "\n".join(out)
