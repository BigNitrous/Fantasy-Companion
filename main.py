#!/usr/bin/env python3
"""Collects everything and writes site/index.html plus site/brief.md.

Runs with no arguments. If ESPN isn't configured yet it still produces a
useful page from the free public sources, so you can deploy before you've
sorted out cookies.
"""

import os
import sys
import traceback
from datetime import datetime

from collector import (config, sleeper_source, news_source, render, brief, history, optimizer, rankings, trades,
                       waivers, usage, roles, schedule_source, assess, sources)


def _now_ct() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        return datetime.now()


def _week_finished(week: int, us: dict) -> bool:
    """True when every game of `week` is final. ESPN's scoreboard decides. Don't use the
    latest week in the nflverse stats: Thursday night's game puts the week in the stats
    after one game, and the build then assessed next week all weekend. If the scoreboard
    can't be reached, nflverse must show nearly every team (26+) played that week."""
    sl = schedule_source.slate(week, config.SEASON)
    if sl:
        return set(sl["day"]) <= sl["final"]
    if us and not us["stale"]:
        played = sum(1 for t in us["teams"].values() if week in t["weeks"])
        return played >= 26
    return False


def main() -> int:
    week = sleeper_source.current_week()
    print(f"NFL week {week}")

    print("Loading usage (nflverse)...")
    us = usage.load(config.SEASON)
    if us:
        print(f"  {len(us['players'])} players, {len(us['teams'])} teams, through week {us['through']}"
              + (" (last season's data)" if us["stale"] else ""))
    else:
        print("  usage data unavailable; role and usage analysis skipped")

    # Sleeper keeps reporting the week that just ended until Tuesday. Once every game of
    # `week` is final, the week you're deciding for is the next one.
    if week < 18 and _week_finished(week, us):
        print(f"  week {week} is complete, assessing week {week + 1}")
        week += 1

    data = {
        "week": week,
        "scoring": config.SCORING,
        "generated": render.timestamp(),
        "roster": [],
        "team_name": "",
        "record": "",
    }

    data["espn"] = {"ok": False, "reason": ""}
    if config.is_configured():
        from collector import espn_source
        print("Fetching ESPN...")
        try:
            data.update(espn_source.fetch(week))
            optimizer.set_league_slots((data.get("league") or {}).get("slots"))
            notes = [n for n in (data.get("team_note", ""),
                                 "The ESPN_S2 secret is pasted twice back to back; the first copy was used. Update the secret in GitHub so this keeps working." if config.ESPN_S2_DOUBLED else "") if n]
            data["espn"] = {"ok": True, "reason": " ".join(notes)}
            print(f"  OK: {len(data['roster'])} players on {data['team_name']}")
            for n in notes:
                print(f"  NOTE: {n}")
        except espn_source.ESPNSetupError as e:
            data["espn"]["reason"] = str(e)
            print(f"  ESPN NOT CONNECTED: {e}")
        except Exception as e:
            data["espn"]["reason"] = f"Unexpected {type(e).__name__}: {e}"
            print(f"  ESPN NOT CONNECTED (bug, not config): {type(e).__name__}: {e}")
            traceback.print_exc(limit=3)
    else:
        data["espn"]["reason"] = "LEAGUE_ID secret is not set."
        print("  LEAGUE_ID not set. Skipping ESPN.")

    print("Fetching Sleeper...")
    data["trending_adds"] = sleeper_source.trending("add", hours=48, limit=25)
    data["trending_drops"] = sleeper_source.trending("drop", hours=48, limit=15)
    if data["roster"]:
        names = [p["name"] for p in data["roster"]]
        data["roster_injuries"] = sleeper_source.injuries_for(names)
        print(f"  {len(data['roster_injuries'])} injury notes on your players")

    print("Fetching news...")
    data["news"] = news_source.headlines(limit=50)

    slate = schedule_source.slate(week, config.SEASON) if data["roster"] else {}
    if slate:
        # ESPN's reloaded rosters carry no opponent for the target week; the slate has every matchup.
        for key in ("roster", "opponent_roster", "free_agents", "league_pool"):
            for pl in data.get(key, []):
                if not pl.get("opponent") and pl.get("position") != "D/ST":
                    pl["opponent"] = slate["opp"].get(pl.get("team", ""), "")
                elif not pl.get("opponent"):
                    pl["opponent"] = slate["opp"].get(pl.get("team", ""), "")
                # A player whose game has kicked off can't be moved, added or dropped for this week.
                tm = pl.get("team", "")
                pl["locked"] = tm in slate.get("started", ())
                pl["kickoff_ts"] = slate.get("ts", {}).get(tm)
                if tm in slate.get("bye", ()):
                    pl["bye"] = True

    if data["roster"]:
        # Second opinions: Sleeper's (RotoWire's) projection scored with this league's rules, averaged with ESPN's.
        lists = [data.get(k, []) for k in ("roster", "opponent_roster", "free_agents", "league_pool")]
        sl = sources.sleeper_week(config.SEASON, week, (data.get("league") or {}).get("scoring"))
        up = sources.usage_points(config.SEASON, week)
        n = sources.apply(lists, sl, up, sources.Index(sleeper_source.all_players()))
        print(f"  sources: Sleeper projections for {n} player(s), usage numbers for {len(up)}")

    if data["roster"] and us:
        rl = roles.Roles(us, sleeper_source.all_players(), data["news"])
        n = rl.annotate(data["roster"]) + rl.annotate(data.get("opponent_roster", [])) \
            + rl.annotate(data.get("free_agents", [])) + rl.annotate(data.get("league_pool", []))
        data["role_watch"] = roles.watch(data["roster"], data.get("free_agents", []))
        print(f"  roles: {n} projection(s) adjusted for vacated opportunity, {len(data['role_watch'])} on the watch list")

    # Analysis layers. All degrade to empty if ESPN isn't available.
    print("Loading 2025 season history...")
    hist = history.load(config.SEASON - 1)
    print(f"  {len(hist)} players with last-season data")

    if data["roster"]:
        data["optimizer"] = optimizer.optimize(data["roster"])
        print(f"  optimizer: {len(data['optimizer']['swaps'])} swap(s), +{data['optimizer']['gain']}")

        pool = data.get("league_pool", [])
        my_names = {p["name"] for p in data["roster"]}
        rk = rankings.build(pool, hist, my_names, top_n=30)
        data["rankings"] = rk
        # Enrich the pool with scores so trades can use them.
        scored = {}
        for pos_list in rankings.build(pool, hist, my_names, top_n=10_000).values():
            for r in pos_list:
                scored[r["name"]] = r
        pool_scored = [scored.get(p["name"], {**p, "score": 0.0, "proj": 0.0, "ppg_2025": 0.0}) for p in pool]
        data["trades"] = trades.build(pool_scored, data["team_name"], optimizer.slot_structure(data["roster"]))
        print(f"  rankings built, {len(data['trades']['targets'])} trade target(s)")

        data["waivers"] = waivers.build(
            data.get("free_agents", []), data["roster"], hist, data.get("trending_adds", []),
            data.get("activity", []), data.get("league", {}), data["trades"]["needs"], data["team_name"])
        w = data["waivers"]
        print(f"  waivers: {len(w['adds'])} add candidate(s), {len(w['hot'])} hot & unclaimed, {len(w['just_dropped'])} recently dropped")

    if data["roster"]:
        now = _now_ct()
        mode = assess.pick_mode(now, os.environ.get("ASSESS_MODE", "").strip().lower())
        data["assessment"] = assess.build(data, slate, (us or {}).get("sigma"), mode, now)
        a = data["assessment"]
        if a and a.get("score") is not None:
            print(f"  assessment ({a['title']}): {a['score']} confidence ({a['label']}), "
                  f"{a['mine']} vs {a['opp']}, {len(a['actions'])} action(s)")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    html_path = os.path.join(config.OUTPUT_DIR, "index.html")
    brief_path = os.path.join(config.OUTPUT_DIR, "brief.md")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render.build(data))
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(brief.build(data))
    if data.get("assessment"):
        with open(os.path.join(config.OUTPUT_DIR, "assessment.md"), "w", encoding="utf-8") as f:
            f.write(assess.markdown(data["assessment"], data))

    print(f"Wrote {html_path} and {brief_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
