"""Renders the static dashboard.

Design: deep navy surfaces, one saturated green carrying every "go" signal,
blunt START / SIT / CONSIDER verdicts, tier bands in the rankings, bottom
tab bar on phones and top pills on wider screens. Light mode keeps the same
layout on a pale navy-tinted paper.
"""

from __future__ import annotations
import html
from datetime import datetime
from . import assess, sources

DARK = ("--paper:#020617;--shell:#0f172a;--sheet:#0f172a;--well:#020617;--fill:#1e293b;--fill2:#334155;--line:#1e293b;"
        "--ink:#ffffff;--ink2:#e2e8f0;--muted:#94a3b8;--dim:#64748b;"
        "--accent:#3b82f6;--btn:#2563eb;--accent-ink:#60a5fa;--accent-soft:rgba(37,99,235,.16);--accent-line:rgba(59,130,246,.32);"
        "--green:#34d399;--green-soft:rgba(16,185,129,.12);--green-line:rgba(16,185,129,.28);--green-ink:#34d399;--on-green:#04210f;"
        "--out:#fb7185;--out-soft:rgba(244,63,94,.12);--out-line:rgba(244,63,94,.3);"
        "--quest:#fbbf24;--quest-soft:rgba(245,158,11,.12);--quest-line:rgba(245,158,11,.3);"
        "--blue:#60a5fa;--on-blue:#061a33;--amber:#fbbf24;--on-amber:#2e2000;"
        "--glass:rgba(15,23,42,.78);--ring-track:#1e293b;--shadow:0 18px 30px -12px rgba(0,0,0,.55);--card-shadow:none;"
        "--glow:0 10px 18px -4px rgba(37,99,235,.35)")
LIGHT = ("--paper:#f2f2f7;--shell:#ffffff;--sheet:#ffffff;--well:#f2f2f7;--fill:#eceef3;--fill2:#d9dde5;--line:#e6e8ee;"
         "--ink:#0b1220;--ink2:#334155;--muted:#64748b;--dim:#94a3b8;"
         "--accent:#2563eb;--btn:#2563eb;--accent-ink:#2563eb;--accent-soft:rgba(37,99,235,.10);--accent-line:rgba(37,99,235,.28);"
         "--green:#16a34a;--green-soft:#e7f7ee;--green-line:#a7e3c0;--green-ink:#0f7a3a;--on-green:#ffffff;"
         "--out:#e11d48;--out-soft:#fde8ec;--out-line:#f6b5c1;"
         "--quest:#b45309;--quest-soft:#fff4dc;--quest-line:#f2d59a;"
         "--blue:#2563eb;--on-blue:#ffffff;--amber:#d97706;--on-amber:#2e2000;"
         "--glass:rgba(255,255,255,.80);--ring-track:#e6e8ee;--shadow:0 14px 30px -14px rgba(15,23,42,.28);--card-shadow:0 8px 24px -14px rgba(15,23,42,.18);"
         "--glow:0 10px 18px -6px rgba(37,99,235,.38)")

