"""Renders the static dashboard.

Design system (all in the CSS below, no build step):
- Tokens: colour, radius (--r-*) and type (--t-*) CSS variables; dark first, light
  via data-theme. One green carries every "go" signal, amber = questionable /
  watch, red = sit / out, blue = navigation and live games.
- Hierarchy: the hero (win chance + "Do this") leads; start/sit rows show only
  slot, name, status, verdict and one number. Everything else about a player
  (sources, outlook, range, usage, news) lives in the expandable card.
- Secondary lists (role watch, hot adds, league activity, long rankings) sit in
  collapsed <details class="fold"> / <details class="more"> blocks.
- Phones: one column with a bottom tab bar. Desktop: hero across the top, two
  columns below, sticky top tabs.
Presentation only: every number comes from the data dict unchanged.
"""

from __future__ import annotations
import html
import re
from datetime import datetime
from . import assess, sources

DARK = ("--paper:#090d13;--shell:#111720;--sheet:#111720;--well:#0c1118;--fill:#1a222e;--fill2:#2a3545;--line:#1f2835;"
        "--ink:#f4f7fb;--ink2:#cdd5e1;--muted:#93a0b5;--dim:#6f7c92;"
        "--accent:#5b9bff;--btn:#2f6fed;--accent-ink:#7db1ff;--accent-soft:rgba(91,155,255,.13);--accent-line:rgba(91,155,255,.34);"
        "--green:#3ddc97;--green-soft:rgba(61,220,151,.11);--green-line:rgba(61,220,151,.32);--green-ink:#3ddc97;--on-green:#03210f;"
        "--out:#ff7b88;--out-soft:rgba(255,123,136,.12);--out-line:rgba(255,123,136,.34);"
        "--quest:#f6bd4a;--quest-soft:rgba(246,189,74,.12);--quest-line:rgba(246,189,74,.34);"
        "--blue:#7db1ff;--on-blue:#061a33;--amber:#f6bd4a;--on-amber:#2e2000;"
        "--glass:rgba(13,18,26,.86);--ring-track:#1f2835;--shadow:0 12px 28px -12px rgba(0,0,0,.6);--card-shadow:none")
LIGHT = ("--paper:#f3f5f8;--shell:#ffffff;--sheet:#ffffff;--well:#f5f7fa;--fill:#edf0f5;--fill2:#d5dbe5;--line:#e3e7ee;"
         "--ink:#0c1420;--ink2:#2c3a4d;--muted:#5b6880;--dim:#8291a8;"
         "--accent:#2563eb;--btn:#2563eb;--accent-ink:#1d55d0;--accent-soft:rgba(37,99,235,.09);--accent-line:rgba(37,99,235,.28);"
         "--green:#12864a;--green-soft:#e6f6ed;--green-line:#a4dcbc;--green-ink:#0d7040;--on-green:#ffffff;"
         "--out:#c81e3f;--out-soft:#fdeaee;--out-line:#f3b3bf;"
         "--quest:#9a5b06;--quest-soft:#fff3d9;--quest-line:#ecd092;"
         "--blue:#2563eb;--on-blue:#ffffff;--amber:#d97706;--on-amber:#2e2000;"
         "--glass:rgba(255,255,255,.9);--ring-track:#e3e7ee;--shadow:0 10px 26px -14px rgba(15,23,42,.3);--card-shadow:0 1px 2px rgba(15,23,42,.05)")

