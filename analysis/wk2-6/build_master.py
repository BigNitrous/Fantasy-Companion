"""Leak-free feature table for the prediction review.

One row per (week, rostered skill player who played). Every feature uses only
information from weeks BEFORE that week, except the columns marked HINDSIGHT.
"""
import csv, io, json, math, os, statistics as st, sys
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from collector import usage as U
B = os.environ.get("BT_DIR", os.path.dirname(os.path.abspath(__file__)))  # needs week17/espn_players.csv, sleeper_proj.csv, games_2026.csv

def f(x, d=None):
    try:
        v = float(x); return v if math.isfinite(v) else d
    except (TypeError, ValueError):
        return d

# ---- sources ----------------------------------------------------------------
esp = list(csv.DictReader(open(f"{B}/week17/espn_players.csv")))
slp = list(csv.DictReader(open(f"{B}/sleeper_proj.csv")))
games = list(csv.DictReader(open(f"{B}/games_2026.csv")))
stats = U._rows("stats_player", "stats_player_week_2026")
snaps = U._rows("snap_counts", "snap_counts_2026")
teamst = U._rows("stats_team", "stats_team_week_2026")

# ---- per player-week table from nflverse ------------------------------------
pw = {}                                    # (norm, team) -> {week: dict}
for r in stats:
    if r["season_type"] != "REG" or r["position"] not in ("QB", "RB", "WR", "TE"):
        continue
    k = (U.norm(r["player_display_name"]), U.team(r["team"]))
    pw.setdefault(k, {})[int(r["week"])] = {
        "pos": r["position"], "pts": f(r["fantasy_points_ppr"], 0.0), "tgt": f(r["targets"], 0.0),
        "tsh": f(r["target_share"], 0.0), "ays": f(r["air_yards_share"], 0.0), "wopr": f(r["wopr"], 0.0),
        "car": f(r["carries"], 0.0), "att": f(r["attempts"], 0.0), "opp": U.team(r["opponent_team"]),
        "rec": f(r["receptions"], 0.0)}
for r in snaps:
    if r.get("game_type", "REG") != "REG" or r["position"] not in ("QB", "RB", "WR", "TE", "FB"):
        continue
    k = (U.norm(r["player"]), U.team(r["team"]))
    d = pw.setdefault(k, {}).setdefault(int(r["week"]), {"pos": r["position"], "pts": 0.0, "tgt": 0.0, "tsh": 0.0, "ays": 0.0,
                                                          "wopr": 0.0, "car": 0.0, "att": 0.0, "opp": U.team(r["opponent"]), "rec": 0.0})
    d["snap"] = f(r["offense_pct"]); d["snaps"] = f(r["offense_snaps"], 0.0)

tw = defaultdict(dict)                     # team -> week -> {att, car}
for r in teamst:
    if r.get("season_type", "REG") == "REG":
        tw[U.team(r["team"])][int(r["week"])] = {"att": f(r["attempts"], 0.0), "car": f(r["carries"], 0.0)}

# ---- defense vs position (points allowed per game by week) -------------------
allowed = defaultdict(lambda: defaultdict(float))   # (defteam, pos) -> week -> pts
for (k, t), wk in pw.items():
    for w, d in wk.items():
        if d["pos"] in ("QB", "RB", "WR", "TE") and d.get("opp"):
            allowed[(d["opp"], d["pos"])][w] += d["pts"]

# ---- Vegas ---------------------------------------------------------------------
vegas = {}
for g in games:
    sp, tot = f(g["spread_line"]), f(g["total_line"])
    if sp is None or tot is None:
        continue
    w = int(g["week"]); h, a = U.team(g["home_team"]), U.team(g["away_team"])
    vegas[(h, w)] = {"home": 1, "tot": tot, "spread": sp, "imp": tot / 2 + sp / 2, "opp_imp": tot / 2 - sp / 2, "opp": a}
    vegas[(a, w)] = {"home": 0, "tot": tot, "spread": -sp, "imp": tot / 2 - sp / 2, "opp_imp": tot / 2 + sp / 2, "opp": h}

# ---- Sleeper projections --------------------------------------------------------
sp_proj = {}
for r in slp:
    if r.get("company") not in ("rotowire", ""):
        pass
    sp_proj[(int(r["week"]), U.norm(r["name"]), r["position"])] = f(r["pts_ppr"])

def prior(k, w):
    wk = pw.get(k, {})
    return {x: d for x, d in wk.items() if x < w and (d.get("snaps", 0) > 0 or d["pts"] != 0 or d["tgt"] or d["car"] or d["att"])}

def mean(xs): return sum(xs) / len(xs) if xs else None

