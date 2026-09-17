"""Renders the static dashboard.

Call-sheet DNA -- ruled rows, not cards; color only where something needs
action -- but softened for daily use: rounded sheets, generous spacing, a
sticky section nav, and tabbed position rankings.
"""

from __future__ import annotations
import html
from datetime import datetime

CSS = """
:root{--paper:#E9E7E2;--sheet:#FDFCFA;--ink:#1B1E22;--muted:#71757D;--rule:#E3E0DA;
      --out:#A81F27;--quest:#B87514;--act:#1D5B4C;--act-soft:#E4EEEA;--pill:#EFEDE8}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Barlow',system-ui,sans-serif;
     font-size:16px;line-height:1.5;-webkit-text-size-adjust:100%}
.wrap{max-width:680px;margin:0 auto;padding:18px 16px 72px}
header{margin-bottom:14px}
h1{font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:36px;line-height:1;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:15px;margin:0}
nav{position:sticky;top:0;z-index:5;background:var(--paper);padding:10px 0 12px;margin-bottom:6px}
nav ul{list-style:none;margin:0;padding:0;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
nav ul::-webkit-scrollbar{display:none}
nav a{display:block;padding:7px 13px;border-radius:999px;background:var(--pill);color:var(--ink);
      text-decoration:none;font-size:14.5px;font-weight:500;white-space:nowrap}
nav a:hover,nav a:focus-visible{background:var(--sheet)}
.sheet{background:var(--sheet);border-radius:14px;padding:20px 18px 14px;margin-bottom:16px;
       box-shadow:0 1px 0 rgba(27,30,34,.05)}
h2{font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:24px;margin:0 0 12px}
.group{font-family:'Barlow Condensed',sans-serif;color:var(--muted);font-size:16px;margin:18px 0 4px}
.group:first-of-type{margin-top:0}
.row{display:grid;grid-template-columns:1fr auto;gap:12px;padding:10px 0;border-bottom:1px solid var(--rule);align-items:center}
.row:last-child{border-bottom:none}
.nm{font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:500;line-height:1.15}
.meta{font-size:13px;color:var(--muted);margin-top:1px}
.num{font-variant-numeric:tabular-nums;font-size:15px;text-align:right;white-space:nowrap;line-height:1.25}
.num small{display:block;font-size:12px;color:var(--muted)}
.flag{font-size:12.5px;font-weight:600}
.flag.out{color:var(--out)} .flag.quest{color:var(--quest)}
.dim{opacity:.55}
.alert{border-left:3px solid var(--out);padding:6px 0 6px 12px;margin-bottom:12px}
.alert.warn{border-left-color:var(--quest)} .alert.info{border-left-color:var(--act)}
.alert p{margin:0}
.alert .who{font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:600}
.alert .why{font-size:14px;color:var(--muted)}
.summary{background:var(--act-soft);border-radius:10px;padding:12px 14px;margin-bottom:12px;font-size:15px}
.summary b{font-weight:600}
.swap{display:grid;grid-template-columns:1fr auto 1fr auto;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid var(--rule)}
.swap:last-child{border-bottom:none}
.swap .arrow{color:var(--muted);font-size:14px}
.swap .gain{font-variant-numeric:tabular-nums;color:var(--act);font-weight:600;white-space:nowrap}
.slot{display:inline-block;min-width:44px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.tabs{display:flex;gap:4px;background:var(--pill);border-radius:10px;padding:4px;margin-bottom:8px}
.tabs button{flex:1;border:0;background:transparent;border-radius:7px;padding:8px 0;font:inherit;font-size:14px;
             font-weight:500;color:var(--muted);cursor:pointer}
.tabs button[aria-selected=true]{background:var(--sheet);color:var(--ink);box-shadow:0 1px 2px rgba(27,30,34,.08)}
.panel{display:none} .panel[data-active]{display:block}
.rk{display:grid;grid-template-columns:28px 1fr auto;gap:10px;padding:9px 0;border-bottom:1px solid var(--rule);align-items:center}
.rk:last-child{border-bottom:none}
.rk .n{font-variant-numeric:tabular-nums;color:var(--muted);font-size:14px}
.rk.mine{background:linear-gradient(90deg,var(--act-soft),transparent 60%);margin:0 -8px;padding-left:8px;padding-right:8px;border-radius:6px}
.cols{display:grid;grid-template-columns:28px 1fr auto;gap:10px;font-size:12px;color:var(--muted);padding:0 0 6px}
.cols span:last-child{text-align:right}
.reason{font-size:13px;color:var(--muted)}
.news .row{display:block} .news a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}
.news a:hover,.news a:focus-visible{border-bottom-color:var(--ink)}
.empty{color:var(--muted);font-size:15px;margin:4px 0 8px}
.foot{color:var(--muted);font-size:13px;margin-top:8px}
:focus-visible{outline:2px solid var(--act);outline-offset:2px}
@media(max-width:420px){h1{font-size:31px}.wrap{padding:12px 12px 56px}.sheet{padding:16px 14px 10px}.tabs button{font-size:13px}}
"""