CSS = """
:root{__DARK__;color-scheme:dark;
  --r-lg:16px;--r-md:12px;--r-sm:8px;--r-xs:5px;--pad:16px;
  --t-xs:.6875rem;--t-sm:.8125rem;--t-md:.9375rem;--t-lg:1.0625rem;--t-xl:1.375rem}
:root[data-theme=light]{__LIGHT__;color-scheme:light}
@media(prefers-color-scheme:light){:root[data-theme=auto]{__LIGHT__;color-scheme:light}}
html{font-size:16px;scroll-behavior:smooth;scroll-padding-top:8px}
html[data-size=small]{font-size:14px} html[data-size=large]{font-size:18px} html[data-size=xl]{font-size:20px}
*{box-sizing:border-box}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto} *{transition:none!important;animation:none!important}}
body{margin:0;background:var(--paper);color:var(--ink2);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
     font-size:var(--t-md);line-height:1.45;-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%;-webkit-tap-highlight-color:transparent}
a{color:var(--accent-ink)}
button{font:inherit;color:inherit;cursor:pointer}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.wrap{max-width:560px;margin:0 auto;padding:max(14px,env(safe-area-inset-top)) 12px calc(84px + env(safe-area-inset-bottom))}
/* masthead */
header{display:flex;align-items:flex-start;gap:12px;padding:2px 4px 14px}
header>div{min-width:0}
header .grow{flex:1}
.eb{font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-ink)}
header h1{font-size:var(--t-xl);font-weight:800;line-height:1.15;margin:3px 0 0;letter-spacing:-.02em;color:var(--ink);text-wrap:balance}
header .sub{font-size:var(--t-sm);color:var(--muted);margin-top:4px;overflow-wrap:anywhere}
header .sub b{color:var(--ink2);font-weight:700}
.age{margin:3px 0 0;font-size:.75rem;color:var(--muted);font-variant-numeric:tabular-nums}
.age[data-stale=stale]{color:var(--quest)} .age[data-stale=old]{color:var(--out)}
.age b{font-weight:700;color:inherit}
.gear{width:40px;height:40px;border-radius:var(--r-md);border:1px solid var(--line);background:var(--sheet);color:var(--ink2);
      display:inline-grid;place-items:center;flex:none;transition:background .15s}
.gear:hover,.gear[aria-expanded=true]{background:var(--fill)}
/* cards */
.sheet{background:var(--sheet);border:1px solid var(--line);border-radius:var(--r-lg);margin-bottom:12px;overflow:hidden;box-shadow:var(--card-shadow)}
.hd{display:flex;align-items:center;gap:10px;padding:14px var(--pad) 12px}
.hd h2,.hd h3{font-size:var(--t-lg);font-weight:800;margin:0;letter-spacing:-.01em;color:var(--ink)}
.hd .m{flex:1;min-width:0;font-size:var(--t-xs);font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.xall{flex:none;border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:999px;padding:5px 11px;font-size:.75rem;font-weight:700;min-height:30px}
.xall:hover{color:var(--ink);background:var(--fill)}
.grp{display:flex;align-items:center;gap:8px;padding:11px var(--pad) 7px;font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);border-top:1px solid var(--line)}
.ct{display:inline-grid;place-items:center;min-width:19px;height:19px;padding:0 6px;border-radius:999px;background:var(--fill);color:var(--ink2);font-size:.6875rem;font-weight:800;letter-spacing:0;font-variant-numeric:tabular-nums}
/* rows */
.row{display:flex;align-items:center;gap:10px;padding:10px var(--pad);border-top:1px solid var(--line);min-height:54px}
.row .who{min-width:0;flex:1}
.nm{display:flex;align-items:center;gap:6px;min-width:0;font-size:var(--t-md);font-weight:650;line-height:1.25;color:var(--ink)}
.nt{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nm.free .nt{white-space:normal;overflow:visible}
.m{font-size:.75rem;color:var(--muted);margin-top:1px}
.reason{font-size:.75rem;color:var(--muted);margin-top:3px}
.reason a,.row .m a{color:var(--accent-ink);text-decoration:none} .reason a:hover{text-decoration:underline}
.num{flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:3px;text-align:right;font-variant-numeric:tabular-nums;font-size:var(--t-lg);font-weight:800;color:var(--ink);white-space:nowrap;line-height:1.1}
.num small{font-size:.6875rem;font-weight:600;color:var(--muted)}
.rk{width:22px;color:var(--dim);font-size:var(--t-sm);font-weight:700;font-variant-numeric:tabular-nums;flex:none}
.row.me{background:var(--green-soft)}
.row.hi{background:var(--green-soft);box-shadow:inset 3px 0 0 var(--green)}
.row.lo{background:var(--out-soft);box-shadow:inset 3px 0 0 var(--out)}
.row.qm{box-shadow:inset 3px 0 0 var(--quest)}
.f-out{color:var(--out)} .f-quest{color:var(--quest)} .f-go{color:var(--green-ink)} .f-live{color:var(--accent-ink);font-weight:700} .f-dim{color:var(--dim)}
/* chips: verdicts and action kinds. Solid = do it now, tinted = caution, outline = optional */
.chip{flex:none;display:inline-block;padding:3px 7px;border-radius:var(--r-xs);font-size:.625rem;font-weight:800;letter-spacing:.06em;line-height:1.2;white-space:nowrap;border:1px solid transparent}
.chip.start,.chip.k-swap{background:var(--green);color:var(--on-green)}
.chip.sit,.chip.fill,.chip.k-fix{background:var(--out-soft);color:var(--out);border-color:var(--out-line)}
.chip.consider,.chip.k-watch,.chip.bench{background:var(--quest-soft);color:var(--quest);border-color:var(--quest-line)}
.chip.stream,.chip.k-pickup{background:var(--btn);color:#fff}
.chip.stash{background:transparent;color:var(--accent-ink);border-color:var(--accent-line)}
.chip.live{background:var(--accent-soft);color:var(--accent-ink);border-color:var(--accent-line)}
.chip.final{background:var(--fill);color:var(--muted)}
.chip.slot{width:42px;height:32px;padding:0;border-radius:var(--r-sm);display:inline-grid;place-items:center;letter-spacing:.02em;font-size:.6875rem;
           background:var(--fill);color:var(--ink);border-color:var(--fill2)}
.chip.slot.bn{background:transparent;color:var(--dim);border-color:var(--line)}
.todo .chip,.adds .chip{min-width:56px;text-align:center}
.adds .row{align-items:flex-start} .adds .chip{margin-top:2px}
.reason b{color:var(--ink2);font-weight:700}
/* injury tags next to a name */
.tag{flex:none;display:inline-block;padding:1px 5px;border-radius:4px;font-size:.625rem;font-weight:800;letter-spacing:.04em;line-height:1.35;border:1px solid transparent}
.tag.q{background:var(--quest-soft);color:var(--quest);border-color:var(--quest-line)}
.tag.o{background:var(--out-soft);color:var(--out);border-color:var(--out-line)}
/* hero: win chance, then what to do */
.gauge{display:flex;align-items:center;gap:16px;padding:2px var(--pad) 0}
.gauge .big{font-size:3.75rem;font-weight:900;line-height:.9;letter-spacing:-.045em;flex:none;font-variant-numeric:tabular-nums}
.gauge .big small{font-size:1.375rem;font-weight:800;margin-left:2px;letter-spacing:0;opacity:.75}
.g-hi{color:var(--green)} .g-mid{color:var(--quest)} .g-lo{color:var(--out)}
.hero-t{min-width:0}
.hero-t .eb{color:var(--muted)}
.hero-t .gt{font-size:var(--t-xl);font-weight:800;line-height:1.1;letter-spacing:-.02em}
.hero-t .gs{font-size:var(--t-sm);color:var(--muted);margin-top:4px;overflow-wrap:anywhere}
.meter{position:relative;height:8px;margin:14px var(--pad) 0;border-radius:999px;background:var(--ring-track)}
.meter span{display:block;height:100%;border-radius:999px;background:currentColor}
.meter i{position:absolute;top:-3px;bottom:-3px;left:50%;width:2px;margin-left:-1px;border-radius:2px;background:var(--ink2);opacity:.6}
.after{margin:10px var(--pad) 0;font-size:var(--t-sm);color:var(--muted)} .after b{color:var(--green-ink);font-weight:800}
.espn{margin:4px var(--pad) 0;font-size:.75rem;color:var(--muted);font-variant-numeric:tabular-nums} .espn b{color:var(--ink2);font-weight:700}
/* ESPN matchup board, shown large once games are live (same numbers as the fantasy app) */
.board{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:end;margin:0 var(--pad) 14px;padding:12px 14px;border-radius:var(--r-md);background:var(--well);border:1px solid var(--line)}
.board .side{min-width:0}
.board .side.opp{text-align:right}
.board .live{font-size:1.875rem;font-weight:900;line-height:1;letter-spacing:-.03em;color:var(--ink);font-variant-numeric:tabular-nums}
.board .proj{font-size:.75rem;color:var(--muted);margin-top:4px;font-variant-numeric:tabular-nums}
.board .proj b{color:var(--ink2);font-weight:700}
.board .mid{font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);padding-bottom:8px}
.hero{display:flex;flex-direction:column}
.kpis{display:flex;gap:8px;padding:12px var(--pad) 14px}
.hero>.kpis{order:3;border-top:1px solid var(--line)}
.hero-main{padding-bottom:14px}
.kpi{flex:1;min-width:0;padding:9px 11px;border-radius:var(--r-md);background:var(--well);border:1px solid var(--line)}
.kpi .l{font-size:.625rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi .v{font-size:var(--t-lg);font-weight:800;line-height:1.2;margin-top:2px;color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}
.kpi .s{font-size:.6875rem;color:var(--muted);line-height:1.3}
.kpi.go .v{color:var(--green-ink)}
.cols>.kpis{padding:0 0 12px}
.todo{list-style:none;margin:0;padding:0}
.todo .row{align-items:flex-start}
.todo .chip{margin-top:1px}
.todo .num{font-size:var(--t-md)}
.todo .nm{font-weight:700}
.qrisk{padding:2px var(--pad) 12px;font-size:var(--t-sm);color:var(--muted)} .qrisk p{margin:6px 0} .qrisk b{color:var(--quest);font-weight:700}
/* collapsible groups */
.fold{border-top:1px solid var(--line)}
.fold>summary{display:flex;align-items:center;gap:8px;padding:12px var(--pad);min-height:44px;font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);cursor:pointer;list-style:none}
.fold>summary::-webkit-details-marker,.pl>summary::-webkit-details-marker,.more>summary::-webkit-details-marker{display:none}
.fold>summary:hover{color:var(--ink2)}
.fold>summary::after,.pl>summary::after{content:"";flex:none;width:7px;height:7px;margin:0 3px 3px 0;border-right:2px solid var(--dim);border-bottom:2px solid var(--dim);transform:rotate(45deg);transition:transform .15s}
.fold>summary::after{margin-left:auto}
.fold[open]>summary::after,.pl[open]>summary::after{transform:rotate(225deg);margin-bottom:-3px}
.more{border-top:1px solid var(--line)}
.more>summary{padding:12px var(--pad);min-height:44px;font-size:var(--t-sm);font-weight:700;color:var(--accent-ink);cursor:pointer;list-style:none;text-align:center}
.more[open]>summary{display:none}
/* player cards */
.pl{border-top:1px solid var(--line)}
.pl>summary{list-style:none;cursor:pointer;border-top:0}
.pl>summary:hover{background:var(--fill)}
.pl>summary.hi:hover{background:var(--green-soft)} .pl>summary.lo:hover{background:var(--out-soft)}
.pl .num{min-width:52px}
.deep{margin:0 12px 12px;padding:12px;border-radius:var(--r-md);background:var(--well);border:1px solid var(--line);font-size:var(--t-sm);color:var(--ink2)}
.tiles{display:flex;gap:6px;margin-bottom:10px}
.tile{flex:1;min-width:0;padding:7px 9px;border-radius:var(--r-sm);background:var(--sheet);border:1px solid var(--line)}
.tile .l{font-size:.625rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.tile .v{font-size:var(--t-lg);font-weight:800;line-height:1.2;color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}
.tile .s{font-size:.6875rem;color:var(--muted);line-height:1.3}
.ol-s{color:var(--green-ink)!important} .ol-w{color:var(--quest)!important} .ol-x{color:var(--out)!important}
.kv{display:grid;grid-template-columns:4.6rem minmax(0,1fr);gap:5px 10px;margin:0}
.kv dt{font-size:.625rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding-top:3px}
.kv dd{margin:0;font-variant-numeric:tabular-nums} .kv dd b{color:var(--ink);font-weight:700}
.deep .ln{margin-top:8px;color:var(--muted)} .deep a{color:var(--accent-ink);text-decoration:none} .deep a:hover{text-decoration:underline}
.sig{list-style:none;margin:10px 0 0;padding:8px 0 0;border-top:1px solid var(--line)}
.sig li{display:flex;gap:8px;padding:2px 0}
.sig .sp{flex:none;width:14px;text-align:center;font-weight:900}
.sg-p{color:var(--green-ink)} .sg-m{color:var(--out)} .sg-i{color:var(--muted)}
.act{padding:9px var(--pad);font-size:var(--t-sm);border-top:1px solid var(--line);color:var(--muted)} .act b{font-weight:700;color:var(--ink)}
/* segmented position tabs */
.pos{display:flex;gap:4px;margin:0 var(--pad) 10px;padding:3px;border-radius:var(--r-md);background:var(--well);border:1px solid var(--line)}
.pos button{flex:1;text-align:center;padding:7px 0;min-height:34px;border-radius:9px;font-size:.75rem;font-weight:700;color:var(--muted);background:transparent;border:0;transition:background .15s,color .15s}
.pos button:hover{color:var(--ink)}
.pos button[aria-selected=true]{background:var(--fill);color:var(--ink);box-shadow:inset 0 0 0 1px var(--fill2)}
.panel{display:none} .panel[data-active]{display:block}
.tier{display:flex;align-items:center;gap:8px;padding:9px var(--pad) 5px;font-size:.625rem;font-weight:800;letter-spacing:.1em;border-top:1px solid var(--line)}
.tier::before{content:"";width:8px;height:8px;border-radius:2px;background:currentColor}
.tier.t1{color:var(--green-ink)} .tier.t2{color:var(--blue)} .tier.t3{color:var(--amber)} .tier.t4{color:var(--muted)}
.tier+.row{border-top:0}
.swap{display:grid;grid-template-columns:1fr auto 1fr auto;gap:8px;align-items:center;padding:10px var(--pad);border-top:1px solid var(--line)}
.swap .arrow{color:var(--muted);font-size:.75rem}
.swap .gain{font-variant-numeric:tabular-nums;color:var(--green-ink);font-weight:800;white-space:nowrap;font-size:var(--t-md)}
/* notices */
.alert{display:flex;gap:10px;align-items:baseline;margin:0 12px 8px;padding:9px 12px;border-radius:var(--r-md);background:var(--out-soft);border:1px solid var(--out-line)}
.alert.warn{background:var(--quest-soft);border-color:var(--quest-line)}
.alert .who{flex:none;font-size:var(--t-sm);font-weight:700;color:var(--ink)} .alert .why{font-size:.75rem;color:var(--ink2)}
.status{border:1px solid var(--quest-line);background:var(--quest-soft);border-radius:var(--r-md);padding:11px 14px;margin-bottom:12px;font-size:var(--t-sm)}
.status p{margin:0} .status .why{color:var(--muted);margin-top:3px}
.news .row{display:block;min-height:0;padding:11px var(--pad)} .news a{color:var(--ink);text-decoration:none;font-size:var(--t-md);font-weight:650;line-height:1.3}
.news a:hover{color:var(--accent-ink)}
.news .m{margin-top:3px}
.empty{color:var(--muted);font-size:var(--t-sm);padding:10px var(--pad) 14px;margin:0;border-top:1px solid var(--line)}
.foot{color:var(--dim);font-size:.75rem;padding:4px 6px 0}
/* settings */
#settings{display:none} #settings[data-open]{display:block}
.setrow{display:grid;grid-template-columns:84px 1fr;gap:12px;align-items:center;padding:6px var(--pad)}
.setrow:last-child{padding-bottom:14px}
.setrow label{font-size:var(--t-sm);font-weight:600;color:var(--muted)}
.seg{display:flex;gap:3px;background:var(--well);border:1px solid var(--line);border-radius:var(--r-md);padding:3px}
.seg button{flex:1;border:0;background:transparent;border-radius:9px;padding:7px 0;font-size:var(--t-sm);font-weight:700;color:var(--muted);min-height:36px;transition:background .15s,color .15s}
.seg button[aria-pressed=true]{background:var(--fill);color:var(--ink);box-shadow:inset 0 0 0 1px var(--fill2)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pl>summary:focus-visible,.fold>summary:focus-visible,.more>summary:focus-visible{outline-offset:-2px}
/* navigation: bottom tab bar on phones, sticky top tabs on desktop */
nav.top{display:none}
nav.bottom{position:fixed;left:0;right:0;bottom:0;z-index:20;background:var(--glass);border-top:1px solid var(--line);
  -webkit-backdrop-filter:saturate(160%) blur(18px);backdrop-filter:saturate(160%) blur(18px);padding:0 4px env(safe-area-inset-bottom)}
nav.bottom ul{list-style:none;margin:0 auto;padding:0;display:flex;max-width:560px}
nav.bottom li{flex:1;min-width:0}
nav.bottom a{position:relative;display:flex;flex-direction:column;align-items:center;gap:3px;padding:9px 0 8px;text-decoration:none;color:var(--muted);
  font-size:.625rem;font-weight:700;white-space:nowrap;line-height:1.1;transition:color .15s}
nav.bottom a svg{width:21px;height:21px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
nav.bottom a.on{color:var(--accent-ink)}
nav.bottom a.on::before{content:"";position:absolute;top:-1px;left:22%;right:22%;height:2px;border-radius:0 0 2px 2px;background:var(--accent)}
/* phones: one column in reading order; desktop: hero across the top, two columns below */
.cols{display:flex;flex-direction:column}
.col{display:contents}
#lineup{order:1} #waiver{order:2} #rank{order:3} #trades{order:4} #news{order:5}
@media(min-width:1024px){
  html{scroll-padding-top:76px}
  .wrap{max-width:1180px;padding:22px 28px 40px}
  .sheet{margin-bottom:16px}
  .cols{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:0 16px;align-items:start}
  .col{display:block}
  .cols>.kpis{grid-column:1/-1;padding-bottom:16px}
  header{padding:4px 4px 16px} header h1{font-size:1.75rem}
  nav.bottom{display:none}
  nav.top{display:block;position:sticky;top:10px;z-index:20;margin:0 0 16px}
  nav.top ul{list-style:none;margin:0;padding:5px;display:flex;flex-wrap:wrap;gap:2px;background:var(--glass);border:1px solid var(--line);border-radius:var(--r-lg);
    -webkit-backdrop-filter:saturate(160%) blur(18px);backdrop-filter:saturate(160%) blur(18px);box-shadow:var(--shadow)}
  nav.top a{display:block;padding:8px 14px;border-radius:11px;text-decoration:none;color:var(--muted);font-size:var(--t-sm);font-weight:700;transition:background .15s,color .15s}
  nav.top a:hover{color:var(--ink);background:var(--fill)}
  nav.top a.on{background:var(--accent-soft);color:var(--accent-ink)}
  nav.top li:last-child{margin-left:auto}
  .hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);grid-template-rows:auto 1fr}
  .hero-main{padding-bottom:4px}
  .hero>.kpis{grid-column:1;grid-row:2;border-top:0;align-self:start}
  .hero-do{grid-column:2;grid-row:1/3;border-left:1px solid var(--line)}
  .hero-do>.grp:first-child{border-top:0;padding-top:16px}
  .gauge .big{font-size:4.5rem}
}
""".replace("__DARK__", DARK).replace("__LIGHT__", LIGHT)

