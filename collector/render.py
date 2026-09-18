"""Renders the static dashboard.

Design: deep navy surfaces, one saturated green carrying every "go" signal,
blunt START / SIT / CONSIDER verdicts, tier bands in the rankings, bottom
tab bar on phones and top pills on wider screens. Light mode keeps the same
layout on a pale navy-tinted paper.
"""

from __future__ import annotations
import html
from datetime import datetime

DARK = ("--paper:#0D1626;--sheet:#12203A;--line:#1F2C42;--ink:#E9EEF5;--muted:#8A9BB5;"
        "--green:#22D36E;--green-soft:#122A1C;--green-line:#1E5B36;--green-ink:#7ED9A3;--on-green:#062B14;"
        "--out:#F0646C;--out-soft:#3A1A20;--out-line:#6B2830;--quest:#F2B33D;--quest-soft:#3A2E14;--quest-line:#6B5520;"
        "--blue:#4FA3F7;--on-blue:#061A33;--amber:#F2B33D;--on-amber:#2E2000;--bar:#0A1220;--glass:rgba(13,22,38,.85)")
LIGHT = ("--paper:#EEF2F7;--sheet:#FFFFFF;--line:#D9E0EA;--ink:#0D1626;--muted:#5E6E88;"
         "--green:#15A853;--green-soft:#E3F6EA;--green-line:#A9E3C0;--green-ink:#0E6B36;--on-green:#FFFFFF;"
         "--out:#C8323C;--out-soft:#FBE7E9;--out-line:#F0B7BC;--quest:#B8760F;--quest-soft:#FFF4DF;--quest-line:#F2D59A;"
         "--blue:#2E7FD1;--on-blue:#FFFFFF;--amber:#E39A15;--on-amber:#2E2000;--bar:#FFFFFF;--glass:rgba(238,242,247,.88)")

