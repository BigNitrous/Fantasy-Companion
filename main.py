#!/usr/bin/env python3
"""Collects everything and writes site/index.html plus site/brief.md.

Runs with no arguments. If ESPN isn't configured yet it still produces a
useful page from the free public sources, so you can deploy before you've
sorted out cookies.
"""

import os
import sys
import traceback

from collector import config, sleeper_source, news_source, render, brief, history, optimizer, rankings, trades, waivers


def main() -> int:
    week = sleeper_source.current_week()
    print(f"NFL week {week}")

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

    print("Fetching news...")
    data["news"] = news_source.headlines(limit=15)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    html_path = os.path.join(config.OUTPUT_DIR, "index.html")
    brief_path = os.path.join(config.OUTPUT_DIR, "brief.md")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render.build(data))
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(brief.build(data))

    print(f"Wrote {html_path} and {brief_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