JS = """
document.querySelectorAll('.tabs').forEach(function(tabs){
  var btns=tabs.querySelectorAll('button');
  btns.forEach(function(b){b.addEventListener('click',function(){
    btns.forEach(function(x){x.setAttribute('aria-selected','false')});
    b.setAttribute('aria-selected','true');
    tabs.parentElement.querySelectorAll('.panel').forEach(function(p){
      if(p.dataset.pos===b.dataset.pos){p.setAttribute('data-active','')}else{p.removeAttribute('data-active')}
    });
  })});
});
"""

_BAD = {"OUT", "DOUBTFUL", "IR", "SUSPENSION", "INJURY_RESERVE"}
_MEH = {"QUESTIONABLE", "DAY_TO_DAY", "PROBABLE"}


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _pts(v) -> str:
    return f"{v:.1f}" if isinstance(v, (int, float)) else "&mdash;"


def _flag(status: str) -> str:
    s = (status or "").upper().replace(" ", "_")
    label = s.replace("_", " ").title()
    if s in _BAD:
        return f'<span class="flag out">{_e(label)}</span>'
    if s in _MEH:
        return f'<span class="flag quest">{_e(label)}</span>'
    return ""


def _meta(p: dict) -> str:
    bits = " ".join(b for b in [p.get("position"), p.get("team")] if b)
    if p.get("opponent"):
        bits += f" vs {p['opponent']}"
    return f"{_e(bits)} {_flag(p.get('injury', ''))}"


def _name_block(p: dict, slot=True) -> str:
    s = f'<span class="slot">{_e(p.get("slot",""))}</span>' if slot and p.get("slot") not in ("BE", "", None) else ""
    return f'<div>{s}<span class="nm">{_e(p["name"])}</span><div class="meta">{_meta(p)}</div></div>'


def _player_row(p: dict) -> str:
    dim = " dim" if not p.get("starting", True) else ""
    return f'<div class="row{dim}">{_name_block(p)}<div class="num">{_pts(p.get("projected"))}</div></div>'


def _alerts(roster: list[dict]) -> str:
    items = []
    for p in roster:
        if not p.get("starting"):
            continue
        s = (p.get("injury") or "").upper().replace(" ", "_")
        if s in _BAD:
            items.append(("alert", p["name"], f"Listed {s.replace('_',' ').lower()} and in your starting lineup."))
        elif s in _MEH:
            items.append(("alert warn", p["name"], "Questionable. Check inactives before kickoff."))
        elif not p.get("opponent"):
            items.append(("alert warn", p["name"], "No game this week. Likely a bye."))
    if not items:
        return '<p class="empty">Nothing flagged. Every starter has a game and a clean status.</p>'
    return "".join(f'<div class="{c}"><p class="who">{_e(w)}</p><p class="why">{_e(y)}</p></div>' for c, w, y in items)