CSS = f"""
:root{{{LIGHT}}}
:root[data-theme=dark]{{{DARK}}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{{DARK}}}}}
html{{font-size:16px;scroll-behavior:smooth;scroll-padding-top:8px}}
html[data-size=small]{{font-size:14px}} html[data-size=large]{{font-size:18px}} html[data-size=xl]{{font-size:20px}}
*{{box-sizing:border-box}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}} *{{transition:none!important}}}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:'Barlow',system-ui,sans-serif;font-size:1rem;line-height:1.45;
     -webkit-text-size-adjust:100%;transition:background .2s,color .2s}}
.wrap{{max-width:720px;margin:0 auto;padding:16px 16px 92px}}
.cond{{font-family:'Barlow Condensed',sans-serif;font-weight:600;letter-spacing:.01em}}
header{{display:flex;align-items:flex-end;gap:12px;padding:4px 0 14px}}
header .wk{{color:var(--muted);font-size:.8125rem}}
header h1{{font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:2rem;line-height:1;margin:2px 0 0;letter-spacing:-.005em}}
header .opp{{margin-left:auto;text-align:right}}
header .opp .cond{{font-size:1.0625rem}}
.gear{{margin-left:10px;width:36px;height:36px;border-radius:10px;border:1px solid var(--line);background:var(--sheet);color:var(--muted);
      display:inline-flex;align-items:center;justify-content:center;cursor:pointer;flex:none}}
.gear:hover{{color:var(--ink)}}
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}}
.stat{{background:var(--sheet);border:1px solid var(--line);border-radius:14px;padding:11px 13px}}
.stat.wide{{grid-column:1/-1}}
.stat.go{{background:var(--green-soft);border-color:var(--green-line)}}
.stat .l{{font-size:.75rem;color:var(--muted)}} .stat.go .l{{color:var(--green-ink)}}
.stat .v{{font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:1.5rem;line-height:1.1;margin:2px 0}}
.stat.go .v{{color:var(--green)}}
.stat .s{{font-size:.75rem;color:var(--muted)}} .stat.go .s{{color:var(--green-ink)}}
.sheet{{background:var(--sheet);border:1px solid var(--line);border-radius:16px;margin-bottom:14px;overflow:hidden}}
.hd{{display:flex;align-items:baseline;gap:8px;padding:14px 16px 6px}}
.hd h2{{font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:1.25rem;margin:0;white-space:nowrap}}
.hd .m{{font-size:.75rem;color:var(--muted)}}
.row{{display:flex;align-items:center;gap:10px;padding:10px 16px;border-top:1px solid var(--line)}}
.row.hi{{background:var(--green-soft)}}
.row .who{{min-width:0;flex:1}}
.nm{{font-family:'Barlow Condensed',sans-serif;font-size:1.0625rem;font-weight:500;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.m{{font-size:.75rem;color:var(--muted)}}
.num{{text-align:right;font-variant-numeric:tabular-nums;font-size:.875rem;white-space:nowrap;line-height:1.2}}
.num small{{display:block;font-size:.6875rem;color:var(--muted)}}
.chip{{display:inline-block;padding:3px 9px;border-radius:6px;font-size:.6875rem;font-weight:500;font-family:'Barlow Condensed',sans-serif;letter-spacing:.06em;white-space:nowrap}}
.chip.start{{background:var(--green);color:var(--on-green)}}
.chip.sit{{background:var(--out-soft);color:var(--out);border:1px solid var(--out-line)}}
.chip.consider{{background:var(--quest-soft);color:var(--quest);border:1px solid var(--quest-line)}}
.chip.slot{{background:transparent;color:var(--muted);border:1px solid var(--line);min-width:44px;text-align:center}}
.chip.stream{{background:var(--blue);color:var(--on-blue)}}
.chip.bench{{background:var(--quest-soft);color:var(--quest);border:1px solid var(--quest-line)}}
.chip.stash{{background:transparent;color:var(--blue);border:1px solid var(--blue)}}
.act{{padding:7px 16px;font-size:.8125rem;border-top:1px solid var(--line);color:var(--muted)}} .act b{{font-weight:500;color:var(--ink)}}
.f-out{{color:var(--out)}} .f-quest{{color:var(--quest)}} .f-go{{color:var(--green)}}
.grp{{padding:10px 16px 4px;font-family:'Barlow Condensed',sans-serif;font-size:.8125rem;letter-spacing:.06em;color:var(--muted);border-top:1px solid var(--line)}}
.pos{{display:flex;gap:4px;padding:8px 16px 6px}}
.pos button{{flex:1;text-align:center;padding:7px 0;border-radius:8px;font:inherit;font-size:.75rem;font-weight:500;color:var(--muted);
   background:transparent;border:1px solid var(--line);cursor:pointer;transition:background .15s,color .15s,border-color .15s}}
.pos button[aria-selected=true]{{background:var(--green);color:var(--on-green);border-color:var(--green)}}
.panel{{display:none}} .panel[data-active]{{display:block}}
.tier{{padding:5px 16px;font-family:'Barlow Condensed',sans-serif;font-size:.75rem;letter-spacing:.08em;font-weight:600}}
.tier.t1{{background:var(--green);color:var(--on-green)}} .tier.t2{{background:var(--blue);color:var(--on-blue)}}
.tier.t3{{background:var(--amber);color:var(--on-amber)}} .tier.t4{{background:var(--line);color:var(--ink)}}
.rk{{width:22px;color:var(--muted);font-size:.8125rem;font-variant-numeric:tabular-nums;flex:none}}
.row.me{{background:var(--green-soft)}}
.swap{{display:grid;grid-template-columns:1fr auto 1fr auto;gap:8px;align-items:center;padding:10px 16px;border-top:1px solid var(--line)}}
.swap .arrow{{color:var(--muted);font-size:.75rem}}
.swap .gain{{font-variant-numeric:tabular-nums;color:var(--green);font-weight:600;white-space:nowrap;font-size:.875rem}}
.alert{{padding:8px 16px;border-top:1px solid var(--line);border-left:3px solid var(--out)}}
.alert.warn{{border-left-color:var(--quest)}}
.alert .who{{font-family:'Barlow Condensed',sans-serif;font-size:1.0625rem;font-weight:600}} .alert .why{{font-size:.8125rem;color:var(--muted)}}
.status{{border:1px solid var(--quest-line);background:var(--quest-soft);border-radius:12px;padding:10px 14px;margin-bottom:14px;font-size:.875rem}}
.status p{{margin:0}} .status .why{{color:var(--muted);font-size:.8125rem;margin-top:2px}}
.reason{{font-size:.75rem;color:var(--muted);margin-top:2px}}
.news .row{{display:block}} .news a{{color:var(--ink);text-decoration:none;font-family:'Barlow Condensed',sans-serif;font-size:1.0625rem;font-weight:500}}
.news a:hover{{color:var(--green)}}
.empty{{color:var(--muted);font-size:.875rem;padding:6px 16px 14px;margin:0}}
.foot{{color:var(--muted);font-size:.75rem;padding:4px 2px 0}}
nav.top{{display:none}}
nav.bottom{{position:fixed;left:0;right:0;bottom:0;z-index:9;background:var(--glass);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
  border-top:1px solid var(--line);padding:6px 0 max(8px,env(safe-area-inset-bottom))}}
nav.bottom ul{{list-style:none;margin:0 auto;padding:0;display:flex;max-width:720px}}
nav.bottom li{{flex:1;min-width:0}}
nav.bottom a{{display:block;text-align:center;text-decoration:none;color:var(--muted);font-size:.6875rem;padding:4px 0}}
nav.bottom a svg{{display:block;margin:0 auto 2px;width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}}
nav.bottom a.on,nav.bottom a:hover{{color:var(--green)}}
#settings{{display:none}} #settings[data-open]{{display:block}}
.setrow{{display:grid;grid-template-columns:84px 1fr;gap:12px;align-items:center;padding:8px 16px}}
.setrow label{{font-size:.875rem;color:var(--muted)}}
.seg{{display:flex;gap:3px;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:3px}}
.seg button{{flex:1;border:1px solid transparent;background:transparent;border-radius:7px;padding:6px 0;font:inherit;font-size:.8125rem;font-weight:500;color:var(--muted);cursor:pointer;transition:background .15s,color .15s}}
.seg button[aria-pressed=true]{{background:var(--sheet);color:var(--ink);border-color:var(--line)}}
:focus-visible{{outline:2px solid var(--green);outline-offset:2px}}
@media(min-width:720px){{
  .wrap{{padding-bottom:40px}}
  .stats{{grid-template-columns:1fr 1fr 1fr}} .stat.wide{{grid-column:auto}}
  nav.bottom{{display:none}}
  nav.top{{display:block;position:sticky;top:0;z-index:5;background:var(--glass);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);padding:8px 0 12px;margin-bottom:8px}}
  nav.top ul{{list-style:none;margin:0;padding:0;display:flex;gap:6px}}
  nav.top a{{display:block;padding:6px 12px;border-radius:999px;color:var(--muted);border:1px solid var(--line);text-decoration:none;font-size:.875rem;font-weight:500;transition:background .15s,color .15s}}
  nav.top a:hover{{background:var(--sheet);color:var(--ink)}}
}}
"""