CSS = """
:root{__DARK__;color-scheme:dark}
:root[data-theme=light]{__LIGHT__;color-scheme:light}
@media(prefers-color-scheme:light){:root[data-theme=auto]{__LIGHT__;color-scheme:light}}
html{font-size:16px;scroll-behavior:smooth;scroll-padding-top:8px}
html[data-size=small]{font-size:14px} html[data-size=large]{font-size:18px} html[data-size=xl]{font-size:20px}
*{box-sizing:border-box}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto} *{transition:none!important;animation:none!important}}
body{margin:0;background:var(--paper);color:var(--ink2);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
     font-size:.9375rem;line-height:1.45;-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%;-webkit-tap-highlight-color:transparent;transition:background .2s,color .2s}
h1,h2,h3,.nm,.stat .v,.gt,.ring-c b{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif}
a{color:var(--accent-ink)}
button{font:inherit;color:inherit;cursor:pointer}
.wrap{max-width:520px;margin:0 auto;padding:max(18px,env(safe-area-inset-top)) 16px 124px}
/* page header: eyebrow, heavy title, round action button */
header{display:flex;align-items:flex-start;gap:12px;padding:4px 2px 16px}
header>div{min-width:0}
header .grow{flex:1}
.eb{font-size:.6875rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:var(--accent-ink)}
header h1{font-size:1.75rem;font-weight:900;line-height:1.08;margin:4px 0 0;letter-spacing:-.025em;color:var(--ink);text-wrap:balance}
header .sub{font-size:.8125rem;color:var(--muted);margin-top:5px;overflow-wrap:anywhere}
header .sub b{color:var(--ink2);font-weight:700}
.gear{width:42px;height:42px;border-radius:15px;border:1px solid var(--fill2);background:var(--fill);color:var(--ink2);
      display:inline-grid;place-items:center;flex:none;transition:transform .12s,background .15s}
.gear:active{transform:scale(.94)}
/* bubble cards */
.stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.stat{background:var(--sheet);border:1px solid var(--line);border-radius:22px;padding:15px 17px;box-shadow:var(--card-shadow)}
.stat.wide{grid-column:1/-1}
.stat.go{background:var(--green-soft);border-color:var(--green-line)}
.stat .l{font-size:.6875rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)} .stat.go .l{color:var(--green-ink)}
.stat .v{font-size:1.75rem;font-weight:900;line-height:1.05;margin:5px 0 3px;letter-spacing:-.025em;color:var(--ink)}
.stat.go .v{color:var(--green)}
.stat .s{font-size:.75rem;color:var(--muted)} .stat.go .s{color:var(--green-ink)}
.sheet{background:var(--sheet);border:1px solid var(--line);border-radius:26px;margin-bottom:16px;overflow:hidden;box-shadow:var(--card-shadow)}
.hero{background:radial-gradient(120% 70% at 0% 0%,var(--accent-soft),transparent 62%),var(--sheet)}
.hd{display:flex;align-items:baseline;gap:10px;padding:18px 20px 8px}
.hd h2{font-size:1.1875rem;font-weight:900;margin:0;white-space:nowrap;letter-spacing:-.02em;color:var(--ink)}
.hd .m{font-size:.6875rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.row{display:flex;align-items:center;gap:12px;padding:13px 20px;border-top:1px solid var(--line)}
.row.hi{background:var(--green-soft)}
.row .who{min-width:0;flex:1}
.nm{font-size:1rem;font-weight:700;line-height:1.2;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m{font-size:.75rem;color:var(--muted)}
.num{text-align:right;font-variant-numeric:tabular-nums;font-size:.9375rem;font-weight:800;color:var(--ink);white-space:nowrap;line-height:1.2}
.num .chip{display:block;width:max-content;margin:0 0 5px auto}
.pl>summary.row{padding:13px 16px;gap:10px}
.num small{display:block;font-size:.6875rem;font-weight:600;color:var(--muted)}
/* pill chips and tiles */
.chip{flex:none;display:inline-block;padding:4px 11px;border-radius:999px;font-size:.6875rem;font-weight:800;letter-spacing:.05em;white-space:nowrap;transition:transform .12s}
.chip.start{background:var(--green);color:var(--on-green)}
.chip.sit{background:var(--out-soft);color:var(--out);border:1px solid var(--out-line)}
.chip.consider{background:var(--quest-soft);color:var(--quest);border:1px solid var(--quest-line)}
.chip.slot{min-width:48px;height:36px;padding:0 6px;border-radius:13px;display:inline-grid;place-items:center;letter-spacing:0;
           background:var(--accent-soft);color:var(--accent-ink);border:1px solid var(--accent-line)}
.chip.slot.bn{background:var(--fill);color:var(--muted);border-color:var(--fill2)}
.chip.stream{background:var(--blue);color:var(--on-blue)}
.chip.fill,.chip.k-fix{background:var(--out-soft);color:var(--out);border:1px solid var(--out-line)}
.chip.k-swap{background:var(--green);color:var(--on-green)}
.chip.k-pickup{background:var(--btn);color:#fff;box-shadow:var(--glow)}
.chip.k-watch{background:var(--quest-soft);color:var(--quest);border:1px solid var(--quest-line)}
.chip.bench{background:var(--quest-soft);color:var(--quest);border:1px solid var(--quest-line)}
.chip.stash{background:transparent;color:var(--accent-ink);border:1px solid var(--accent-line)}
/* confidence line */
.gauge{display:flex;align-items:center;gap:18px;padding:6px 20px 2px}
.gauge .big{font-size:4rem;font-weight:900;line-height:.9;letter-spacing:-.045em;flex:none}
.gauge .big small{font-size:1.5rem;font-weight:800;color:var(--muted);margin-left:2px;letter-spacing:0}
.g-hi{color:var(--green)} .g-mid{color:var(--quest)} .g-lo{color:var(--out)}
.meter{position:relative;height:12px;margin:16px 20px 4px;border-radius:999px;background:var(--ring-track)}
.meter span{display:block;height:100%;border-radius:999px;background:currentColor;box-shadow:0 0 16px -2px currentColor;transition:width .9s cubic-bezier(.2,.8,.2,1)}
.meter i{position:absolute;top:-4px;bottom:-4px;left:50%;width:3px;margin-left:-1px;border-radius:2px;background:var(--ink2);opacity:.55}
.hero-t{min-width:0}
.hero-t .gt{font-size:1.375rem;font-weight:900;line-height:1.1;letter-spacing:-.02em}
.hero-t .gs{font-size:.8125rem;color:var(--muted);margin-top:5px;overflow-wrap:anywhere}
.after{margin:12px 20px 0;padding:11px 14px;border-radius:18px;background:var(--well);border:1px solid var(--line);font-size:.8125rem;color:var(--muted)} .after b{color:var(--green);font-weight:800}
.qrisk{margin:8px 20px 14px;font-size:.8125rem;color:var(--muted)} .qrisk p{margin:5px 0} .qrisk b{color:var(--quest);font-weight:800}
.hero .after:last-of-type{margin-bottom:14px}
/* player cards */
.pl{border-top:1px solid var(--line)}
.pl>summary{list-style:none;cursor:pointer;border-top:0;transition:background .15s}
.pl>summary::-webkit-details-marker{display:none}
.pl>summary:active{background:var(--fill)}
.deep{margin:0 14px 14px;padding:13px 16px;border-radius:20px;background:var(--well);border:1px solid var(--line);font-size:.8125rem;color:var(--muted)}
.deep .ln{margin-top:6px} .deep .ln:first-child{margin-top:0} .deep .ln b{color:var(--ink);font-weight:800} .deep a{color:var(--accent-ink)}
.sig{list-style:none;margin:8px 0 0;padding:0}
.sig li{display:flex;gap:9px;padding:3px 0;color:var(--ink2)}
.sig .sp{flex:none;width:15px;text-align:center;font-weight:900}
.sg-p{color:var(--green)} .sg-m{color:var(--out)} .sg-i{color:var(--muted)}
.use{font-size:.6875rem;color:var(--muted);margin-top:3px}
.nm.free{white-space:normal;overflow:visible}
.reason{font-size:.75rem;color:var(--muted);margin-top:3px}
.reason a,.row .m a{color:var(--accent-ink);text-decoration:none} .reason a:hover{text-decoration:underline}
.num small.ol-s{color:var(--green)} .num small.ol-w{color:var(--quest)} .num small.ol-x{color:var(--out)}
.act{padding:8px 20px;font-size:.8125rem;border-top:1px solid var(--line);color:var(--muted)} .act b{font-weight:700;color:var(--ink)}
.f-out{color:var(--out)} .f-quest{color:var(--quest)} .f-go{color:var(--green)}
.grp{padding:14px 20px 6px;font-size:.6875rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);border-top:1px solid var(--line)}
/* segmented pills for positions */
.pos{display:flex;gap:6px;padding:10px 16px 8px}
.pos button{flex:1;text-align:center;padding:8px 0;border-radius:999px;font-size:.75rem;font-weight:800;color:var(--muted);
   background:var(--fill);border:1px solid var(--fill2);transition:background .15s,color .15s,transform .12s}
.pos button:active{transform:scale(.95)}
.pos button[aria-selected=true]{background:var(--btn);color:#fff;border-color:var(--btn);box-shadow:var(--glow)}
.panel{display:none} .panel[data-active]{display:block}
.tier{display:block;width:max-content;margin:10px 20px 4px;padding:4px 13px;border-radius:999px;font-size:.6875rem;font-weight:900;letter-spacing:.08em}
.tier.t1{background:var(--green);color:var(--on-green)} .tier.t2{background:var(--blue);color:var(--on-blue)}
.tier.t3{background:var(--amber);color:var(--on-amber)} .tier.t4{background:var(--fill);color:var(--muted)}
.rk{width:24px;color:var(--dim);font-size:.8125rem;font-weight:700;font-variant-numeric:tabular-nums;flex:none}
.row.me{background:var(--green-soft)}
.swap{display:grid;grid-template-columns:1fr auto 1fr auto;gap:8px;align-items:center;padding:12px 20px;border-top:1px solid var(--line)}
.swap .arrow{color:var(--muted);font-size:.75rem}
.swap .gain{font-variant-numeric:tabular-nums;color:var(--green);font-weight:800;white-space:nowrap;font-size:.875rem}
.alert{margin:6px 14px;padding:11px 15px;border-radius:18px;background:var(--out-soft);border:1px solid var(--out-line)}
.alert.warn{background:var(--quest-soft);border-color:var(--quest-line)}
.alert .who{font-size:1rem;font-weight:800;color:var(--ink)} .alert .why{font-size:.8125rem;color:var(--muted)}
.status{border:1px solid var(--quest-line);background:var(--quest-soft);border-radius:20px;padding:12px 16px;margin-bottom:16px;font-size:.875rem}
.status p{margin:0} .status .why{color:var(--muted);font-size:.8125rem;margin-top:3px}
.news .row{display:block} .news a{color:var(--ink);text-decoration:none;font-size:1rem;font-weight:700}
.news a:hover{color:var(--accent-ink)}
.empty{color:var(--muted);font-size:.875rem;padding:8px 20px 16px;margin:0}
.foot{color:var(--dim);font-size:.75rem;padding:4px 6px 0}
nav.top{display:none}
/* floating glass tab bar */
nav.bottom{position:fixed;left:0;right:0;bottom:0;z-index:20;padding:0 14px max(14px,env(safe-area-inset-bottom));pointer-events:none}
nav.bottom ul{pointer-events:auto;list-style:none;margin:0 auto;padding:6px;display:flex;gap:2px;max-width:492px;background:var(--glass);
  -webkit-backdrop-filter:saturate(180%) blur(22px);backdrop-filter:saturate(180%) blur(22px);border:1px solid var(--line);border-radius:30px;box-shadow:var(--shadow)}
nav.bottom li{flex:1;min-width:0}
nav.bottom a{display:flex;flex-direction:column;align-items:center;gap:3px;padding:8px 2px 7px;border-radius:24px;text-decoration:none;color:var(--muted);
  font-size:.625rem;font-weight:700;transition:background .15s,color .15s,transform .12s}
nav.bottom a svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
nav.bottom a.on{background:var(--accent-soft);color:var(--accent-ink)}
nav.bottom a:active{transform:scale(.94)}
#settings{display:none} #settings[data-open]{display:block}
.setrow{display:grid;grid-template-columns:84px 1fr;gap:12px;align-items:center;padding:9px 20px}
.setrow label{font-size:.875rem;font-weight:600;color:var(--muted)}
.seg{display:flex;gap:3px;background:var(--well);border:1px solid var(--line);border-radius:15px;padding:3px}
.seg button{flex:1;border:0;background:transparent;border-radius:12px;padding:7px 0;font-size:.8125rem;font-weight:700;color:var(--muted);min-height:34px;transition:background .15s,color .15s}
.seg button[aria-pressed=true]{background:var(--fill);color:var(--ink);box-shadow:inset 0 0 0 1px var(--fill2)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media(min-width:640px){.wrap{padding-top:32px}}
""".replace("__DARK__", DARK).replace("__LIGHT__", LIGHT)