def _optimizer(opt: dict) -> str:
    if not opt.get("lineup"):
        return '<p class="empty">Connect ESPN to see lineup recommendations.</p>'
    if not opt["swaps"]:
        head = (f'<div class="summary">Your lineup is already the best available. '
                f'Projected <b>{opt["optimal_total"]}</b> points.</div>')
    else:
        n = len(opt["swaps"])
        head = (f'<div class="summary"><b>{n} swap{"s" if n > 1 else ""}</b> would add '
                f'<b>+{opt["gain"]}</b> projected points ({opt["current_total"]} to {opt["optimal_total"]}).</div>')
        for s in opt["swaps"]:
            out_block = _name_block(s["out"], slot=False) if s["out"] else '<div><span class="meta">open slot</span></div>'
            head += (f'<div class="swap">{_name_block(s["in"], slot=False)}<span class="arrow">for</span>'
                     f'{out_block}<span class="gain">+{s["gain"]}</span></div>')
    body = '<p class="group">Best lineup</p>'
    for e in opt["lineup"]:
        if e["player"]:
            p = dict(e["player"], slot=e["slot"])
            body += f'<div class="row">{_name_block(p)}<div class="num">{_pts(p.get("projected"))}</div></div>'
        else:
            body += (f'<div class="row"><div><span class="slot">{_e(e["slot"])}</span>'
                     f'<span class="meta">no healthy option</span></div><div class="num">&mdash;</div></div>')
    return head + body


def _rankings(rk: dict) -> str:
    if not any(rk.values()):
        return '<p class="empty">Connect ESPN to see rankings across your league\'s player pool.</p>'
    order = ["QB", "RB", "WR", "TE", "D/ST", "K"]
    tabs = '<div class="tabs" role="tablist">' + "".join(
        f'<button role="tab" data-pos="{_e(p)}" aria-selected="{"true" if i == 0 else "false"}">{_e(p)}</button>'
        for i, p in enumerate(order)) + "</div>"
    panels = ""
    for i, pos in enumerate(order):
        rows = ""
        for r in rk.get(pos, []):
            owner = (" &middot; " + _e(r["owner"])) if r.get("owner") and not r.get("mine") else (" &middot; available" if not r.get("owner") else "")
            rows += (f'<div class="rk{" mine" if r.get("mine") else ""}"><span class="n">{r["rank"]}</span>'
                     f'<div><span class="nm">{_e(r["name"])}</span><div class="meta">{_meta(r)}{owner}</div></div>'
                     f'<div class="num">{_pts(r["proj"])}<small>{_pts(r["ppg_2025"])} last yr</small></div></div>')
        panels += (f'<div class="panel" data-pos="{_e(pos)}"{" data-active" if i == 0 else ""}>'
                   f'<div class="cols"><span>#</span><span>Player</span><span>Proj / 2025 avg</span></div>'
                   f'{rows or "<p class=empty>No data.</p>"}</div>')
    return tabs + panels