HEAD_JS = """(function(){try{var t=localStorage.getItem('ff-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);
var s=localStorage.getItem('ff-size');if(s&&s!=='default')document.documentElement.setAttribute('data-size',s);}catch(e){}})();"""

JS = """
(function(){
  var root=document.documentElement,panel=document.getElementById('settings');
  function toggle(e){e.preventDefault();if(panel.hasAttribute('data-open'))panel.removeAttribute('data-open');else{panel.setAttribute('data-open','');panel.scrollIntoView({block:'start'});}}
  document.querySelectorAll('[data-gear]').forEach(function(b){b.addEventListener('click',toggle)});
  function get(k,d){try{return localStorage.getItem(k)||d}catch(e){return d}}
  function set(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  function wire(name,key,attr,def){
    var btns=panel.querySelectorAll('[data-set="'+name+'"] button');
    function paint(v){btns.forEach(function(b){b.setAttribute('aria-pressed',b.dataset.v===v?'true':'false')});if(v===def)root.removeAttribute(attr);else root.setAttribute(attr,v);}
    paint(get(key,def));btns.forEach(function(b){b.addEventListener('click',function(){set(key,b.dataset.v);paint(b.dataset.v)})});
  }
  wire('theme','ff-theme','data-theme','auto');wire('size','ff-size','data-size','default');
  document.querySelectorAll('.pos').forEach(function(tabs){
    var btns=tabs.querySelectorAll('button');
    btns.forEach(function(b){b.addEventListener('click',function(){
      btns.forEach(function(x){x.setAttribute('aria-selected','false')});b.setAttribute('aria-selected','true');
      tabs.parentElement.querySelectorAll('.panel').forEach(function(p){if(p.dataset.pos===b.dataset.pos)p.setAttribute('data-active','');else p.removeAttribute('data-active')});
    })});
  });
  var links=document.querySelectorAll('nav.bottom a[href^="#"]'),secs=[];
  links.forEach(function(a){var s=document.querySelector(a.getAttribute('href'));if(s)secs.push([s,a])});
  function mark(){var y=window.scrollY+120,cur=null,best=-1;secs.forEach(function(p){var t=p[0].offsetTop;if(p[0].offsetParent!==null&&t<=y&&t>best){best=t;cur=p[1]}});if(!cur&&secs.length)cur=secs[0][1];links.forEach(function(a){a.classList.toggle('on',a===cur)});}
  window.addEventListener('scroll',mark,{passive:true});mark();
})();
"""