HEAD_JS = """(function(){try{var t=localStorage.getItem('ff-theme');if(t&&t!=='dark')document.documentElement.setAttribute('data-theme',t);
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
  wire('theme','ff-theme','data-theme','dark');wire('size','ff-size','data-size','default');
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
    "check": '<svg viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2zM9 14l2 2 4-4"/></svg>',
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


def _lineup(roster: list[dict], opt: dict, cards: dict = None, open_all: bool = False, rw: list = None) -> str:
    cards = cards or {}
    starters = [p for p in roster if p.get("starting")]
    bench = sorted((p for p in roster if not p.get("starting")), key=lambda p: p.get("slot") == "IR")  # IR last
    v = _verdicts(roster, opt)

    def row(p):
        verdict, note = v.get(p["name"], (None, ""))
        # Bench rows only get a chip when there's something to do; red belongs on a starter who should sit.
        show_chip = verdict and (p.get("starting") or verdict != "sit")
        chip = f'<span class="chip {verdict}">{verdict.upper()}</span>' if show_chip else ""
        extra = f' &middot; <span class="f-go">{_e(note)}</span>' if note and verdict == "start" else (
                f' &middot; <span class="{"f-quest" if verdict == "consider" else "f-out"}">{_e(note)}</span>' if note else "")
        hi = " hi" if (verdict == "start" and not p.get("starting")) else ""
        raw_slot = p.get("slot") or "BE"
        slot_txt = {"RB/WR/TE": "FLEX", "BE": "BN"}.get(raw_slot, raw_slot)
        slot = f'<span class="chip slot{" bn" if raw_slot in ("BE", "IR") else ""}">{_e(slot_txt)}</span>'
        c = cards.get(p["name"])
        small = f'<small class="ol ol-{_OL.get(c["label"], "o")}">{c["outlook"]} outlook</small>' if c else ""
        inner = (f'{slot}<div class="who"><div class="nm">{_e(p["name"])}</div>{_meta(p, extra)}{_use(p)}</div>'
                 f'<div class="num">{chip}<span class="pts">{_pts(p.get("projected"))}</span>{small}</div>')
        if not c:
            return f'<div class="row{hi}">{inner}</div>'
        return (f'<details class="pl"{" open" if open_all else ""}><summary class="row{hi}">{inner}</summary>'
                f'{_deep(c)}</details>')

    if not roster:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    return (_role_watch(rw) + '<div class="grp">STARTING</div>' + "".join(row(p) for p in starters) +
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


_OL = {"Strong": "s", "Solid": "o", "Shaky": "w", "Weak": "x", "Not playing": "x"}
_TRENDW = {"up": "usage rising", "down": "usage falling", "flat": "usage steady"}
_SG = {"+": ("p", "+"), "-": ("m", "\u2212"), "i": ("i", "\u2022")}
_DAYS = {"Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday", "Mon": "Monday", "Bye": "Bye week"}


def _use(p: dict) -> str:
    """Quiet lines under a name: role and usage plus any role boost, then each source's projection."""
    t = (p.get("usage") or {}).get("text", "")
    boost = f' &middot; <span class="f-go">+{p["boost"]:.1f} role</span>' if p.get("boost") else ""
    out = f'<div class="use">{_e(t)}{boost}</div>' if t else ""
    src = sources.line(p)
    if src:
        cls = ' class="f-quest"' if p.get("split") else ""
        out += f'<div class="use"><span{cls}>{_e(src)}</span></div>'
    return out