HEAD_JS = """(function(){try{localStorage.removeItem('ff-theme');var t=localStorage.getItem('ff-theme2');if(t&&t!=='dark')document.documentElement.setAttribute('data-theme',t);
var s=localStorage.getItem('ff-size');if(s&&s!=='default')document.documentElement.setAttribute('data-size',s);}catch(e){}})();"""

JS = """
(function(){
  var root=document.documentElement,panel=document.getElementById('settings');
  var themeMeta=document.querySelector('meta[name="theme-color"]');
  function themeColor(){var t=root.getAttribute('data-theme');if(t==='light')return '#f3f5f8';if(t==='auto'&&window.matchMedia('(prefers-color-scheme:light)').matches)return '#f3f5f8';return '#090d13';}
  function paintTheme(){if(themeMeta)themeMeta.setAttribute('content',themeColor());}
  function setGear(open){document.querySelectorAll('[data-gear]').forEach(function(b){b.setAttribute('aria-expanded',open?'true':'false')});}
  function toggle(e){e.preventDefault();var open=!panel.hasAttribute('data-open');if(open){panel.setAttribute('data-open','');panel.scrollIntoView({block:'start'});}else panel.removeAttribute('data-open');setGear(open);}
  document.querySelectorAll('[data-gear]').forEach(function(b){b.addEventListener('click',toggle)});setGear(false);
  function get(k,d){try{return localStorage.getItem(k)||d}catch(e){return d}}
  function set(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  function wire(name,key,attr,def){
    var btns=panel.querySelectorAll('[data-set="'+name+'"] button');
    function paint(v){btns.forEach(function(b){b.setAttribute('aria-pressed',b.dataset.v===v?'true':'false')});if(v===def)root.removeAttribute(attr);else root.setAttribute(attr,v);if(name==='theme')paintTheme();}
    paint(get(key,def));btns.forEach(function(b){b.addEventListener('click',function(){set(key,b.dataset.v);paint(b.dataset.v)})});
  }
  wire('theme','ff-theme2','data-theme','dark');wire('size','ff-size','data-size','default');
  paintTheme();
  try{window.matchMedia('(prefers-color-scheme:light)').addEventListener('change',paintTheme);}catch(e){}
  document.querySelectorAll('.pos').forEach(function(tabs){
    var btns=tabs.querySelectorAll('button');
    btns.forEach(function(b){b.addEventListener('click',function(){
      btns.forEach(function(x){x.setAttribute('aria-selected','false')});b.setAttribute('aria-selected','true');
      tabs.parentElement.querySelectorAll('.panel').forEach(function(p){if(p.dataset.pos===b.dataset.pos)p.setAttribute('data-active','');else p.removeAttribute('data-active')});
    })});
  });
  /* Expand all / Collapse all for the player cards in a section. */
  document.querySelectorAll('[data-xall]').forEach(function(b){
    var cards=b.closest('section').querySelectorAll('details.pl');
    function label(){var open=0;cards.forEach(function(d){if(d.open)open++});var all=open===cards.length&&open>0;b.textContent=all?'Collapse all':'Expand all';b.setAttribute('aria-pressed',all?'true':'false');return all;}
    b.addEventListener('click',function(){var all=label();cards.forEach(function(d){d.open=!all});label();});
    cards.forEach(function(d){d.addEventListener('toggle',label)});label();
  });
  var links=document.querySelectorAll('nav a[href^="#"]'),secs=[];
  links.forEach(function(a){var s=document.querySelector(a.getAttribute('href'));if(s)secs.push([s,a])});
  function mark(){var y=window.scrollY+120,cur=null,best=-1;secs.forEach(function(p){var t=p[0].getBoundingClientRect().top+window.scrollY;if(p[0].offsetParent!==null&&t<=y&&t>best){best=t;cur=p[0]}});if(!cur){for(var i=0;i<secs.length;i++){if(secs[i][0].offsetParent!==null){cur=secs[i][0];break;}}}
    if(window.innerHeight+window.scrollY>=document.documentElement.scrollHeight-2&&secs.length){for(var j=secs.length-1;j>=0;j--){if(secs[j][0].offsetParent!==null){cur=secs[j][0];break;}}}
    links.forEach(function(a){a.classList.toggle('on',document.querySelector(a.getAttribute('href'))===cur)});}
  window.addEventListener('scroll',mark,{passive:true});mark();
  /* Relative age from the build's ISO timestamp so a static Pages deploy still reads "2h ago". */
  function ageLabel(ms){
    if(ms<0)ms=0;
    var m=Math.floor(ms/60000);
    if(m<1)return 'just now';
    if(m<60)return m+'m ago';
    var h=Math.floor(m/60);
    if(h<48)return h+'h ago';
    return Math.floor(h/24)+'d ago';
  }
  function paintAge(){
    document.querySelectorAll('[data-generated-at]').forEach(function(el){
      var t=Date.parse(el.getAttribute('data-generated-at')||'');
      if(!t)return;
      var ms=Date.now()-t,label=ageLabel(ms);
      el.querySelectorAll('[data-age]').forEach(function(s){s.textContent=label});
      var stale=ms>=18*3600*1000?'old':(ms>=6*3600*1000?'stale':'');
      if(stale)el.setAttribute('data-stale',stale);else el.removeAttribute('data-stale');
    });
  }
  paintAge();setInterval(paintAge,60000);
  document.addEventListener('visibilitychange',function(){if(!document.hidden)paintAge()});
})();
"""