ICONS = {
    "lineup": '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    "waiver": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
    "rank": '<svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    "trades": '<svg viewBox="0 0 24 24"><path d="M7 10h10l-3-3M17 14H7l3 3"/></svg>',
    "news": '<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4zM8 9h8M8 13h8M8 17h5"/></svg>',
    "gear": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
}

_BAD = {"OUT", "DOUBTFUL", "IR", "SUSPENSION", "INJURY_RESERVE"}
_MEH = {"QUESTIONABLE", "DAY_TO_DAY", "PROBABLE"}


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _pts(v) -> str:
    return f"{v:.1f}" if isinstance(v, (int, float)) else "&mdash;"


def _last(v) -> str:
    """Last-season line under a projection. Hidden when there's no history rather than showing 0.0."""
    return f"<small>{_pts(v)} last yr</small>" if isinstance(v, (int, float)) and v > 0 else ""


def _blurb(text, limit: int = 150) -> str:
    """Headline description trimmed at a word boundary, minus the feed's stray leading dash."""
    t = " ".join((text or "").split()).lstrip("\u2014\u2013- ")
    if len(t) <= limit:
        return t
    return t[:limit].rsplit(" ", 1)[0].rstrip(",;:\u2014\u2013-") + "\u2026"


def _inj(p: dict) -> str:
    s = (p.get("injury") or "").upper().replace(" ", "_")
    label = s.replace("_", " ").title()
    if s in _BAD:
        return f' &middot; <span class="f-out">{_e(label)}</span>'
    if s in _MEH:
        return f' &middot; <span class="f-quest">{_e(label)}</span>'
    return ""


def _meta(p: dict, extra: str = "") -> str:
    bits = " ".join(b for b in [p.get("position"), p.get("team")] if b)
    if p.get("opponent"):
        bits += f" vs {p['opponent']}"
    return f'<div class="m">{_e(bits)}{_inj(p)}{extra}</div>'


def _verdicts(roster: list[dict], opt: dict) -> dict:
    """name -> ('start'|'sit'|'consider', note)"""
    if not opt or not opt.get("lineup"):
        return {}
    optimal = {e["player"]["name"] for e in opt["lineup"] if e.get("player")}
    out = {}
    for p in roster:
        s = (p.get("injury") or "").upper().replace(" ", "_")
        if p["name"] in optimal:
            if s in _MEH:
                out[p["name"]] = ("consider", "" if p.get("starting") else "starts if active")
            elif not p.get("starting"):
                out[p["name"]] = ("start", "on your bench, start him")
            else:
                out[p["name"]] = ("start", "")
        else:
            if s in _BAD:
                out[p["name"]] = ("sit", "")
            elif p.get("starting"):
                out[p["name"]] = ("sit", "better option on bench")
            else:
                out[p["name"]] = ("sit", "")
    return out