def _deep(c: dict) -> str:
    """The expandable player card: outlook, last week, recent baseline, and why."""
    parts = [f'<div class="ln"><b>{c["outlook"]}</b> outlook ({_e(c["label"].lower())}, {_e(_TRENDW[c["trend"]])}) &middot; '
             f'expected <b>{c["expected"]:.1f}</b> vs {c["bench"]:.1f} for the average {_e(c["position"])} starter</div>']
    src = c.get("sources") or {}
    if len(src) >= 2:
        s_txt = " &middot; ".join(f"{_e(k)} {v:.1f}" for k, v in src.items())
        blend = c["proj"] - (c.get("boost") or 0.0)
        extra = f' + {c["boost"]:.1f} role = <b>{c["proj"]:.1f}</b>' if c.get("boost") else ""
        split = ' &middot; <span class="f-quest">sources split</span>' if c.get("split") else ""
        parts.append(f'<div class="ln">{s_txt} &rarr; average {blend:.1f}{extra}{split}</div>')
    elif isinstance(c.get("proj_espn"), (int, float)) and abs(c["proj"] - c["proj_espn"]) >= 0.05:
        parts.append(f'<div class="ln">ESPN {c["proj_espn"]:.1f} &rarr; {c["proj"]:.1f} with the role change</div>')
    if c.get("usage_pts") is not None:
        parts.append(f'<div class="ln">Usage: his recent targets, carries and throws were worth '
                     f'{c["usage_pts"]:.1f} a game (context, not in the number)</div>')
    if c.get("range"):
        up = ""
        if not c.get("starting") and c.get("boom") and c["boom"] >= assess.UPSIDE_AT:
            up = (' Higher upside than a typical bench player: about 1 in 7 like him beat their projection by 8+, '
                  'against 1 in 11 overall. A weak signal that mostly reflects a higher projection.')
        parts.append(f'<div class="ln">Typical range <b>{c["range"][0]}&ndash;{c["range"][1]}</b> if he plays '
                     f'(middle 80% of past outcomes in this league).{up}</div>')
    if c.get("last"):
        parts.append(f'<div class="ln"><b>{_e(c["last"])}</b></div>')
    if c.get("avg"):
        parts.append(f'<div class="ln">{_e(c["avg"])}</div>')
    sigs = ""
    for sign, text in c.get("signals", []):
        cls, ch = _SG[sign]
        sigs += f'<li><span class="sp sg-{cls}">{ch}</span><span>{_e(text)}</span></li>'
    if sigs:
        parts.append(f'<ul class="sig">{sigs}</ul>')
    n = c.get("news")
    if n and n.get("link"):
        parts.append(f'<div class="ln"><a href="{_e(n["link"])}">{_e(n["headline"])}</a></div>')
    return '<div class="deep">' + "".join(parts) + "</div>"