ICONS = {
    "lineup": '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2zM9 14l2 2 4-4"/></svg>',
    "waiver": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
    "rank": '<svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    "trades": '<svg viewBox="0 0 24 24"><path d="M7 10h10l-3-3M17 14H7l3 3"/></svg>',
    "news": '<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4zM8 9h8M8 13h8M8 17h5"/></svg>',
    "plan": '<svg viewBox="0 0 24 24"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H5a2 2 0 0 0 0 4h2M17 6h2a2 2 0 0 1 0 4h-2"/></svg>',
    "gear": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
}


_BAD = {"OUT", "DOUBTFUL", "IR", "SUSPENSION", "INJURY_RESERVE"}
_MEH = {"QUESTIONABLE", "DAY_TO_DAY", "PROBABLE"}
# Injury tag beside a name: short text, colour class (q = amber, o = red).
_TAG = {"QUESTIONABLE": ("Q", "q"), "DAY_TO_DAY": ("DTD", "q"), "PROBABLE": ("P", "q"), "DOUBTFUL": ("D", "o"),
        "OUT": ("OUT", "o"), "IR": ("IR", "o"), "INJURY_RESERVE": ("IR", "o"), "SUSPENSION": ("SUSP", "o")}
SHOW_FIRST = 12          # rows shown before a "Show N more" fold in long lists


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _ext(href: str, text: str) -> str:
    """Outbound link: new tab so Add-to-Home-Screen doesn't lose the dashboard."""
    return f'<a href="{_e(href)}" target="_blank" rel="noopener noreferrer">{_e(text)}</a>'


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


def _status_key(p: dict) -> str:
    return (p.get("injury") or "").upper().replace(" ", "_")


def _inj(p: dict) -> str:
    s = _status_key(p)
    label = s.replace("_", " ").title()
    if s in _BAD:
        return f' &middot; <span class="f-out">{_e(label)}</span>'
    if s in _MEH:
        return f' &middot; <span class="f-quest">{_e(label)}</span>'
    return ""


def _tag(p: dict) -> str:
    """Compact injury tag (Q, OUT, IR...) shown beside the name; the full word is kept for screen readers."""
    s = _status_key(p)
    if s not in _TAG:
        return ""
    short, cls = _TAG[s]
    label = s.replace("_", " ").title()
    return (f'<span class="tag {cls}" title="{_e(label)}"><span class="sr">{_e(label)}</span>'
            f'<span aria-hidden="true">{short}</span></span>')


def _nm(name, tag: str = "", free: bool = False) -> str:
    """Name line. The name truncates; a tag after it never does. free=True lets a sentence wrap."""
    cls = "nm free" if free else "nm"
    return f'<div class="{cls}"><span class="nt">{_e(name)}</span>{tag}</div>'


def _kick(p: dict) -> str:
    """Kickoff, Live, or Final: game-day cues the pipeline already knows."""
    if p.get("final"):
        return ' &middot; <span class="f-dim">Final</span>'
    if p.get("locked"):
        return ' &middot; <span class="f-live">Live</span>'
    ko = p.get("kickoff")
    return f" &middot; {_e(ko)}" if ko else ""


def _meta(p: dict, extra: str = "", inj: bool = True, kick: bool = True) -> str:
    bits = " ".join(b for b in [p.get("position"), p.get("team")] if b)
    opp = p.get("opponent")
    if opp and str(opp) != "None":
        bits += f" vs {opp}"
    return f'<div class="m">{_e(bits)}{_inj(p) if inj else ""}{_kick(p) if kick else ""}{extra}</div>'


def _fold(title: str, body: str, count=None, is_open: bool = False) -> str:
    """A collapsed group inside a card. Empty body renders nothing."""
    if not body:
        return ""
    ct = f'<span class="ct">{count}</span>' if count else ""
    return f'<details class="fold"{" open" if is_open else ""}><summary>{_e(title)}{ct}</summary>{body}</details>'


def _capped(rows: list, first: int = SHOW_FIRST) -> str:
    """Join rows; anything past the first few goes behind a 'Show N more' control."""
    if len(rows) <= first + 2:
        return "".join(rows)
    rest = rows[first:]
    return ("".join(rows[:first]) + f'<details class="more"><summary>Show {len(rest)} more</summary>'
            + "".join(rest) + "</details>")


def _verdicts(roster: list[dict], opt: dict) -> dict:
    """name -> ('start'|'sit'|'consider', note)"""
    if not opt or not opt.get("lineup"):
        return {}
    optimal = {e["player"]["name"] for e in opt["lineup"] if e.get("player")}
    out = {}
    for p in roster:
        s = _status_key(p)
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