def _lineup(roster: list[dict], opt: dict) -> str:
    starters = [p for p in roster if p.get("starting")]
    bench = [p for p in roster if not p.get("starting")]
    v = _verdicts(roster, opt)

    def row(p):
        verdict, note = v.get(p["name"], (None, ""))
        # Bench rows only get a chip when there's something to do; red belongs on a starter who should sit.
        show_chip = verdict and (p.get("starting") or verdict != "sit")
        chip = f'<span class="chip {verdict}">{verdict.upper()}</span>' if show_chip else ""
        extra = f' &middot; <span class="f-go">{_e(note)}</span>' if note and verdict == "start" else (
                f' &middot; <span class="{"f-quest" if verdict == "consider" else "f-out"}">{_e(note)}</span>' if note else "")
        hi = " hi" if (verdict == "start" and not p.get("starting")) else ""
        slot = f'<span class="chip slot">{_e(p.get("slot", ""))}</span>' if p.get("slot") not in ("BE", "", None) else ""
        return (f'<div class="row{hi}">{slot}<div class="who"><div class="nm">{_e(p["name"])}</div>{_meta(p, extra)}</div>'
                f'{chip}<div class="num">{_pts(p.get("projected"))}</div></div>')

    if not roster:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    return ('<div class="grp">STARTING</div>' + "".join(row(p) for p in starters) +
            '<div class="grp">BENCH</div>' + "".join(row(p) for p in bench))


def _alerts(roster: list[dict]) -> str:
    items = []
    for p in roster:
        if not p.get("starting"):
            continue
        s = (p.get("injury") or "").upper().replace(" ", "_")
        if s in _BAD:
            items.append(("alert", p["name"], f"Listed {s.replace('_', ' ').lower()} and in your starting lineup."))
        elif s in _MEH:
            items.append(("alert warn", p["name"], "Questionable. Check inactives before kickoff."))
        elif not p.get("opponent") and p.get("position") != "D/ST":
            items.append(("alert warn", p["name"], "No game this week. Likely a bye."))
    return "".join(f'<div class="{c}"><div class="who">{_e(w)}</div><div class="why">{_e(y)}</div></div>' for c, w, y in items)


def _swaps(opt: dict) -> str:
    if not opt or not opt.get("lineup"):
        return ""
    if not opt["swaps"]:
        return '<p class="empty">Your lineup is already the best available.</p>'
    out = ""
    for s in opt["swaps"]:
        o = s["out"]
        out_html = (f'<div class="nm">{_e(o["name"])}</div>' + _meta(o)) if o else '<span class="m">open slot</span>'
        out += (f'<div class="swap"><div><div class="nm">{_e(s["in"]["name"])}</div>{_meta(s["in"])}</div>'
                f'<span class="arrow">over</span>'
                f'<div>{out_html}</div>'
                f'<span class="gain">+{s["gain"]}</span></div>')
    return out


def _tiers(rows: list[dict]) -> list[int]:
    """Tier number per row. New tier when score drops >12% from the previous row."""
    tiers, t = [], 1
    for i, r in enumerate(rows):
        if i and rows[i - 1]["score"] > 0 and (rows[i - 1]["score"] - r["score"]) / rows[i - 1]["score"] > 0.12:
            t += 1
        tiers.append(min(t, 4))
    return tiers


def _rankings(rk: dict) -> str:
    if not any(rk.values()):
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    order = ["QB", "RB", "WR", "TE", "D/ST", "K"]
    tabs = '<div class="pos" role="tablist">' + "".join(
        f'<button role="tab" data-pos="{_e(p)}" aria-selected="{"true" if i == 0 else "false"}">{_e(p)}</button>'
        for i, p in enumerate(order)) + "</div>"
    panels = ""
    for i, pos in enumerate(order):
        rows = rk.get(pos, [])
        tiers = _tiers(rows)
        body, last = "", 0
        for r, t in zip(rows, tiers):
            if t != last:
                body += f'<div class="tier t{t}">TIER {t}</div>'
                last = t
            who = ' &middot; <span class="f-go">yours</span>' if r.get("mine") else (
                  f' &middot; {_e(r["owner"])}' if r.get("owner") else ' &middot; available')
            body += (f'<div class="row{" me" if r.get("mine") else ""}"><span class="rk">{r["rank"]}</span>'
                     f'<div class="who"><div class="nm">{_e(r["name"])}</div>{_meta(r, who)}</div>'
                     f'<div class="num">{_pts(r["proj"])}{_last(r["ppg_2025"])}</div></div>')
        panels += f'<div class="panel" data-pos="{_e(pos)}"{" data-active" if i == 0 else ""}>{body or "<p class=empty>No data.</p>"}</div>'
    return tabs + panels


