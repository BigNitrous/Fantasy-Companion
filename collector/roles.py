"""Role changes that matter for start/sit.

Usage (usage.py) says who gets the ball. This module asks what changes this
week: a teammate who is out leaves carries and targets on the table, and the
healthy players at his position pick them up. The next man up is guaranteed
a floor even if he hasn't touched the ball yet (the classic handcuff).

The points are an estimate, and deliberately small: ESPN's and Sleeper's
projections already react to injury news, so only ADJ_WEIGHT of the
usage-implied gain is added, capped at CAP points. Every adjustment is shown
next to the source numbers so you can overrule it.

Headlines from ESPN are matched to players by name and attached as evidence.
"""

from __future__ import annotations
import re

from . import usage as U

ADJ_WEIGHT = 0.15     # share of the usage-implied gain added to the projection. Backtest (2026 wks 2-5):
                      # on top of the ESPN+Sleeper average only ~0.13 of it showed up (95% range -0.40 to 0.65),
                      # since both sources already react to injuries. Was 0.5.
CAP = 6.0             # most points a role change can add
MIN_BOOST = 0.3       # ignore anything smaller than this
MAX_DC, MAX_DT = 0.35, 0.15   # most carry / target share a teammate can inherit
FLOOR_CARRY, FLOOR_TGT = 0.06, 0.03   # guaranteed share for the next man up
SAME_POS = 1.6        # vacated targets lean toward the same position group
# (points per carry, points per target) in PPR
PTS = {"RB": (0.60, 1.5), "FB": (0.50, 1.2), "WR": (0.0, 1.7), "TE": (0.0, 1.6)}
OUT_INJ = {"out", "doubtful", "ir", "pup", "suspended", "dnr", "na"}
RUSHERS, CATCHERS = ("RB", "FB"), ("RB", "FB", "WR", "TE")

_ROLE = re.compile(r"\b(expected to|workload|touches|carries|targets?|snaps?|lead back|backfield|featured|"
                   r"bell.?cow|committee|take over|taking over|starting|starter|step(?:s|ping)? into|"
                   r"increased|role|usage|volume|primary|work as|RB1|RB2|WR1|WR2|TE1)\b", re.I)
_INJ = re.compile(r"\b(out|ruled out|miss(?:es)?|injur\w*|IR|questionable|doubtful|hamstring|ankle|knee|"
                  r"concussion|shoulder|groin|calf|return\w*|sidelined)\b", re.I)


def _pct(x) -> str:
    return f"{x * 100:.0f}%"