# ESPN's lineup order: QB, RB, WR, TE, FLEX, D/ST, K (stable within a slot).
_SLOT_ORDER = ["QB", "RB", "WR", "TE", "RB/WR/TE", "FLEX", "OP", "D/ST", "K"]


def _slot_rank(p: dict) -> int:
    s = p.get("slot") or ""
    return _SLOT_ORDER.index(s) if s in _SLOT_ORDER else len(_SLOT_ORDER)


def _played(p: dict) -> bool:
    return bool(p.get("locked") or p.get("final")) and isinstance(p.get("actual"), (int, float))


def _lineup(roster: list[dict], opt: dict, cards: dict = None, gameday: bool = False, rw: list = None,
            swaps_open: bool = True) -> str:
    """Start/sit rows. The collapsed row carries one number (live or final points once his game has
    started, else the blended projection) and one verdict; sources, ESPN's own number, expected
    points and outlook are in the card underneath. On game day the cards that need a decision
    (a recommended move or an uncertain player) start open."""
    cards = cards or {}
    starters = sorted((p for p in roster if p.get("starting")), key=_slot_rank)  # ESPN order
    bench = sorted((p for p in roster if not p.get("starting")), key=lambda p: p.get("slot") == "IR")  # IR last
    v = _verdicts(roster, opt)

    def row(p):
        verdict, note = v.get(p["name"], (None, ""))
        c = cards.get(p["name"])
        move_in = verdict == "start" and not p.get("starting")
        move_out = verdict == "sit" and bool(p.get("starting"))
        unsure = verdict == "consider" or bool(c and 0 < c.get("p_play", 1) < 1)
        # Bench rows only get a chip when there's something to do; red belongs on a starter who should sit.
        chip = ""
        if verdict and (p.get("starting") or verdict != "sit"):
            chip = f'<span class="chip {verdict}">{verdict.upper()}</span>'
        if _played(p):
            state = "final" if p.get("final") else "live"
            chip = f'<span class="chip {state}">{state.upper()}</span>'
            big = _pts(p["actual"])
            meta = _meta(p, f' &middot; proj {_pts(p.get("projected"))}', inj=False, kick=False)
        else:
            big = _pts(p.get("projected"))
            meta = _meta(p, inj=False)
        if note:        # what to do about him, on its own line
            tone = "f-go" if verdict == "start" else "f-quest" if verdict == "consider" else "f-out"
            meta += f'<div class="m {tone}">{_e(note)}</div>'
        if p.get("locked") or p.get("final"):       # kicked off: nothing left to decide
            move_in = move_out = unsure = False
        state_cls = " hi" if move_in else " lo" if move_out else " qm" if unsure and p.get("starting") else ""
        raw_slot = p.get("slot") or "BE"
        slot_txt = {"RB/WR/TE": "FLEX", "BE": "BN"}.get(raw_slot, raw_slot)
        slot = f'<span class="chip slot{" bn" if raw_slot in ("BE", "IR") else ""}">{_e(slot_txt)}</span>'
        inner = (f'{slot}<div class="who">{_nm(p["name"], _tag(p))}{meta}</div>'
                 f'<div class="num"><span class="pts">{big}</span>{chip}</div>')
        deep = _deep(c, p) if c else _deep_basic(p)
        if not deep:
            return f'<div class="row{state_cls}">{inner}</div>'
        is_open = gameday and (move_in or move_out or unsure)
        return (f'<details class="pl"{" open" if is_open else ""}><summary class="row{state_cls}">{inner}</summary>'
                f'{deep}</details>')

    if not roster:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    swaps = ""
    if opt.get("lineup"):
        swaps = _fold("Recommended swaps", _swaps(opt), len(opt["swaps"]), swaps_open)
    return ('<div class="grp">Starting</div>' + "".join(row(p) for p in starters) +
            '<div class="grp">Bench</div>' + "".join(row(p) for p in bench) +
            swaps + _role_watch(rw))


def _alerts(roster: list[dict]) -> str:
    items = []
    for p in roster:
        if not p.get("starting"):
            continue
        s = _status_key(p)
        label = s.replace("_", " ").title()
        ko = f" {p['kickoff']}." if p.get("kickoff") and not p.get("locked") else ""
        if s in _BAD:
            items.append(("alert", p["name"], f"Listed {label.lower()} and in your starting lineup.{ko}"))
        elif s in _MEH:
            items.append(("alert warn", p["name"], f"{label}. Check inactives before kickoff.{ko}"))
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
        out_html = (_nm(o["name"], _tag(o)) + _meta(o, inj=False)) if o else '<span class="m">open slot</span>'
        out += (f'<div class="swap"><div>{_nm(s["in"]["name"], _tag(s["in"]))}{_meta(s["in"], inj=False)}</div>'
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
        f'<button type="button" role="tab" data-pos="{_e(p)}" aria-selected="{"true" if i == 0 else "false"}">{_e(p)}</button>'
        for i, p in enumerate(order)) + "</div>"
    panels = ""
    for i, pos in enumerate(order):
        rows = rk.get(pos, [])
        tiers = _tiers(rows)
        items, last = [], 0
        for r, t in zip(rows, tiers):
            head = ""
            if t != last:
                head = f'<div class="tier t{t}">TIER {t}</div>'
                last = t
            who = ' &middot; <span class="f-go">yours</span>' if r.get("mine") else (
                  f' &middot; {_e(r["owner"])}' if r.get("owner") else ' &middot; available')
            items.append(f'{head}<div class="row{" me" if r.get("mine") else ""}"><span class="rk">{r["rank"]}</span>'
                         f'<div class="who">{_nm(r["name"], _tag(r))}{_meta(r, who, inj=False)}</div>'
                         f'<div class="num">{_pts(r["proj"])}{_last(r["ppg_2025"])}</div></div>')
        body = _capped(items) or '<p class="empty">No data.</p>'
        panels += f'<div class="panel" data-pos="{_e(pos)}"{" data-active" if i == 0 else ""}>{body}</div>'
    return tabs + panels


def _trades(tr: dict) -> str:
    if not tr:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    out = ""
    if tr["needs"]:
        out += '<div class="grp">Where you\'re thin</div>' + "".join(
            f'<div class="row"><div class="who">{_nm(n["position"])}'
            f'<div class="m">your best starter {n["best"]}, league median {n["median"]}</div></div>'
            f'<div class="num f-out">&minus;{n["gap"]}</div></div>' for n in tr["needs"])
    else:
        out += '<p class="empty">No position where your starter is below the league median.</p>'
    if tr["chips"]:
        out += '<div class="grp">Trade chips on your bench</div>' + "".join(
            f'<div class="row"><div class="who">{_nm(c["name"], _tag(c))}{_meta(c, " &middot; median starter " + str(c["median"]), inj=False)}</div>'
            f'<div class="num">{_pts(c["score"])}</div></div>' for c in tr["chips"])
    if tr["targets"]:
        out += '<div class="grp">Targets on teams with surplus</div>' + _capped([
            f'<div class="row"><div class="who">{_nm(t["name"], _tag(t))}{_meta(t, inj=False)}<div class="reason">{_e(t["reason"])}</div></div>'
            f'<div class="num">{_pts(t["proj"])}{_last(t["ppg_2025"])}</div></div>' for t in tr["targets"]], 5)
    if tr["buy_low"]:
        out += '<div class="grp">Buy low</div>' + _capped([
            f'<div class="row"><div class="who">{_nm(b["name"], _tag(b))}{_meta(b, " &middot; " + _e(b["owner"]), inj=False)}<div class="reason">{_e(b["reason"])}</div></div>'
            f'<div class="num">{_pts(b["proj"])}{_last(b["ppg_2025"])}</div></div>' for b in tr["buy_low"]], 5)
    return out


_OL = {"Strong": "s", "Solid": "o", "Shaky": "w", "Weak": "x", "Not playing": "x"}
_TRENDW = {"up": "usage rising", "down": "usage falling", "flat": "usage steady"}
_SG = {"+": ("p", "+"), "-": ("m", "\u2212"), "i": ("i", "\u2022")}
_DAYS = {"Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday", "Mon": "Monday", "Bye": "Bye week"}


def _tile(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="tile"><div class="l">{label}</div><div class="v{(" " + cls) if cls else ""}">{value}</div>'
            f'<div class="s">{sub}</div></div>')


def _kv(pairs: list) -> str:
    rows = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in pairs if v)
    return f'<dl class="kv">{rows}</dl>' if rows else ""