def _trades(tr: dict) -> str:
    if not tr:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    out = ""
    if tr["needs"]:
        out += '<div class="grp">WHERE YOU\'RE THIN</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(n["position"])}</div>'
            f'<div class="m">your best starter {n["best"]}, league median {n["median"]}</div></div>'
            f'<div class="num f-out">&minus;{n["gap"]}</div></div>' for n in tr["needs"])
    else:
        out += '<p class="empty">No position where your starter is below the league median.</p>'
    if tr["chips"]:
        out += '<div class="grp">TRADE CHIPS ON YOUR BENCH</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(c["name"])}</div>{_meta(c, " &middot; median starter " + str(c["median"]))}</div>'
            f'<div class="num">{_pts(c["score"])}</div></div>' for c in tr["chips"])
    if tr["targets"]:
        out += '<div class="grp">TARGETS ON TEAMS WITH SURPLUS</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(t["name"])}</div>{_meta(t)}<div class="reason">{_e(t["reason"])}</div></div>'
            f'<div class="num">{_pts(t["proj"])}{_last(t["ppg_2025"])}</div></div>' for t in tr["targets"])
    if tr["buy_low"]:
        out += '<div class="grp">BUY LOW</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(b["name"])}</div>{_meta(b, " &middot; " + _e(b["owner"]))}<div class="reason">{_e(b["reason"])}</div></div>'
            f'<div class="num">{_pts(b["proj"])}{_last(b["ppg_2025"])}</div></div>' for b in tr["buy_low"])
    return out


def _ordinal(n) -> str:
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _activity(rows: list[dict]) -> str:
    """One line per transaction: 'Sep 17  Lynch em All  added Malik Washington, dropped Cooper Kupp'."""
    verbs = {"FA ADDED": "added", "WAIVER ADDED": "claimed", "DROPPED": "dropped", "TRADED": "traded"}
    groups, order = {}, []
    for r in rows:
        k = (r.get("ts"), r.get("team"))
        if k not in groups:
            groups[k] = {"when": r.get("when", ""), "team": r.get("team", ""), "parts": []}
            order.append(k)
        verb = verbs.get(r.get("action", ""), (r.get("action") or "").lower())
        groups[k]["parts"].append(f"{verb} {r.get('player', '')}")
    out = ""
    for k in order[:10]:
        g = groups[k]
        out += f'<div class="act">{_e(g["when"])} &middot; <b>{_e(g["team"])}</b> {_e(", ".join(g["parts"]))}</div>'
    return out