def _clean(s) -> str:
    return (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


class Roles:
    def __init__(self, us: dict, sleeper_players: dict, articles: list):
        self.us = us
        self.articles = [{"headline": _clean(a.get("headline")), "desc": _clean(a.get("description")),
                          "link": a.get("link", ""), "published": a.get("published", "")}
                         for a in (articles or [])]
        self._news = {}
        self._sl = {}                 # norm name -> [sleeper players]
        self._by_team = {}            # team -> [sleeper players]
        for p in (sleeper_players or {}).values():
            if p.get("position") in U.SKILL and p.get("team"):
                self._sl.setdefault(U.norm(p.get("full_name")), []).append(p)
                self._by_team.setdefault(U.team(p["team"]), []).append(p)
        self.plan = {}                # (key, team) -> {"dc", "dt", "who": [...]}
        self.cond = {}                # same, for players listed questionable
        self.ranks = {}               # (key, team) -> "WR2"
        self.depth_only = {}          # (key, team) -> synthetic record for healthy players with no snaps yet
        self._build()

    # -- lookups -----------------------------------------------------------
    def sleeper(self, name: str, tm: str):
        c = self._sl.get(U.norm(name)) or []
        tm = U.team(tm)
        for p in c:
            if U.team(p.get("team")) == tm:
                return p
        return c[0] if len(c) == 1 else None

    @staticmethod
    def _status(sp) -> str:
        return (sp.get("injury_status") or "").lower()

    # -- plan --------------------------------------------------------------
    def _candidates(self, t: str) -> list:
        """Healthy skill players on a team, including depth-chart players who haven't played yet."""
        out, seen = [], set()
        for recs in self.us["players"].values():
            for r in recs:
                if r["team"] != t or r["position"] not in CATCHERS:
                    continue
                sp = self.sleeper(r["name"], t)
                if sp is None or U.team(sp.get("team")) != t or sp.get("status") != "Active":
                    continue
                if self._status(sp) in OUT_INJ:
                    continue
                key = (U.norm(r["name"]), t)
                seen.add(key)
                out.append({"key": key, "name": r["name"], "position": r["position"],
                            "carry_share": r["carry_share"], "target_share": r["target_share"],
                            "depth": sp.get("depth_chart_order") or 9, "snap_pct": r["snap_pct"]})
        for sp in self._by_team.get(t, []):
            key = (U.norm(sp.get("full_name")), t)
            if (key in seen or sp.get("position") not in CATCHERS or sp.get("status") != "Active"
                    or self._status(sp) in OUT_INJ or (sp.get("depth_chart_order") or 9) > 3):
                continue
            seen.add(key)
            out.append({"key": key, "name": sp.get("full_name"), "position": sp["position"],
                        "carry_share": 0.0, "target_share": 0.0,
                        "depth": sp.get("depth_chart_order") or 9, "snap_pct": None})
            self.depth_only[key] = {"name": sp.get("full_name"), "position": sp["position"], "team": t,
                                    "depth": sp.get("depth_chart_order") or 9}
        return out

    @staticmethod
    def _allocate(out_rec: dict, cands: list) -> dict:
        """How an absent player's carries and targets are redistributed: {key: (d_carry, d_target)}."""
        f = out_rec["presence"]
        vc, vt = f * out_rec["carry_share"], f * out_rec["target_share"]
        res = {}
        if vc >= 0.02:
            rbs = [c for c in cands if c["position"] in RUSHERS]
            nxt = min(rbs, key=lambda c: c["depth"]) if rbs else None
            w = {c["key"]: c["carry_share"] + 0.01 + (FLOOR_CARRY if c is nxt else 0.0) for c in rbs}
            tot = sum(w.values())
            for k, x in w.items():
                res[k] = (vc * x / tot, 0.0)
        if vt >= 0.02:
            pos = out_rec["position"]
            samepos = [c for c in cands if c["position"] == pos]
            nxt = min(samepos, key=lambda c: c["depth"]) if samepos else None
            w = {c["key"]: (c["target_share"] + 0.01) * (SAME_POS if c["position"] == pos else 1.0)
                 + (FLOOR_TGT if c is nxt else 0.0) for c in cands}
            tot = sum(w.values())
            for k, x in w.items():
                dc, dt = res.get(k, (0.0, 0.0))
                res[k] = (dc, dt + vt * x / tot)
        return res

    def _build(self):
        for t in self.us["teams"]:
            ents = []
            for recs in self.us["players"].values():
                for r in recs:
                    if r["team"] == t and r["position"] in CATCHERS:
                        sp = self.sleeper(r["name"], t)
                        if sp is not None and U.team(sp.get("team")) == t:
                            ents.append((r, sp))
            cands = self._candidates(t)
            for r, sp in ents:
                st = self._status(sp)
                if st in OUT_INJ:
                    target = self.plan
                elif st == "questionable":
                    target = self.cond
                else:
                    continue
                label = (sp.get("injury_status") or "Out") + (f", {sp['injury_body_part']}" if sp.get("injury_body_part") else "")
                for k, (dc, dt) in self._allocate(r, cands).items():
                    e = target.setdefault(k, {"dc": 0.0, "dt": 0.0, "who": []})
                    e["dc"], e["dt"] = e["dc"] + dc, e["dt"] + dt
                    e["who"].append({"name": r["name"], "label": label, "dc": dc, "dt": dt})
            for pos in ("RB", "WR", "TE"):
                grp = sorted((c for c in cands if c["position"] == pos),
                             key=lambda c: -(c["snap_pct"] if c["snap_pct"] is not None
                                              else (c["carry_share"] + c["target_share"] - 1.0)))
                for i, c in enumerate(grp, 1):
                    self.ranks[c["key"]] = f"{pos}{i}"

    # -- news ----------------------------------------------------------------
    def news_for(self, name: str):
        base = _SUFFIX_RE.sub("", _clean(name).lower()).strip()
        if not base or " " not in base:
            return None
        if base in self._news:
            return self._news[base]
        rx, found = re.compile(r"\b" + re.escape(base) + r"\b"), None
        for a in self.articles:
            text = a["headline"] + ". " + a["desc"]
            if rx.search(text.lower()):
                tag = "role" if _ROLE.search(text) else ("injury" if _INJ.search(text) else "news")
                found = {"headline": a["headline"], "blurb": a["desc"][:160], "link": a["link"], "tag": tag}
                break
        self._news[base] = found
        return found

    # -- QB ------------------------------------------------------------------
    def qb_note(self, t: str) -> str:
        tm = self.us["teams"].get(t) or {}
        notes = []
        if tm.get("qb_prev") and tm.get("qb") and tm["qb_prev"] != tm["qb"]:
            notes.append(f"{tm['qb']} started last week in place of {tm['qb_prev']}")
        qbs = sorted((p for p in self._by_team.get(t, []) if p.get("position") == "QB" and p.get("status") == "Active"),
                     key=lambda p: p.get("depth_chart_order") or 9)
        if qbs:
            starter = qbs[0]
            st = self._status(starter)
            if st in OUT_INJ:
                backup = qbs[1].get("full_name") if len(qbs) > 1 else ""
                notes.append(f"QB {starter.get('full_name')} is out" + (f", {backup} likely starts" if backup else ""))
            elif st == "questionable":
                notes.append(f"QB {starter.get('full_name')} is questionable")
        return "; ".join(notes)

    # -- per-player ------------------------------------------------------------
    def _text(self, pos: str, rec: dict, role: str) -> str:
        bits = [role]
        if pos == "QB":
            tm = self.us["teams"].get(rec["team"]) or {}
            bits.append(f"{rec['att_pg']:.0f} att/g")
            if tm:
                bits.append(f"{_pct(tm['pass_rate'])} pass rate")
            return " · ".join(bits)
        if rec.get("snap_pct") is not None:
            bits.append(f"{_pct(rec['snap_pct'])} snaps")
        if pos in RUSHERS:
            bits.append(f"{rec['carries_pg']:.1f} car/g")
            bits.append(f"{rec['targets_pg']:.1f} tgt/g")
        else:
            bits.append(f"{rec['targets_pg']:.1f} tgt/g ({_pct(rec['target_share'])} of team)")
        if rec.get("trend") is not None and abs(rec["trend"]) >= 10:
            bits.append(f"snaps {rec['trend']:+d} last 2")
        return " · ".join(bits)

    def info(self, p: dict) -> dict:
        pos, t = p.get("position"), U.team(p.get("team"))
        if pos not in ("QB", "RB", "WR", "TE") or not t or t not in self.us["teams"]:
            return {}
        rec = U.find(self.us, p.get("name"), t)
        key = (U.norm(p.get("name")), t)
        out = {"news": self.news_for(p.get("name")), "qb_note": self.qb_note(t) if pos != "QB" else ""}
        if rec is None:
            d = self.depth_only.get(key)
            sp = self.sleeper(p.get("name"), t)
            depth = d["depth"] if d else (sp.get("depth_chart_order") if sp else None)
            if depth and depth <= 4:
                out["usage"] = {"role": f"{pos}{depth}", "text": f"{pos}{depth} · no snaps yet", "team": t}
        else:
            role = self.ranks.get(key) or ("QB1" if pos == "QB" else pos)
            if pos == "QB":
                role = "QB1"
            out["usage"] = {"role": role, "text": self._text(pos, rec, role), "team": t,
                            "snap_pct": rec["snap_pct"], "target_share": rec["target_share"],
                            "carry_share": rec["carry_share"], "targets_pg": rec["targets_pg"],
                            "carries_pg": rec["carries_pg"], "trend": rec["trend"], "last": rec["last"],
                            "games": rec["games"]}
        tm = self.us["teams"][t]
        out["usage"] = out.get("usage") or {}
        out["usage"]["qb"] = tm.get("qb", "")
        out["usage"]["qb_att_pg"] = round(tm.get("att_pg", 0.0), 1)

        for src, field in ((self.plan, "boost"), (self.cond, "if_out")):
            e = src.get(key)
            if not e or pos == "QB":
                continue
            ppc, ppt = PTS.get(pos, (0.0, 1.5))
            dc, dt = min(e["dc"], MAX_DC), min(e["dt"], MAX_DT)
            raw = dc * tm["car_pg"] * ppc + dt * tm["att_pg"] * ppt
            val = round(min(CAP, ADJ_WEIGHT * raw), 1)
            if val < MIN_BOOST:
                continue
            who = sorted(e["who"], key=lambda w: -(w["dc"] + w["dt"]))
            out[field] = val
            out[field + "_why"] = ", ".join(f"{w['name']} ({w['label']})" for w in who[:2])
            out[field + "_gain"] = {"carries": round(dc * tm["car_pg"], 1), "targets": round(dt * tm["att_pg"], 1)}
            if field == "boost":
                out["boost_news"] = next((n for n in (self.news_for(w["name"]) for w in who) if n), None)
        return out

    def annotate(self, players: list) -> int:
        """Adds usage, role boost, news to each player dict and folds the boost into
        'projected' (ESPN's own number stays in 'projected_espn'). Returns how many got a boost."""
        n = 0
        for p in players:
            if p.get("_roles"):                 # the same dict can sit in several lists
                continue
            p["_roles"] = True
            p.setdefault("projected_espn", p.get("projected"))
            info = self.info(p)
            if not info:
                continue
            playing = isinstance(p.get("projected"), (int, float)) and p["projected"] > 0
            if not playing:
                for k in ("boost", "boost_why", "boost_gain", "boost_news", "if_out", "if_out_why", "if_out_gain"):
                    info.pop(k, None)
            p.update(info)
            if info.get("boost"):
                p["projected"] = round(p["projected"] + info["boost"], 2)
                n += 1
        return n


_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv)\b\.?", re.I)