def _trades(tr: dict) -> str:
    if not tr:
        return '<p class="empty">Connect ESPN to see trade targets.</p>'
    out = ""
    if tr["needs"]:
        out += '<p class="group">Where you\'re thin</p>' + "".join(
            f'<div class="row"><div><span class="nm">{_e(n["position"])}</span>'
            f'<div class="meta">your best starter scores {n["best"]}, league median is {n["median"]}</div></div>'
            f'<div class="num">&minus;{n["gap"]}</div></div>' for n in tr["needs"])
    else:
        out += '<p class="empty">No position where your starter is below the league median.</p>'
    if tr["chips"]:
        out += '<p class="group">Bench players other teams would start</p>' + "".join(
            f'<div class="row"><div><span class="nm">{_e(c["name"])}</span><div class="meta">{_meta(c)} &middot; median starter {c["median"]}</div></div>'
            f'<div class="num">{_pts(c["score"])}</div></div>' for c in tr["chips"])
    if tr["targets"]:
        out += '<p class="group">Targets on teams with surplus</p>' + "".join(
            f'<div class="row"><div><span class="nm">{_e(t["name"])}</span><div class="meta">{_meta(t)}</div>'
            f'<div class="reason">{_e(t["reason"])}</div></div>'
            f'<div class="num">{_pts(t["proj"])}<small>{_pts(t["ppg_2025"])} last yr</small></div></div>' for t in tr["targets"])
    if tr["buy_low"]:
        out += '<p class="group">Buy low</p>' + "".join(
            f'<div class="row"><div><span class="nm">{_e(b["name"])}</span><div class="meta">{_meta(b)} &middot; {_e(b["owner"])}</div>'
            f'<div class="reason">{_e(b["reason"])}</div></div>'
            f'<div class="num">{_pts(b["proj"])}<small>{_pts(b["ppg_2025"])} last yr</small></div></div>' for b in tr["buy_low"])
    return out


def build(data: dict) -> str:
    week = data.get("week", "?")
    team = data.get("team_name") or "Your team"
    roster = data.get("roster", [])
    starters = [p for p in roster if p.get("starting")]
    bench = [p for p in roster if not p.get("starting")]

    def rows(lst):
        return "".join(_player_row(p) for p in lst) or '<p class="empty">Nothing here.</p>'

    add_rows = "".join(
        f'<div class="row"><div><span class="nm">{_e(a["name"])}</span><div class="meta">{_e(a.get("position",""))} {_e(a.get("team",""))} {_flag(a.get("injury",""))}</div></div>'
        f'<div class="num">{a.get("count",0):,}<small>adds</small></div></div>'
        for a in data.get("trending_adds", [])) or '<p class="empty">No trending data.</p>'

    news_rows = "".join(
        f'<div class="row"><a href="{_e(n.get("link","#"))}">{_e(n.get("headline",""))}</a>'
        f'<div class="meta">{_e((n.get("description") or "")[:160])}</div></div>'
        for n in data.get("news", [])) or '<p class="empty">No headlines.</p>'

    opp = f' &middot; vs {_e(data["opponent_name"])}' if data.get("opponent_name") else ""

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#E9E7E2">
<title>Week {week} &mdash; {_e(team)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body><div class="wrap">

<header><h1>Week {week}</h1>
<p class="sub">{_e(team)} &middot; {_e(data.get('record',''))}{opp}</p></header>

<nav aria-label="Sections"><ul>
<li><a href="#lineup">Lineup</a></li><li><a href="#best">Best lineup</a></li>
<li><a href="#rank">Rankings</a></li><li><a href="#trades">Trades</a></li>
<li><a href="#waiver">Waivers</a></li><li><a href="#news">News</a></li></ul></nav>

<section class="sheet" id="lineup"><h2>Needs your attention</h2>{_alerts(roster)}
<p class="group">Starting</p>{rows(starters)}<p class="group">Bench</p>{rows(bench)}</section>

<section class="sheet" id="best"><h2>Best lineup this week</h2>{_optimizer(data.get("optimizer", {}))}</section>

<section class="sheet" id="rank"><h2>Position rankings</h2>{_rankings(data.get("rankings", {}))}</section>

<section class="sheet" id="trades"><h2>Trade targets</h2>{_trades(data.get("trades", {}))}</section>

<section class="sheet" id="waiver"><h2>Most added this week</h2>{add_rows}</section>

<section class="sheet news" id="news"><h2>Headlines</h2>{news_rows}</section>

<p class="foot">Updated {_e(data.get("generated",""))}. Rankings blend this week's projection (65%) with 2025 points per game (35%).</p>
</div><script>{JS}</script></body></html>"""


def timestamp() -> str:
    return datetime.now().strftime("%a %b %d, %I:%M %p")