def _waivers(w: dict) -> str:
    if not w:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    out = ""
    if w["adds"]:
        out += '<div class="grp">PICK UP</div>'
        for a in w["adds"]:
            extra = ""
            if a.get("need"):
                extra += ' &middot; <span class="f-go">fills a need</span>'
            if a.get("hot"):
                extra += f' &middot; <span class="f-quest">{a["hot"]:,} adds in 48h</span>'
            if a.get("dropped_by"):
                extra += f' &middot; dropped by {_e(a["dropped_by"])}'
            drop = f'<small>drop {_e(a["drop"])}</small>' if a.get("drop") else ""
            out += (f'<div class="row"><span class="chip {a["verdict"]}">{a["verdict"].upper()}</span>'
                    f'<div class="who"><div class="nm">{_e(a["name"])}</div>{_meta(a, extra)}<div class="reason">{_e(a["reason"])}</div></div>'
                    f'<div class="num">{_pts(a["proj"])}{drop}</div></div>')
    else:
        out += '<p class="empty">Nobody on the wire beats what you have. Check again after waivers clear.</p>'
    if w["hot"]:
        out += '<div class="grp">HOT EVERYWHERE, UNCLAIMED HERE</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(h["name"])}</div>{_meta(h)}</div>'
            f'<div class="num">{h["count"]:,}<small>adds in 48h</small></div></div>' for h in w["hot"])
    if w["just_dropped"]:
        out += '<div class="grp">JUST DROPPED IN YOUR LEAGUE</div>'
        for d in w["just_dropped"]:
            by = f' &middot; by {_e(d["dropped_by"])}, {_e(d["when"])}'
            out += (f'<div class="row"><div class="who"><div class="nm">{_e(d["name"])}</div>{_meta(d, by)}</div>'
                    f'<div class="num">{_pts(d["proj"])}{_last(d.get("ppg_2025"))}</div></div>')
    if w["drops"]:
        out += '<div class="grp">IF YOU NEED A ROSTER SPOT</div>' + "".join(
            f'<div class="row"><div class="who"><div class="nm">{_e(d["name"])}</div>{_meta(d)}<div class="reason">{_e(d["reason"])}</div></div>'
            f'<div class="num">{_pts(d["proj"])}</div></div>' for d in w["drops"])
    if w["activity"]:
        out += '<div class="grp">LEAGUE ACTIVITY</div>' + _activity(w["activity"])
    return out


def _status(espn: dict) -> str:
    if not espn or espn.get("ok"):
        note = (espn or {}).get("reason", "")
        return f'<div class="status"><p>{_e(note)}</p></div>' if note else ""
    return (f'<div class="status"><p>ESPN isn\'t connected, so your roster is missing.</p>'
            f'<p class="why">{_e(espn.get("reason") or "No reason recorded.")}</p></div>')