def _role_watch(rw: list) -> str:
    """Who gains or loses touches this week, yours first."""
    if not rw:
        return ""
    rows = ""
    for e in rw:
        who = " &middot; yours" if e.get("mine") else " &middot; on the wire"
        lines = []
        if e.get("boost"):
            lines.append(f'+{e["boost"]:.1f} pts expected: {_e(e.get("why", ""))}')
        if e.get("qb_note"):
            lines.append(_e(e["qb_note"]))
        n = e.get("news")
        if n:
            lines.append(f'<a href="{_e(n.get("link", "#"))}">{_e(n.get("headline", ""))}</a>')
        num = f'<div class="num f-go">+{e["boost"]:.1f}</div>' if e.get("boost") else ""
        rows += (f'<div class="row"><div class="who"><div class="nm">{_e(e["name"])}</div>'
                 f'<div class="m">{_e(e.get("position", ""))} {_e(e.get("team", ""))}{who}</div>'
                 f'<div class="reason">{" &middot; ".join(lines)}</div></div>{num}</div>')
    return '<div class="grp">ROLE WATCH: WHO GETS THE BALL</div>' + rows


def _hero(a: dict, opp_name: str) -> str:
    if not a or a.get("score") is None:
        return ""
    sc = a["score"]
    cls = "g-hi" if sc >= 55 else "g-mid" if sc >= 45 else "g-lo"
    vs = f" to beat {_e(opp_name)}" if opp_name else ""
    head = (f'<div class="gauge {cls}"><div class="big">{sc}<small>%</small></div><div class="hero-t">'
            f'<div class="eb">Win chance</div><div class="gt">{_e(a["label"])}</div>'
            f'<div class="gs">{a["mine"]:.1f} vs {a["opp"]:.1f} projected{vs}</div></div></div>'
            f'<div class="meter {cls}"><span style="width:{max(2, min(100, sc))}%"></span><i></i></div>')
    after = ""
    o = a.get("optimal") or {}
    if o.get("win") is not None and o["expected"] >= a["mine"] + 0.5:
        after = (f'<p class="after">With the lineup changes below: <b>{round(100 * o["win"])}%</b> '
                 f'({o["expected"]:.1f} projected)</p>')
    else:
        after = '<p class="after">Chance your lineup outscores this week\'s opponent. 50% is a coin flip.</p>'

    lines = assess.risk_lines(a)
    if lines:
        after += '<div class="qrisk">' + "".join(f'<p><b>{_e(label)}</b>: {_e(text)}</p>' for label, text in lines) + "</div>"

    acts = ""
    for x in a.get("actions", []):
        gain = f'<div class="num f-go">+{x["gain"]:.1f}</div>' if x["gain"] >= 0.1 else ""
        acts += (f'<div class="row"><span class="chip k-{x["kind"]}">{x["kind"].upper()}</span><div class="who">'
                 f'<div class="nm free">{_e(x["title"])}</div><div class="reason">{_e(x["detail"])}</div></div>{gain}</div>')
    if not acts:
        acts = '<p class="empty">Nothing to do. Your lineup is optimal and no pickup improves it.</p>'

    days = ""
    for d in a.get("days", []):
        names = ", ".join(d["names"])
        if d["day"] == "Bye":
            days += (f'<div class="row"><div class="who"><div class="nm">No game</div>'
                     f'<div class="m">{_e(names)} {"has" if d["n"] == 1 else "have"} a bye</div></div>'
                     f'<div class="num f-out">0</div></div>')
            continue
        k = "f-go" if d["score"] >= 55 else "f-quest" if d["score"] >= 40 else "f-out"
        s_ = "" if d["n"] == 1 else "s"
        days += (f'<div class="row"><div class="who"><div class="nm">{_DAYS.get(d["day"], d["day"])}</div>'
                 f'<div class="m">{d["n"]} starter{s_} &middot; {d["expected"]:.1f} projected &middot; {_e(names)}</div></div>'
                 f'<div class="num {k}">{d["score"]}%<small>{d["vs_typical"]:+.1f} vs avg team</small></div></div>')
    days = ('<div class="grp">BY DAY</div>' + days) if days else ""
    return (f'<section class="sheet hero" id="checkup"><div class="hd"><h2>{_e(a["title"])}</h2>'
            f'<span class="m">Week {_e(a["week"])}</span></div>'
            f'{head}{after}<div class="grp">DO THIS</div>{acts}{days}</section>')


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
                    f'<div class="who"><div class="nm">{_e(a["name"])}</div>{_meta(a, extra)}{_use(a)}<div class="reason">{_e(a["reason"])}</div></div>'
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
        proj = (f'<div class="stat"><div class="l">Best lineup</div><div class="v">{opt["optimal_total"]}</div>'
                f'<div class="s">{("opp " + f"{opp_total:.1f}") if opp_total else "this week"}</div></div>')
        stats = f'<div class="stats">{go}{proj}{standing}</div>'
    else:
        stats = f'<div class="stats">{standing}</div>' if standing else ""

    adds = "".join(
        f'<div class="row"><div class="who"><div class="nm">{_e(a["name"])}</div>{_meta(a)}</div>'
        f'<div class="num">{a.get("count", 0):,}<small>adds</small></div></div>' for a in data.get("trending_adds", [])) or '<p class="empty">No trending data.</p>'
    news = "".join(
        f'<div class="row"><a href="{_e(n.get("link", "#"))}">{_e(n.get("headline", ""))}</a>'
        f'<div class="m">{_e(_blurb(n.get("description")))}</div></div>' for n in data.get("news", [])[:15]) or '<p class="empty">No headlines.</p>'

    w = data.get("waivers")
    if w:
        prio = w.get("priority", {}).get("text", "")
        sub = prio.replace("Waiver priority", "priority") if prio else "unclaimed in your league"
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Waiver wire</h2><span class="m">{sub}</span></div>{_waivers(w)}</section>'
    else:
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Most added</h2><span class="m">all leagues, 48h</span></div>{adds}</section>'

    opp = data.get("opponent_name")
    opp_html = f'<div class="sub">vs <b>{_e(opp)}</b></div>' if opp else ""

    assessment = data.get("assessment") or {}
    cards = {c["name"]: c for c in assessment.get("cards", [])}
    hero_html = _hero(assessment, data.get("opponent_name", ""))
    navitems = ([("#checkup", "check", "Check-up")] if hero_html else []) + [
        ("#lineup", "lineup", "Lineup"), ("#waiver", "waiver", "Waivers"), ("#rank", "rank", "Rankings"),
        ("#trades", "trades", "Trades"), ("#news", "news", "News")]
    bottom = "".join(f'<li><a href="{h}">{ICONS[i]}{l}</a></li>' for h, i, l in navitems if i != "news") + f'<li><a href="#settings" data-gear>{ICONS["gear"]}Settings</a></li>'
    top = "".join(f'<li><a href="{h}">{l}</a></li>' for h, i, l in navitems) + '<li><a href="#settings" data-gear>Settings</a></li>'

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#020617">
<title>Week {week} &mdash; {_e(team)}</title>
<script>{HEAD_JS}</script>
<style>{CSS}</style>
</head><body><div class="wrap">