def _role_line(p: dict) -> str:
    """Role and usage, plus any role boost."""
    t = (p.get("usage") or {}).get("text", "")
    boost = f'<span class="f-go">+{p["boost"]:.1f} role</span>' if p.get("boost") else ""
    return " &middot; ".join(b for b in [_e(t), boost] if b)


def _deep_basic(p: dict) -> str:
    """Card body when there is no assessment card: role and each source's projection."""
    src = sources.line(p)
    src_html = f'<span{" class=" + chr(34) + "f-quest" + chr(34) if p.get("split") else ""}>{_e(src)}</span>' if src else ""
    body = _kv([("Role", _role_line(p)), ("Sources", src_html)])
    return f'<div class="deep">{body}</div>' if body else ""


def _deep(c: dict, p: dict = None) -> str:
    """The expandable player card. Headline numbers as tiles (outlook, expected points, typical
    range), then where the projection comes from, his role and recent usage, the signed reasons
    and one news link."""
    p = p or {}
    tiles = _tile("Outlook", str(c["outlook"]), _e(c["label"]), "ol-" + _OL.get(c["label"], "o"))
    if c.get("actual") is not None and (c.get("locked") or c.get("final")):
        tiles += _tile("Final" if c.get("final") else "Live", f'{c["expected"]:.1f}', f'proj {c["proj"]:.1f}')
    else:
        tiles += _tile("Expected", f'{c["expected"]:.1f}', f'vs {c["bench"]:.1f} avg {_e(c["position"])}')
    if c.get("range"):
        tiles += _tile("Range", f'{c["range"][0]}&ndash;{c["range"][1]}', "middle 80%")

    src = c.get("sources") or {}
    src_html = ""
    if len(src) >= 2:
        s_txt = " &middot; ".join(f"{_e(k)} {v:.1f}" for k, v in src.items())
        blend = c["proj"] - (c.get("boost") or 0.0)
        extra = f' + {c["boost"]:.1f} role = <b>{c["proj"]:.1f}</b>' if c.get("boost") else ""
        split = ' &middot; <span class="f-quest">sources split</span>' if c.get("split") else ""
        src_html = f'{s_txt} &rarr; average <b>{blend:.1f}</b>{extra}{split}'
    elif isinstance(c.get("proj_espn"), (int, float)) and abs(c["proj"] - c["proj_espn"]) >= 0.05:
        src_html = f'ESPN {c["proj_espn"]:.1f} &rarr; <b>{c["proj"]:.1f}</b> with the role change'
    role = _role_line(p) if p else _e(c.get("role", ""))
    trend = _e(_TRENDW[c["trend"]])
    usage = ""
    if c.get("usage_pts") is not None:
        usage = (f'recent targets, carries and throws worth <b>{c["usage_pts"]:.1f}</b> a game '
                 f'(context, not in the number)')
    body = _kv([("Sources", src_html), ("Role", role), ("Trend", trend), ("Usage", usage),
                ("Last game", _e(c.get("last") or "")), ("Recent", _e(c.get("avg") or ""))])
    parts = [f'<div class="tiles">{tiles}</div>', body]
    if c.get("range") and not c.get("starting") and c.get("boom") and c["boom"] >= assess.UPSIDE_AT:
        parts.append('<div class="ln">Higher upside than a typical bench player: about 1 in 7 like him beat their '
                     'projection by 8+, against 1 in 11 overall. A weak signal that mostly reflects a higher projection.</div>')
    n = c.get("news")
    linked = n.get("headline") if n and n.get("link") else None
    sigs = ""
    for sign, text in c.get("signals", []):
        if linked and text == f"News: {linked}":      # the same headline is linked just below
            continue
        cls, ch = _SG[sign]
        sigs += f'<li><span class="sp sg-{cls}">{ch}</span><span>{_e(text)}</span></li>'
    if sigs:
        parts.append(f'<ul class="sig">{sigs}</ul>')
    if linked:
        parts.append(f'<div class="ln">News: {_ext(n["link"], n["headline"])}</div>')
    return '<div class="deep">' + "".join(parts) + "</div>"


def _role_watch(rw: list) -> str:
    """Who gains or loses touches this week, yours first. Collapsed under the lineup."""
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
        if n and n.get("link"):
            lines.append(_ext(n.get("link", "#"), n.get("headline", "")))
        elif n:
            lines.append(_e(n.get("headline", "")))
        num = f'<div class="num f-go">+{e["boost"]:.1f}</div>' if e.get("boost") else ""
        rows += (f'<div class="row"><div class="who">{_nm(e["name"])}'
                 f'<div class="m">{_e(e.get("position", ""))} {_e(e.get("team", ""))}{who}</div>'
                 f'<div class="reason">{" &middot; ".join(lines)}</div></div>{num}</div>')
    return _fold("Role watch: who gets the ball", rows, len(rw))


# The gain is shown as the number on the right of an action, so the same sentence is dropped from its detail.
_GAIN_LEAD = re.compile(r"\+\d+(?:\.\d+)? (?:projected points|this week)\.\s*")


def _kpis(opt: dict, opp_total: float, lg: dict) -> str:
    """Optimizer gain, best lineup total and league standing as one compact strip."""
    out = ""
    if opt.get("lineup"):
        n = len(opt["swaps"])
        if n:
            out += (f'<div class="kpi go"><div class="l">Optimizer</div><div class="v">+{opt["gain"]}</div>'
                    f'<div class="s">{n} swap{"s" if n != 1 else ""} available</div></div>')
        else:
            out += ('<div class="kpi go"><div class="l">Optimizer</div><div class="v">Optimal</div>'
                    '<div class="s">no changes needed</div></div>')
        opp_txt = ("opp " + f"{opp_total:.1f}") if opp_total else "this week"
        out += (f'<div class="kpi"><div class="l">Best lineup</div><div class="v">{opt["optimal_total"]}</div>'
                f'<div class="s">{opp_txt}</div></div>')
    if lg.get("standing") and lg.get("team_count"):
        bits = []
        if isinstance(lg.get("playoff_pct"), (int, float)):
            bits.append(f"{lg['playoff_pct']:.0f}% playoff odds")
        if lg.get("streak"):
            bits.append(f"{lg['streak']} streak")
        sub = _e(" \u00b7 ".join(bits)) or "\u00a0"
        out += (f'<div class="kpi"><div class="l">Standing</div><div class="v">{_ordinal(lg["standing"])} of {lg["team_count"]}</div>'
                f'<div class="s">{sub}</div></div>')
    return f'<div class="kpis">{out}</div>' if out else ""