out = []
for r in esp:
    w = int(r["week"]); pos = r["position"]
    if pos not in ("QB", "RB", "WR", "TE") or r["slot"] == "IR" or int(r["bye"]) or w < 2:
        continue
    proj, act = f(r["projected"]), f(r["actual"])
    if proj is None or act is None or f(r["game_played"], 0) <= 0:
        continue
    team = U.team(r["pro_team"]); k = (U.norm(r["name"]), team)
    if k not in pw:                              # nflverse name/team mismatch: keep the row, features blank
        cand = [kk for kk in pw if kk[0] == k[0]]
        k = cand[0] if len(cand) == 1 else k
    p = prior(k, w)
    ws = sorted(p)
    pts = [p[x]["pts"] for x in ws]
    l3 = ws[-3:]; l2 = ws[-2:]
    snp = [p[x]["snap"] for x in ws if p[x].get("snap") is not None]
    snp2 = [p[x]["snap"] for x in l2 if p[x].get("snap") is not None]
    ts_all = [p[x]["tsh"] for x in ws]; ts2 = [p[x]["tsh"] for x in l2]
    car_sh = []
    for x in ws:
        tc = tw.get(team, {}).get(x, {}).get("car", 0)
        car_sh.append(p[x]["car"] / tc if tc else 0.0)
    v = vegas.get((team, w), {})
    # matchup: opponent defense points allowed to this position per game, prior weeks, vs league average
    opp = v.get("opp") or U.team(r["pro_opponent"])
    def allow(defteam):
        d = allowed.get((defteam, pos), {}); xs = [d[x] for x in d if x < w]
        return mean(xs)
    league_avg = mean([a for a in (allow(t) for t in {t for (t, ps) in allowed if ps == pos}) if a is not None])
    ap = allow(opp) if opp else None
    dvp = (ap / league_avg - 1) if (ap is not None and league_avg) else None
    # HINDSIGHT: teammates who played last week but not this week (inactive/injured) and the usage they leave
    vac_t = vac_c = 0.0
    for (nn, tt), wk in pw.items():
        if tt != team or nn == k[0] or (w - 1) not in wk or w in wk and (wk[w].get("snaps", 0) or wk[w]["pts"]):
            continue
        pr = {x: d for x, d in wk.items() if x < w}
        vac_t += mean([d["tsh"] for d in pr.values()]) or 0.0
        tcs = [d["car"] / tw[team][x]["car"] for x, d in pr.items() if tw.get(team, {}).get(x, {}).get("car")]
        vac_c += mean(tcs) or 0.0
    sproj = sp_proj.get((w, U.norm(r["name"]), pos))
    blend = (proj + sproj) / 2 if sproj is not None else proj
    out.append({
        "week": w, "name": r["name"], "pos": pos, "team": team, "slot": r["slot"], "is_bench": int(r["slot"] == "BE"),
        "is_mine": r["is_mine"], "inj": r["injury_status"],
        "espn_proj": proj, "sleeper_proj": sproj, "blend": round(blend, 3), "actual": act,
        "resid": round(act - blend, 3), "boom8": int(act - blend >= 8), "act20": int(act >= 20), "act15": int(act >= 15),
        "g_prior": len(ws), "ppg_all": mean(pts), "ppg_l3": mean([p[x]["pts"] for x in l3]),
        "sd_pts": (st.pstdev(pts) if len(pts) >= 2 else None), "max_pts": max(pts) if pts else None,
        "last_pts": p[ws[-1]]["pts"] if ws and ws[-1] == w - 1 else None,
        "tsh_all": mean(ts_all), "tsh_l2": mean(ts2), "ays_all": mean([p[x]["ays"] for x in ws]), "wopr_all": mean([p[x]["wopr"] for x in ws]),
        "snap_all": mean(snp), "snap_l2": mean(snp2), "tgt_pg": mean([p[x]["tgt"] for x in ws]), "car_pg": mean([p[x]["car"] for x in ws]),
        "carsh_all": mean(car_sh), "team_att_pg": mean([tw[team][x]["att"] for x in sorted(tw.get(team, {})) if x < w][-4:]),
        "vegas_total": v.get("tot"), "team_spread": v.get("spread"), "implied_team": v.get("imp"), "implied_opp": v.get("opp_imp"), "home": v.get("home"),
        "dvp": dvp, "vac_tgt_HINDSIGHT": round(vac_t, 4), "vac_car_HINDSIGHT": round(vac_c, 4)})

fields = list(out[0].keys())
w = csv.DictWriter(open(f"{B}/master.csv", "w", newline=""), fieldnames=fields); w.writeheader(); w.writerows(out)
print("wrote master.csv rows:", len(out), "| weeks:", sorted({r['week'] for r in out}))
sp = [r for r in out if r["sleeper_proj"] is not None]
print("rows with Sleeper proj:", len(sp), "| bench rows:", sum(r["is_bench"] for r in out))
mae = lambda rs, key: mean([abs(r["actual"] - r[key]) for r in rs])
print("MAE ESPN:", round(mae(out, "espn_proj"), 3), "| MAE blend:", round(mae(out, "blend"), 3), "| MAE Sleeper (where present):", round(mae(sp, "sleeper_proj"), 3))
print("missing feature share:", {c: round(sum(1 for r in out if r[c] is None) / len(out), 2) for c in ("ppg_all", "tsh_all", "snap_all", "implied_team", "dvp", "sleeper_proj")})