ROLE_CHANGE = 2.0      # inherited carries + targets per game that make a role change worth showing


def inherited(p: dict) -> float:
    """Extra carries plus targets per game he picks up from absent teammates."""
    g = p.get("boost_gain") or {}
    return (g.get("carries") or 0.0) + (g.get("targets") or 0.0)


def watch(roster: list, free_agents: list, limit: int = 6) -> list:
    """Players whose situation changed enough to look at: yours first, then the wire. Judged by
    the extra work he inherits, not the (deliberately small) points added to his projection."""
    def interesting(p):
        n = p.get("news") or {}
        return bool(inherited(p) >= ROLE_CHANGE or p.get("qb_note") or n.get("tag") == "role")

    def entry(p, mine):
        return {"name": p["name"], "position": p.get("position"), "team": p.get("team"), "mine": mine,
                "boost": p.get("boost") or 0.0, "why": p.get("boost_why", ""), "qb_note": p.get("qb_note", ""),
                "news": p.get("news") or p.get("boost_news"), "text": (p.get("usage") or {}).get("text", "")}

    mine = sorted((entry(p, True) for p in roster if interesting(p)), key=lambda e: -e["boost"])
    wire = sorted((entry(p, False) for p in free_agents if inherited(p) >= ROLE_CHANGE), key=lambda e: -e["boost"])
    return (mine + wire)[:limit]