<header><div class="grow"><div class="eb">{_e(wk_line)}</div><h1>{_e(team)}</h1>{opp_html}</div>
<button class="gear" data-gear aria-label="Settings">{ICONS["gear"].replace('<svg', '<svg width="19" height="19" style="stroke:currentColor;fill:none;stroke-width:1.7"')}</button></header>

<nav class="top" aria-label="Sections"><ul>{top}</ul></nav>

<section class="sheet" id="settings"><div class="hd"><h2>Settings</h2><span class="m">saved on this device</span></div>
<div class="setrow"><label>Theme</label><div class="seg" data-set="theme"><button data-v="auto">Auto</button><button data-v="light">Light</button><button data-v="dark">Dark</button></div></div>
<div class="setrow" style="padding-bottom:14px"><label>Text size</label><div class="seg" data-set="size"><button data-v="small">Small</button><button data-v="default">Default</button><button data-v="large">Large</button><button data-v="xl">XL</button></div></div></section>

{_status(data.get("espn"))}
{hero_html}
{stats}

<section class="sheet" id="lineup"><div class="hd"><h2>Start / sit</h2><span class="m">your lineup</span></div>
{_alerts(roster)}{_lineup(roster, opt, cards, assessment.get("mode") == "gameday", data.get("role_watch"))}
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