def _hero(a: dict, opp_name: str, kpis: str = "") -> str:
    """Top card: win chance on the left (first on a phone), the 'Do this' list beside or under it.
    The explanations (injury-risk lines, by-day scores) are folded away below the actions."""
    if not a or a.get("score") is None:
        return ""
    sc = a["score"]
    cls = "g-hi" if sc >= 55 else "g-mid" if sc >= 45 else "g-lo"
    vs = f" to beat {_e(opp_name)}" if opp_name else ""
    # Blend-based expected total (advice). Separate from the ESPN scoreboard numbers.
    unit = "model" if a.get("has_actuals") else "projected"
    board = espn = ""
    if a.get("espn_proj") is not None:
        live_m = a.get("espn_live", 0.0)
        live_o = a.get("espn_live_opp")
        proj_o = a.get("espn_proj_opp")
        both = isinstance(live_o, (int, float)) and isinstance(proj_o, (int, float))
        if a.get("has_actuals") or live_m or (both and live_o):
            left = (f'<div class="side"><div class="live">{live_m:.1f}</div>'
                    f'<div class="proj">ESPN proj <b>{a["espn_proj"]:.1f}</b></div></div>')
            right = (f'<div class="side opp"><div class="live">{live_o:.1f}</div>'
                     f'<div class="proj">ESPN proj <b>{proj_o:.1f}</b></div></div>') if both else (
                '<div class="side opp"><div class="live">&mdash;</div><div class="proj">&nbsp;</div></div>')
            board = f'<div class="board">{left}<div class="mid">vs</div>{right}</div>'
        else:       # nothing has kicked off: the live score is 0-0, so one quiet line is enough
            opp_txt = f" vs <b>{proj_o:.1f}</b>" if both else ""
            espn = f'<p class="espn">ESPN projects <b>{a["espn_proj"]:.1f}</b>{opp_txt}</p>'
    head = (f'{board}<div class="gauge {cls}"><div class="big">{sc}<small>%</small></div><div class="hero-t">'
            f'<div class="eb">Win chance</div><div class="gt">{_e(a["label"])}</div>'
            f'<div class="gs">Our model {a["mine"]:.1f} vs {a["opp"]:.1f} {unit}{vs}</div></div></div>'
            f'<div class="meter {cls}" role="img" aria-label="Win chance {sc} percent"><span style="width:{max(2, min(100, sc))}%"></span><i></i></div>')
    o = a.get("optimal") or {}
    if o.get("win") is not None and o["expected"] >= a["mine"] + 0.5:
        after = (f'<p class="after">With the lineup changes: <b>{round(100 * o["win"])}%</b> '
                 f'({o["expected"]:.1f} {unit})</p>')
    elif a.get("has_actuals"):
        after = ('<p class="after">Scoreboard above matches ESPN (actuals + ESPN projections). '
                 'Win chance uses our model on the same actuals. 50% is a coin flip.</p>')
    else:
        after = '<p class="after">Chance your lineup outscores this week\'s opponent. 50% is a coin flip.</p>'

    acts = ""
    actions = a.get("actions", [])
    for x in actions:
        shown = x["gain"] >= 0.1
        gain = f'<div class="num f-go">+{x["gain"]:.1f}<small>pts</small></div>' if shown else ""
        detail = _GAIN_LEAD.sub("", x["detail"], count=1) if shown else x["detail"]
        why = f'<div class="reason">{_e(detail)}</div>' if detail.strip() else ""
        acts += (f'<li class="row"><span class="chip k-{x["kind"]}">{x["kind"].upper()}</span><div class="who">'
                 f'{_nm(x["title"], free=True)}{why}</div>{gain}</li>')
    if acts:
        acts = f'<ol class="todo">{acts}</ol>'
    else:
        acts = '<p class="empty">Nothing to do. Your lineup is optimal and no pickup improves it.</p>'
    count = f'<span class="ct">{len(actions)}</span>' if actions else ""

    lines = assess.risk_lines(a)
    risk = ""
    if lines:
        risk = _fold("Injury risk: how they're counted",
                     '<div class="qrisk">' + "".join(f'<p><b>{_e(label)}</b>: {_e(text)}</p>' for label, text in lines) + "</div>",
                     len(lines))

    days = ""
    for d in a.get("days", []):
        names = ", ".join(d["names"])
        if d["day"] == "Bye":
            days += (f'<div class="row"><div class="who">{_nm("No game")}'
                     f'<div class="m">{_e(names)} {"has" if d["n"] == 1 else "have"} a bye</div></div>'
                     f'<div class="num f-out">0</div></div>')
            continue
        s_ = "" if d["n"] == 1 else "s"
        day = _nm(_DAYS.get(d["day"], d["day"]))
        if d.get("final"):
            days += (f'<div class="row"><div class="who">{day}'
                     f'<div class="m">{d["n"]} starter{s_} &middot; {d["expected"]:.1f} final &middot; {_e(names)}</div></div>'
                     f'<div class="num f-dim">Final<small>{d["vs_typical"]:+.1f} vs avg team</small></div></div>')
            continue
        k = "f-go" if d["score"] >= 55 else "f-quest" if d["score"] >= 40 else "f-out"
        days += (f'<div class="row"><div class="who">{day}'
                 f'<div class="m">{d["n"]} starter{s_} &middot; {d["expected"]:.1f} projected &middot; {_e(names)}</div></div>'
                 f'<div class="num {k}">{d["score"]}%<small>{d["vs_typical"]:+.1f} vs avg team</small></div></div>')
    days = _fold("By day", days)
    return (f'<section class="sheet hero" id="checkup"><div class="hero-main"><div class="hd"><h2>{_e(a["title"])}</h2>'
            f'<span class="m">Week {_e(a["week"])}</span></div>'
            f'{head}{after}{espn}</div>'
            f'<div class="hero-do"><div class="grp">Do this{count}</div>{acts}{risk}{days}</div>{kpis}</section>')


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
    """Pick-ups first (each expands to role and source numbers); the browsing lists are folded."""
    if not w:
        return '<p class="empty">Needs your roster. See the note at the top of the page.</p>'
    out = ""
    if w["adds"]:
        rows = []
        for a in w["adds"]:
            flags = []
            if a.get("need"):
                flags.append('<span class="f-go">fills a need</span>')
            if a.get("hot"):
                flags.append(f'<span class="f-quest">{a["hot"]:,} adds in 48h</span>')
            if a.get("dropped_by"):
                flags.append(f'dropped by {_e(a["dropped_by"])}')
            extra = f'<div class="m">{" &middot; ".join(flags)}</div>' if flags else ""
            drop = f'<b>Drop {_e(a["drop"])}.</b> ' if a.get("drop") else ""
            inner = (f'<span class="chip {a["verdict"]}">{a["verdict"].upper()}</span>'
                     f'<div class="who">{_nm(a["name"], _tag(a))}{_meta(a, inj=False)}{extra}<div class="reason">{drop}{_e(a["reason"])}</div></div>'
                     f'<div class="num">{_pts(a["proj"])}</div>')
            deep = _deep_basic(a)
            if deep:
                rows.append(f'<details class="pl"><summary class="row">{inner}</summary>{deep}</details>')
            else:
                rows.append(f'<div class="row">{inner}</div>')
        out += f'<div class="grp">Pick up<span class="ct">{len(rows)}</span></div><div class="adds">' + _capped(rows, 5) + "</div>"
    else:
        out += '<p class="empty">Nobody on the wire beats what you have. Check again after waivers clear.</p>'
    if w["hot"]:
        out += _fold("Hot everywhere, unclaimed here", "".join(
            f'<div class="row"><div class="who">{_nm(h["name"], _tag(h))}{_meta(h, inj=False)}</div>'
            f'<div class="num">{h["count"]:,}<small>adds in 48h</small></div></div>' for h in w["hot"]), len(w["hot"]))
    if w["just_dropped"]:
        rows = ""
        for d in w["just_dropped"]:
            by = f' &middot; by {_e(d["dropped_by"])}, {_e(d["when"])}'
            rows += (f'<div class="row"><div class="who">{_nm(d["name"], _tag(d))}{_meta(d, by, inj=False)}</div>'
                     f'<div class="num">{_pts(d["proj"])}{_last(d.get("ppg_2025"))}</div></div>')
        out += _fold("Just dropped in your league", rows, len(w["just_dropped"]))
    if w["drops"]:
        out += _fold("If you need a roster spot", "".join(
            f'<div class="row"><div class="who">{_nm(d["name"], _tag(d))}{_meta(d, inj=False)}<div class="reason">{_e(d["reason"])}</div></div>'
            f'<div class="num">{_pts(d["proj"])}</div></div>' for d in w["drops"]), len(w["drops"]))
    if w["activity"]:
        out += _fold("League activity", _activity(w["activity"]))
    return out


def _status(espn: dict) -> str:
    if not espn or espn.get("ok"):
        note = (espn or {}).get("reason", "")
        return f'<div class="status"><p>{_e(note)}</p></div>' if note else ""
    return (f'<div class="status"><p>ESPN isn\'t connected, so your roster is missing.</p>'
            f'<p class="why">{_e(espn.get("reason") or "No reason recorded.")}</p></div>')


def settings_button() -> str:
    """Header gear. Shared with the Championship Plan page."""
    icon = ICONS["gear"].replace(
        "<svg",
        '<svg width="19" height="19" aria-hidden="true" style="stroke:currentColor;fill:none;stroke-width:1.7"',
        1,
    )
    return ('<button type="button" class="gear" data-gear aria-label="Settings" '
            f'aria-controls="settings" aria-expanded="false">{icon}</button>')


def settings_panel() -> str:
    """Theme and text-size controls. Shared with the Championship Plan page."""
    return ('<section class="sheet" id="settings"><div class="hd"><h2>Settings</h2><span class="m">saved on this device</span></div>'
            '<div class="setrow"><label>Theme</label><div class="seg" data-set="theme" role="group" aria-label="Theme">'
            '<button type="button" data-v="auto">Auto</button><button type="button" data-v="light">Light</button>'
            '<button type="button" data-v="dark">Dark</button></div></div>'
            '<div class="setrow"><label>Text size</label><div class="seg" data-set="size" role="group" aria-label="Text size">'
            '<button type="button" data-v="small">Small</button><button type="button" data-v="default">Default</button>'
            '<button type="button" data-v="large">Large</button><button type="button" data-v="xl">XL</button></div></div></section>')