def build(data: dict) -> str:
    week = data.get("week", "?")
    team = data.get("team_name") or "Your team"
    roster = data.get("roster", [])
    opt = data.get("optimizer", {}) or {}
    opp_total = sum(p["projected"] for p in data.get("opponent_roster", []) if p.get("starting") and isinstance(p.get("projected"), (int, float)))

    lg = data.get("league") or {}
    wk_line = f"Week {week}" + (f" \u00b7 {data['record']}" if data.get("record") else "")
    standing = ""
    if lg.get("standing") and lg.get("team_count"):
        bits = []
        if isinstance(lg.get("playoff_pct"), (int, float)):
            bits.append(f"{lg['playoff_pct']:.0f}% playoff odds")
        if lg.get("streak"):
            bits.append(f"{lg['streak']} streak")
        sub = _e(" \u00b7 ".join(bits)) or "\u00a0"
        standing = (f'<div class="stat wide"><div class="l">Standing</div><div class="v">{_ordinal(lg["standing"])} of {lg["team_count"]}</div>'
                    f'<div class="s">{sub}</div></div>')


    if opt.get("lineup"):
        n = len(opt["swaps"])
        go = (f'<div class="stat go"><div class="l">Optimizer</div><div class="v">+{opt["gain"]}</div>'
              f'<div class="s">{n} swap{"s" if n != 1 else ""} available</div></div>') if n else (
              f'<div class="stat go"><div class="l">Optimizer</div><div class="v">Optimal</div><div class="s">no changes needed</div></div>')
        proj = (f'<div class="stat"><div class="l">Projected</div><div class="v">{opt["optimal_total"]}</div>'
                f'<div class="s">{("opp " + f"{opp_total:.1f}") if opp_total else "this week"}</div></div>')
        stats = f'<div class="stats">{go}{proj}{standing}</div>'
    else:
        stats = f'<div class="stats">{standing}</div>' if standing else ""

    adds = "".join(
        f'<div class="row"><div class="who"><div class="nm">{_e(a["name"])}</div>{_meta(a)}</div>'
        f'<div class="num">{a.get("count", 0):,}<small>adds</small></div></div>' for a in data.get("trending_adds", [])) or '<p class="empty">No trending data.</p>'
    news = "".join(
        f'<div class="row"><a href="{_e(n.get("link", "#"))}">{_e(n.get("headline", ""))}</a>'
        f'<div class="m">{_e(_blurb(n.get("description")))}</div></div>' for n in data.get("news", [])) or '<p class="empty">No headlines.</p>'

    w = data.get("waivers")
    if w:
        prio = w.get("priority", {}).get("text", "")
        sub = prio.replace("Waiver priority", "priority") if prio else "unclaimed in your league"
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Waiver wire</h2><span class="m">{sub}</span></div>{_waivers(w)}</section>'
    else:
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Most added</h2><span class="m">all leagues, 48h</span></div>{adds}</section>'

    opp = data.get("opponent_name")
    opp_html = f'<div class="opp"><div class="wk">vs</div><div class="cond">{_e(opp)}</div></div>' if opp else ""

    navitems = [("#lineup", "lineup", "Lineup"), ("#waiver", "waiver", "Waivers"), ("#rank", "rank", "Rankings"),
                ("#trades", "trades", "Trades"), ("#news", "news", "News")]
    bottom = "".join(f'<li><a href="{h}">{ICONS[i]}{l}</a></li>' for h, i, l in navitems) + f'<li><a href="#settings" data-gear>{ICONS["gear"]}Settings</a></li>'
    top = "".join(f'<li><a href="{h}">{l}</a></li>' for h, i, l in navitems) + '<li><a href="#settings" data-gear>Settings</a></li>'

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#EEF2F7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D1626" media="(prefers-color-scheme: dark)">
<title>Week {week} &mdash; {_e(team)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@500;600&display=swap" rel="stylesheet">
<script>{HEAD_JS}</script>
<style>{CSS}</style>
</head><body><div class="wrap">

<header><div><div class="wk">{_e(wk_line)}</div><h1>{_e(team)}</h1></div>
{opp_html}<button class="gear" data-gear aria-label="Settings">{ICONS["gear"].replace('<svg', '<svg width="18" height="18" style="stroke:currentColor;fill:none;stroke-width:1.6"')}</button></header>

<nav class="top" aria-label="Sections"><ul>{top}</ul></nav>

<section class="sheet" id="settings"><div class="hd"><h2>Settings</h2><span class="m">saved on this device</span></div>
<div class="setrow"><label>Theme</label><div class="seg" data-set="theme"><button data-v="auto">Auto</button><button data-v="light">Light</button><button data-v="dark">Dark</button></div></div>
<div class="setrow" style="padding-bottom:14px"><label>Text size</label><div class="seg" data-set="size"><button data-v="small">Small</button><button data-v="default">Default</button><button data-v="large">Large</button><button data-v="xl">XL</button></div></div></section>

{_status(data.get("espn"))}
{stats}

<section class="sheet" id="lineup"><div class="hd"><h2>Start / sit</h2><span class="m">your lineup</span></div>
{_alerts(roster)}{_lineup(roster, opt)}
{('<div class="grp">RECOMMENDED SWAPS</div>' + _swaps(opt)) if opt.get("lineup") else ""}</section>

{waiver_html}

<section class="sheet" id="rank"><div class="hd"><h2>Rankings</h2><span class="m">PPR &middot; this week</span></div>{_rankings(data.get("rankings", {}))}</section>

<section class="sheet" id="trades"><div class="hd"><h2>Trade targets</h2></div>{_trades(data.get("trades", {}))}</section>

<section class="sheet news" id="news"><div class="hd"><h2>Headlines</h2></div>{news}</section>

<p class="foot">Updated {_e(data.get("generated", ""))}. Rankings blend this week's projection (65%) with 2025 points per game (35%). Tiers break on a 12% drop.</p>
</div>
<nav class="bottom" aria-label="Sections"><ul>{bottom}</ul></nav>
<script>{JS}</script></body></html>"""


def timestamp() -> str:
    """Central time: the workflow schedule is written for it, and Actions runs in UTC."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Chicago"))
    except Exception:  # no tz database on this machine
        now = datetime.now()
    return now.strftime("%a %b %d, %-I:%M %p %Z").strip()
