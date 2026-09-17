"""Writes the plain-text brief you hand to Claude.

The dashboard is for glancing. This file is for asking questions -- it's
dense, unstyled, and structured so a model can reason over it without
you re-explaining your league every time.
"""

from __future__ import annotations


def _line(p: dict) -> str:
    proj = p.get("projected")
    proj = f"{proj:.1f}" if isinstance(proj, (int, float)) else "n/a"
    inj = p.get("injury", "ACTIVE")
    inj = "" if inj in ("ACTIVE", "NORMAL", "") else f" [{inj}]"
    opp = f" vs {p['opponent']}" if p.get("opponent") else " (no game)"
    own = p.get("pct_started")
    own = f", started in {own}% of leagues" if isinstance(own, (int, float)) and own >= 0 else ""
    return (f"- {p.get('name')} ({p.get('position')}, {p.get('team')}){opp}"
            f" - projected {proj}{inj}{own}")


def build(data: dict) -> str:
    roster = data.get("roster", [])
    starters = [p for p in roster if p.get("starting")]
    bench = [p for p in roster if not p.get("starting")]

    out = [
        f"# Fantasy brief - Week {data.get('week')}",
        f"Generated {data.get('generated')}",
        "",
        f"League: {data.get('league_name') or 'n/a'} ({data.get('scoring', 'ppr')} scoring)",
        f"Team: {data.get('team_name')} ({data.get('record','')})",
    ]
    if data.get("opponent_name"):
        out.append(f"Opponent this week: {data['opponent_name']}")

    out += ["", "## My starters"] + [_line(p) for p in starters]
    out += ["", "## My bench"] + [_line(p) for p in bench]

    if data.get("opponent_roster"):
        opp_start = [p for p in data["opponent_roster"] if p.get("starting")]
        out += ["", "## Opponent's starters"] + [_line(p) for p in opp_start]

    fa = data.get("free_agents", [])
    if fa:
        ranked = sorted(
            fa,
            key=lambda p: p.get("projected") if isinstance(p.get("projected"), (int, float)) else -1,
            reverse=True,
        )[:25]
        out += ["", "## Top available free agents"] + [_line(p) for p in ranked]

    adds = data.get("trending_adds", [])
    if adds:
        out += ["", "## Most added across all leagues (last 48h)"]
        out += [f"- {a['name']} ({a['position']}, {a['team']}) - {a['count']:,} adds"
                for a in adds]

    drops = data.get("trending_drops", [])
    if drops:
        out += ["", "## Most dropped across all leagues (last 48h)"]
        out += [f"- {d['name']} ({d['position']}, {d['team']}) - {d['count']:,} drops"
                for d in drops]

    inj = data.get("roster_injuries", {})
    if inj:
        out += ["", "## Injury detail on my players"]
        for name, d in inj.items():
            note = f" - {d['notes']}" if d.get("notes") else ""
            out.append(f"- {name}: {d['status']} ({d.get('body_part') or 'unspecified'}){note}")

    opt = data.get("optimizer", {})
    if opt.get("lineup"):
        out += ["", "## Lineup optimizer"]
        if opt["swaps"]:
            out.append(f"Recommended swaps add +{opt['gain']} projected ({opt['current_total']} -> {opt['optimal_total']}):")
            for s in opt["swaps"]:
                o = s["out"]["name"] if s["out"] else "empty slot"
                out.append(f"- Start {s['in']['name']} over {o} (+{s['gain']})")
        else:
            out.append(f"Current lineup is already optimal at {opt['optimal_total']} projected.")

    rk = data.get("rankings", {})
    if rk:
        out += ["", "## Weekly position rankings (top 12 each, league pool)",
                "Score = 65% this-week projection + 35% 2025 PPR points/game. * = on my roster."]
        for pos in ("QB", "RB", "WR", "TE", "D/ST", "K"):
            out.append(f"\n{pos}:")
            for r in rk.get(pos, [])[:12]:
                who = "*" if r.get("mine") else (r.get("owner") or "FA")
                out.append(f"  {r['rank']}. {r['name']} ({r['team']}) proj {r['proj']}, 2025 avg {r['ppg_2025']} [{who}]")

    tr = data.get("trades", {})
    if tr:
        out += ["", "## Trade analysis"]
        if tr["needs"]:
            out.append("Positions where my best starter is below league median:")
            out += [f"- {n['position']}: mine {n['best']} vs median {n['median']}" for n in tr["needs"]]
        if tr["chips"]:
            out.append("Bench players of mine who'd start elsewhere (trade chips):")
            out += [f"- {c['name']} ({c['position']}, {c['team']}) score {c['score']}" for c in tr["chips"]]
        if tr["targets"]:
            out.append("Targets on teams with surplus at my need positions:")
            out += [f"- {t['name']} ({t['position']}, {t['team']}) owned by {t['owner']} - {t['reason']}" for t in tr["targets"]]
        if tr["buy_low"]:
            out.append("Buy-low candidates (proven, soft projection):")
            out += [f"- {b['name']} ({b['position']}, {b['team']}) owned by {b['owner']} - {b['reason']}" for b in tr["buy_low"]]

    news = data.get("news", [])
    if news:
        out += ["", "## Headlines"]
        out += [f"- {n['headline']}: {n.get('description','')}" for n in news[:12]]

    out += [
        "",
        "---",
        "Questions worth asking: who to start at flex, whether any bench player "
        "has passed a starter, which free agent is worth a waiver claim, and "
        "who on my roster is droppable.",
    ]
    return "\n".join(out)