def section_nav(active: str = "", checkup: bool = True, root: str = ""):
    """Section tabs. 'root' is empty on the dashboard and 'index.html' on the
    Championship Plan page, so those tabs leave the plan and come back.
    The dashboard highlights the section in view; the plan page marks itself.
    Phone labels stay short. Desktop uses the full 'Championship Plan' name.
    Settings is the gear in the header on phones and the last tab on desktop.
    """
    items = []
    if checkup:
        items.append(("#checkup", "check", "Check-up", "Check-up"))
    items.extend([
        ("#lineup", "lineup", "Lineup", "Lineup"),
        ("#waiver", "waiver", "Waivers", "Waivers"),
        ("#rank", "rank", "Ranks", "Rankings"),
        ("#trades", "trades", "Trades", "Trades"),
        ("#news", "news", "News", "News"),
        ("plan.html", "plan", "Plan", "Championship Plan"),
    ])

    def href(frag: str, key: str) -> str:
        if key == "plan":
            return "plan.html"
        if key == "gear":
            return "#settings"
        if root:
            return root + frag
        return frag

    def attrs(key: str, short: str, long: str) -> str:
        bits = []
        if active and key == active:
            bits.append('class="on"')
            bits.append('aria-current="page"')
        if short != long:
            bits.append('aria-label="' + _e(long) + '"')
        if not bits:
            return ""
        return " " + " ".join(bits)

    bottom = "".join(
        "<li><a href=\"" + href(h, i) + "\"" + attrs(i, short, long) + ">" + ICONS[i] + short + "</a></li>"
        for h, i, short, long in items
    )
    top = "".join(
        "<li><a href=\"" + href(h, i) + "\"" + attrs(i, long, long) + ">" + long + "</a></li>"
        for h, i, short, long in items
    ) + "<li><a href=\"" + href("#settings", "gear") + "\" data-gear>Settings</a></li>"
    return top, bottom


def build(data: dict) -> str:
    week = data.get("week", "?")
    team = data.get("team_name") or "Your team"
    roster = data.get("roster", [])
    opt = data.get("optimizer", {}) or {}
    assessment = data.get("assessment") or {}
    # Prefer the meter's opponent expected points (P(play) + backups) over a raw projection sum.
    if isinstance(assessment.get("opp"), (int, float)):
        opp_total = float(assessment["opp"])
    else:
        opp_total = sum(p["projected"] for p in data.get("opponent_roster", [])
                        if p.get("starting") and isinstance(p.get("projected"), (int, float)))

    lg = data.get("league") or {}
    wk_line = f"Week {week}" + (f" \u00b7 {data['record']}" if data.get("record") else "")
    kpis = _kpis(opt, opp_total, lg)

    adds = "".join(
        f'<div class="row"><div class="who">{_nm(a["name"])}{_meta(a)}</div>'
        f'<div class="num">{a.get("count", 0):,}<small>adds</small></div></div>' for a in data.get("trending_adds", [])) or '<p class="empty">No trending data.</p>'
    news = _capped([
        f'<div class="row">{_ext(n.get("link", "#"), n.get("headline", ""))}'
        f'<div class="m">{_e(_blurb(n.get("description")))}</div></div>' for n in data.get("news", [])[:15]], 6) or '<p class="empty">No headlines.</p>'

    w = data.get("waivers")
    if w:
        prio = w.get("priority", {}).get("text", "")
        sub = prio.replace("Waiver priority", "priority") if prio else "unclaimed in your league"
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Waiver wire</h2><span class="m">{sub}</span></div>{_waivers(w)}</section>'
    else:
        waiver_html = f'<section class="sheet" id="waiver"><div class="hd"><h2>Most added</h2><span class="m">all leagues, 48h</span></div>{adds}</section>'

    opp = data.get("opponent_name")
    opp_html = f'<div class="sub">vs <b>{_e(opp)}</b></div>' if opp else ""
    gen_iso, gen_human = data.get("generated_at", ""), data.get("generated", "")
    age_html = _age_line(gen_iso, gen_human)
    age_inner = _age_inner(gen_iso, gen_human) or f"Updated {_e(gen_human)}"

    cards = {c["name"]: c for c in assessment.get("cards", [])}
    hero_html = _hero(assessment, data.get("opponent_name", ""), kpis)
    top, bottom = section_nav(checkup=bool(hero_html))
    # Without the hero (no assessment) the strip leads the page and the swaps list stays open.
    loose_kpis = "" if hero_html else kpis
    lineup_html = _lineup(roster, opt, cards, assessment.get("mode") == "gameday", data.get("role_watch"),
                          swaps_open=not hero_html)
    xall = '<button type="button" class="xall" data-xall>Expand all</button>' if roster else ""

    desc = f"Week {week} start/sit, waivers, and win chance for {_e(team)}"
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#090d13">
<meta name="description" content="{desc}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{_e(team)[:12] or 'Fantasy'}">
<title>Week {week} &mdash; {_e(team)}</title>
<script>{HEAD_JS}</script>
<style>{CSS}</style>
</head><body><div class="wrap">

<header><div class="grow"><div class="eb">{_e(wk_line)}</div><h1>{_e(team)}</h1>{opp_html}{age_html}</div>
{settings_button()}</header>

<nav class="top" aria-label="Sections"><ul>{top}</ul></nav>

{settings_panel()}

{_status(data.get("espn"))}
{hero_html}
<div class="cols">{loose_kpis}<div class="col">
<section class="sheet" id="lineup"><div class="hd"><h2>Start / sit</h2><span class="m">your lineup</span>{xall}</div>
{_alerts(roster)}{lineup_html}</section>

<section class="sheet" id="rank"><div class="hd"><h2>Rankings</h2><span class="m">PPR &middot; this week</span></div>{_rankings(data.get("rankings", {}))}</section>
</div><div class="col">
{waiver_html}

<section class="sheet" id="trades"><div class="hd"><h2>Trade targets</h2></div>{_trades(data.get("trades", {}))}</section>

<section class="sheet news" id="news"><div class="hd"><h2>Headlines</h2></div>{news}</section>
</div></div>

<p class="foot"{f' data-generated-at="{_e(gen_iso)}"' if gen_iso else ""}>{age_inner}. Projections average ESPN and Sleeper. Rankings blend that number (65%) with 2025 points per game (35%). Tiers break on a 12% drop. Matchup strength is only what those sources already bake in.</p>
</div>
<nav class="bottom" aria-label="Sections"><ul>{bottom}</ul></nav>
<script>{JS}</script></body></html>"""


def _now_ct() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except Exception:  # no tz database on this machine
        return datetime.now()


def stamp() -> tuple:
    """(human Central label, ISO-8601 with offset) for the build time. The ISO value drives
    the live 'Xh ago' age on the static Pages deploy."""
    now = _now_ct()
    human = now.strftime("%a %b %d, %-I:%M %p %Z").strip()
    return human, now.isoformat(timespec="seconds")


def timestamp() -> str:
    """Central time label only. Prefer stamp() when the page also needs a machine time."""
    return stamp()[0]


def _age_seed(iso: str) -> str:
    """Server-side relative age so the first paint isn't blank before JS runs."""
    try:
        built = datetime.fromisoformat(iso)
        if built.tzinfo is None:
            built = built.replace(tzinfo=_now_ct().tzinfo)
        mins = max(0, int((_now_ct() - built).total_seconds() // 60))
    except Exception:
        return "just now"
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 48:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _age_inner(iso: str, human: str) -> str:
    """'Updated Xm ago · Fri Oct 30, 1:00 PM CDT' — relative span is refreshed by JS."""
    when = _e(human) or _e(iso)
    if not when:
        return ""
    if not iso:
        return f"Updated {when}"
    return (f'<time datetime="{_e(iso)}">Updated <b data-age>{_e(_age_seed(iso))}</b>'
            f" &middot; {when}</time>")


def _age_line(iso: str, human: str) -> str:
    """Header line with data-generated-at so JS can keep the relative age current."""
    inner = _age_inner(iso, human)
    if not inner:
        return ""
    if not iso:
        return f'<p class="age">{inner}</p>'
    return f'<p class="age" data-generated-at="{_e(iso)}">{inner}</p>'
