"""Championship Plan page.

The weekly dashboard stays a lineup tool. This module turns the checked-in
plan (content/championship-plan.md plus content/championship_schedule.json)
into site/plan.html, using the same theme and nav as the dashboard. main.py
writes it on every build, so the Update dashboard workflow publishes it
with the rest of site/.
"""

from __future__ import annotations

import json
import os
import re

from . import render

_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_MD = os.path.join(_ROOT, "content", "championship-plan.md")
_JSON = os.path.join(_ROOT, "content", "championship_schedule.json")

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TOKEN = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`")
_TONE = re.compile(r"^\{(good|warn|bad|muted)\}")
_OL = re.compile(r"^(\d+)\.\s+")
_HEAD = re.compile(r"^(#{2,3})\s+(.*)$")

PLAN_CSS = """
/* Championship Plan: long-form reading on the dashboard's tokens */
.cp-toc{display:flex;gap:6px;margin:0 -12px 12px;padding:8px 12px;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;
  position:sticky;top:0;z-index:15;background:var(--paper);border-bottom:1px solid var(--line)}
.cp-toc::-webkit-scrollbar{display:none}
.cp-toc a{flex:none;display:inline-block;padding:7px 12px;border-radius:999px;background:var(--sheet);border:1px solid var(--line);color:var(--ink2);text-decoration:none;font-size:.75rem;font-weight:700;white-space:nowrap}
.cp-toc a:hover{color:var(--ink);background:var(--fill)}
.cp-sec{scroll-margin-top:60px}
.cp-prose{padding:0 var(--pad) 4px;color:var(--ink2)}
.cp-prose p{margin:0 0 10px}
.cp-prose ul,.cp-prose ol{margin:0 0 12px;padding-left:1.15rem}
.cp-prose li{margin:6px 0}
.cp-prose b{color:var(--ink)}
.cp-prose code{font-size:.85em}
.cp-h3{margin:0;padding:14px var(--pad) 6px;font-size:var(--t-md);font-weight:800;letter-spacing:-.01em;color:var(--ink)}
.cp-call{margin:2px 12px 14px;padding:11px 13px;border-radius:var(--r-md);border:1px solid var(--line);background:var(--well);color:var(--ink2);font-size:var(--t-sm)}
.cp-call .cp-prose{padding:0}
.cp-call p:last-child,.cp-call ul:last-child,.cp-call ol:last-child{margin-bottom:0}
.cp-call.info{background:var(--accent-soft);border-color:var(--accent-line)}
.cp-call.warning{background:var(--quest-soft);border-color:var(--quest-line)}
.cp-call.ok{background:var(--green-soft);border-color:var(--green-line)}
.cp-call.superseded{background:var(--out-soft);border-color:var(--out-line)}
.cp-kicker{display:block;font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px;color:var(--ink)}
.cp-call.info .cp-kicker{color:var(--accent-ink)}
.cp-call.warning .cp-kicker{color:var(--quest)}
.cp-call.ok .cp-kicker{color:var(--green-ink)}
.cp-call.superseded .cp-kicker{color:var(--out)}
.cp-check{list-style:none;margin:0 0 6px;padding:0}
.cp-check li{display:flex;gap:10px;align-items:flex-start;padding:10px var(--pad);border-top:1px solid var(--line);color:var(--ink2);font-size:var(--t-sm)}
.cp-box{width:16px;height:16px;margin-top:2px;border-radius:5px;border:1.5px solid var(--fill2);flex:none}
.cp-check li[data-done="yes"] .cp-box{position:relative;background:var(--green);border-color:var(--green)}
.cp-check li[data-done="yes"] .cp-box::after{content:"✓";position:absolute;inset:0;display:grid;place-items:center;color:var(--on-green);font-size:.7rem;font-weight:900}
.cp-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-bottom:10px}
.cp-table{width:100%;border-collapse:collapse;font-size:var(--t-sm);font-variant-numeric:tabular-nums}
.cp-table th,.cp-table td{padding:8px 10px;border-top:1px solid var(--line);text-align:left;vertical-align:top}
.cp-table th:first-child,.cp-table td:first-child{padding-left:var(--pad)}
.cp-table th{font-size:.625rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);background:var(--well)}
.cp-kv td:first-child{width:8.75rem;font-weight:700;color:var(--ink)}
.cp-matrix{min-width:540px}
.cp-matrix td:first-child,.cp-matrix th:first-child{position:sticky;left:0;background:var(--sheet);z-index:1;min-width:8.5rem}
.cp-matrix th:first-child{background:var(--well)}
.cp-fit td,.cp-fit th{white-space:nowrap}
.cp-fit td:nth-child(5),.cp-fit th:nth-child(5){white-space:normal}
.cp-good{color:var(--green-ink);font-weight:700}
.cp-tough,.cp-warn{color:var(--quest);font-weight:700}
.cp-bad{color:var(--out);font-weight:700}
.cp-muted{color:var(--muted);font-weight:600}
.cp-grid{display:grid;grid-template-columns:1fr;gap:10px;padding:0 12px 14px}
.cp-card{margin:0;background:var(--well)}
.cp-card .cp-scroll{margin-bottom:0}
.cp-card .hd{padding:12px var(--pad) 4px}
.cp-card .hd h3{font-size:var(--t-md)}
.cp-tag{margin:0;padding:0 var(--pad) 8px;font-size:.75rem;color:var(--muted)}
.cp-group{margin:0;padding:12px var(--pad) 8px;font-size:var(--t-xs);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.cp-hint{padding:0 var(--pad) 12px;color:var(--muted);font-size:var(--t-sm)}
@media(min-width:800px){.cp-grid{grid-template-columns:1fr 1fr}}
@media(min-width:1024px){
  .cp-toc{position:static;flex-wrap:wrap;overflow:visible;margin:0 0 16px;padding:0;border-bottom:0;background:transparent}
  .cp-sec{scroll-margin-top:76px}
  .wrap.cp-wrap{max-width:980px}
}
"""


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _safe_href(url: str):
    u = (url or "").strip()
    if u.startswith("https://") or u.startswith("http://"):
        return u, True
    if u.startswith("#") or u.startswith("index.html") or u.startswith("plan.html"):
        return u, False
    return "", False


def _inline_html(text: str) -> str:
    out = []
    pos = 0
    for match in _TOKEN.finditer(text):
        out.append(render._e(text[pos:match.start()]))
        if match.group(1) is not None:
            out.append("<b>" + render._e(match.group(1)) + "</b>")
        elif match.group(2) is not None:
            href, external = _safe_href(match.group(3) or "")
            label = render._e(match.group(2))
            if href and external:
                out.append('<a href="' + render._e(href) + '" target="_blank" rel="noopener noreferrer">' + label + "</a>")
            elif href:
                out.append('<a href="' + render._e(href) + '">' + label + "</a>")
            else:
                out.append(label)
        else:
            out.append("<code>" + render._e(match.group(4) or "") + "</code>")
        pos = match.end()
    out.append(render._e(text[pos:]))
    return "".join(out)


def inline(text: str) -> str:
    raw = (text or "").strip()
    tone = ""
    match = _TONE.match(raw)
    if match:
        tone = match.group(1)
        raw = raw[match.end():].lstrip()
    html = _inline_html(raw)
    if tone == "warn":
        tone = "tough"
    if tone:
        return '<span class="cp-' + tone + '">' + html + "</span>"
    return html


def _plain(text: str) -> str:
    raw = _TONE.sub("", text or "").strip()
    raw = re.sub(r"\*\*(.+?)\*\*", r"\1", raw)
    raw = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
    raw = raw.replace("`", "")
    return raw


def _slug(text: str, used: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", _plain(text).lower()).strip("-") or "section"
    slug = base
    n = 2
    while slug in used:
        slug = base + "-" + str(n)
        n += 1
    used.add(slug)
    return slug


def _list_kind(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("- [ ] ") or stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
        return "check"
    if stripped.startswith("- "):
        return "ul"
    if _OL.match(stripped):
        return "ol"
    return ""


def _split_row(line: str) -> list:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_sep(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped or "-" not in stripped:
        return False
    core = stripped.strip("|").replace("|", "").replace(":", "").replace("-", "").replace(" ", "")
    return core == ""


def parse_blocks(text: str) -> list:
    lines = text.replace("\r\n", "\n").split("\n")
    blocks = []
    buf = []
    i = 0
    n = len(lines)

    def flush():
        if buf:
            blocks.append({"type": "p", "text": " ".join(buf).strip()})
            buf.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush()
            i += 1
            continue
        if stripped == "{{matrix}}":
            flush()
            blocks.append({"type": "matrix"})
            i += 1
            continue
        if stripped == "{{schedules}}":
            flush()
            blocks.append({"type": "schedules"})
            i += 1
            continue
        if stripped.startswith(":::"):
            flush()
            if stripped == ":::":
                i += 1
                continue
            rest = stripped[3:].strip()
            tone, _, title = rest.partition(" ")
            inner = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                inner.append(lines[i])
                i += 1
            if i < n and lines[i].strip() == ":::":
                i += 1
            blocks.append({"type": "callout", "tone": tone.lower() or "info", "title": title.strip(), "blocks": parse_blocks("\n".join(inner))})
            continue
        head = _HEAD.match(stripped)
        if head:
            flush()
            level = len(head.group(1))
            blocks.append({"type": "h2" if level == 2 else "h3", "text": head.group(2).strip()})
            i += 1
            continue
        if "|" in stripped and i + 1 < n and _is_sep(lines[i + 1]):
            flush()
            header = _split_row(stripped)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip() and not lines[i].strip().startswith(":::"):
                rows.append(_split_row(lines[i]))
                i += 1
            width = len(header)
            norm_rows = []
            for row in rows:
                if len(row) < width:
                    row = row + [""] * (width - len(row))
                norm_rows.append(row[:width])
            blocks.append({"type": "table", "header": header, "rows": norm_rows})
            continue
        kind = _list_kind(line)
        if kind:
            flush()
            items = []
            while i < n and _list_kind(lines[i]) == kind:
                item_line = lines[i].lstrip()
                done = None
                if kind == "check":
                    done = item_line.startswith("- [x] ") or item_line.startswith("- [X] ")
                    item_line = item_line[6:]
                elif kind == "ul":
                    item_line = item_line[2:]
                else:
                    item_line = _OL.sub("", item_line)
                i += 1
                extra = []
                while i < n and (lines[i].startswith("  ") or lines[i].startswith("\t")) and lines[i].strip():
                    extra.append(lines[i].strip())
                    i += 1
                text_item = " ".join([item_line.strip()] + extra).strip()
                items.append({"text": text_item, "done": done})
            blocks.append({"type": kind, "items": items})
            continue
        buf.append(stripped)
        i += 1
    flush()
    return blocks


def _blocks_html(blocks: list, schedules: dict) -> str:
    parts = []
    for block in blocks:
        kind = block["type"]
        if kind == "p":
            parts.append('<div class="cp-prose"><p>' + inline(block["text"]) + "</p></div>")
        elif kind == "h3":
            parts.append('<h3 class="cp-h3">' + inline(block["text"]) + "</h3>")
        elif kind == "ul":
            items = "".join("<li>" + inline(item["text"]) + "</li>" for item in block["items"])
            parts.append('<div class="cp-prose"><ul>' + items + "</ul></div>")
        elif kind == "ol":
            items = "".join("<li>" + inline(item["text"]) + "</li>" for item in block["items"])
            parts.append('<div class="cp-prose"><ol>' + items + "</ol></div>")
        elif kind == "check":
            rows = []
            for item in block["items"]:
                flag = "yes" if item["done"] else "no"
                rows.append('<li data-done="' + flag + '"><span class="cp-box" aria-hidden="true"></span><span>' + inline(item["text"]) + "</span></li>")
            parts.append('<ul class="cp-check">' + "".join(rows) + "</ul>")
        elif kind == "table":
            parts.append(_table_html(block["header"], block["rows"], "cp-kv" if len(block["header"]) == 2 else ""))
        elif kind == "callout":
            tone = block["tone"] if block["tone"] in ("info", "warning", "ok", "superseded") else "info"
            kicker = '<span class="cp-kicker">' + inline(block["title"]) + "</span>" if block["title"] else ""
            parts.append('<div class="cp-call ' + tone + '">' + kicker + _blocks_html(block["blocks"], schedules) + "</div>")
        elif kind == "matrix":
            parts.append(_matrix_html(schedules))
        elif kind == "schedules":
            parts.append(_schedules_html(schedules))
    return "".join(parts)


def _table_html(header: list, rows: list, extra: str) -> str:
    klass = "cp-table " + extra if extra else "cp-table"
    head = "".join("<th>" + inline(cell) + "</th>" for cell in header)
    body = []
    for row in rows:
        body.append("<tr>" + "".join("<td>" + inline(cell) + "</td>" for cell in row) + "</tr>")
    return '<div class="cp-scroll"><table class="' + klass.strip() + '"><thead><tr>' + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"


def _tone_rank(rank: int) -> str:
    if rank >= 23:
        return "cp-good"
    if rank <= 10:
        return "cp-tough"
    return ""


def _rank_label(rank: int, opp: str, with_words: bool) -> str:
    if opp == "BYE" or not rank:
        return "BYE" if opp == "BYE" else render._e(opp)
    if with_words:
        if rank >= 23:
            text = "#" + str(rank) + " Good"
        elif rank <= 10:
            text = "#" + str(rank) + " Tough"
        else:
            text = "#" + str(rank) + " Neutral"
    else:
        text = opp + " #" + str(rank)
    klass = _tone_rank(rank)
    safe = render._e(text)
    if klass:
        return '<span class="' + klass + '">' + safe + "</span>"
    return safe


def _pts(value) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return "&mdash;"


def _player_table(player: dict, playoff_only: bool) -> str:
    rows = []
    for game in player.get("weeks") or []:
        week = int(game.get("w") or 0)
        if playoff_only and week < 15:
            continue
        opp = game.get("opp") or ""
        rank = int(game.get("rank") or 0)
        if opp == "BYE":
            cells = ["W" + str(week), "BYE", "", "", ""]
        else:
            cells = [
                "W" + str(week),
                render._e(opp),
                _rank_label(rank, opp, True),
                _pts(game.get("pts")),
                render._e(game.get("site") or ""),
            ]
        rows.append("<tr>" + "".join("<td>" + cell + "</td>" for cell in cells) + "</tr>")
    if not rows:
        return ""
    head = "".join("<th>" + label + "</th>" for label in ("Wk", "Opp", "DvP", "Pts/g", "Site"))
    note = player.get("note") or ""
    tag = '<p class="cp-tag">' + render._e(note) + "</p>" if note else ""
    who = render._e(player.get("name") or "")
    meta = render._e((player.get("pos") or "") + " · " + (player.get("team") or ""))
    table = '<div class="cp-scroll"><table class="cp-table cp-fit"><thead><tr>' + head + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    return '<article class="sheet cp-card"><div class="hd"><h3>' + who + '</h3><span class="m">' + meta + "</span></div>" + tag + table + "</article>"


def _cards(schedules: dict, playoff_only: bool) -> str:
    grouped = {}
    for player in schedules.get("players") or []:
        if playoff_only is False and player.get("playoff_card_only"):
            continue
        card = _player_table(player, playoff_only)
        if not card:
            continue
        grouped.setdefault(player.get("group") or "Other", []).append(card)
    parts = []
    order = list(schedules.get("groups") or [])
    for name in grouped:
        if name not in order:
            order.append(name)
    for name in order:
        cards = grouped.get(name) or []
        if not cards:
            continue
        parts.append('<h3 class="cp-group">' + render._e(name) + "</h3>")
        parts.append('<div class="cp-grid">' + "".join(cards) + "</div>")
    return "".join(parts)


def _schedules_html(schedules: dict) -> str:
    playoffs = _cards(schedules, True)
    full = _cards(schedules, False)
    return (
        '<div class="pos" role="tablist">'
        '<button type="button" role="tab" data-pos="po" aria-selected="true">Playoffs W15–17</button>'
        '<button type="button" role="tab" data-pos="full" aria-selected="false">Rest of season W10–17</button>'
        "</div>"
        '<p class="cp-hint">Playoffs is the default. Rest of season adds Weeks 10–14 from the same file.</p>'
        '<div class="panel" data-pos="po" data-active>' + playoffs + "</div>"
        '<div class="panel" data-pos="full">' + full + "</div>"
    )


def _matrix_html(schedules: dict) -> str:
    body = []
    for player in schedules.get("players") or []:
        by_week = {int(game.get("w") or 0): game for game in player.get("weeks") or []}
        if not all(week in by_week for week in (15, 16, 17)):
            continue
        cells = []
        who = render._e(player.get("name") or "") + " (" + render._e(player.get("team") or "") + ")"
        cells.append("<td>" + who + "<div class=\"m\">" + render._e(player.get("group") or "") + "</div></td>")
        cells.append("<td>" + render._e(player.get("pos") or "") + "</td>")
        for week in (15, 16, 17):
            game = by_week[week]
            opp = game.get("opp") or ""
            rank = int(game.get("rank") or 0)
            cells.append("<td>" + _rank_label(rank, opp, False) + "</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    head = "".join("<th>" + label + "</th>" for label in ("Player", "Pos", "W15", "W16", "W17"))
    return '<div class="cp-scroll"><table class="cp-table cp-matrix"><thead><tr>' + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"


def _page_body(markdown: str, schedules: dict) -> str:
    text = _COMMENT.sub("", markdown).strip()
    blocks = parse_blocks(text)
    sections = []
    current = {"title": "", "blocks": []}
    for block in blocks:
        if block["type"] == "h2":
            if current["title"] or current["blocks"]:
                sections.append(current)
            current = {"title": block["text"], "blocks": []}
        else:
            current["blocks"].append(block)
    if current["title"] or current["blocks"]:
        sections.append(current)

    used = set()
    toc = []
    sheets = []
    for section in sections:
        title = section["title"]
        inner = _blocks_html(section["blocks"], schedules)
        if title:
            slug = _slug(title, used)
            toc.append('<a href="#' + slug + '">' + render._e(_plain(title)) + "</a>")
            sheets.append('<section class="sheet cp-sec" id="' + slug + '"><div class="hd"><h2>' + inline(title) + "</h2></div>" + inner + "</section>")
        elif inner:
            sheets.append('<section class="sheet cp-sec">' + inner + "</section>")
    toc_html = '<div class="cp-toc">' + "".join(toc) + "</div>" if toc else ""
    return toc_html + "".join(sheets)


def build(generated: str = "", generated_at: str = "") -> str:
    markdown = _read(_MD)
    with open(_JSON, encoding="utf-8") as handle:
        schedules = json.load(handle)
    body = _page_body(markdown, schedules)
    top, bottom = render.section_nav(active="plan", checkup=True, root="index.html")
    age = render._age_line(generated_at, generated)
    foot_age = render._age_inner(generated_at, generated)
    if foot_age:
        published = " Published with the dashboard build: " + foot_age + "."
    else:
        published = ""
    page = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#090d13">
<meta name="description" content="Advisory championship plan for The Big Leagues. You decide.">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Plan">
<title>Championship Plan — Deshaun, Don't Touchdown there</title>
<script>__HEADJS__</script>
<style>__CSS____PLANCSS__</style>
</head><body><div class="wrap cp-wrap">
<header><div class="grow"><div class="eb">The Big Leagues · advisory</div><h1>Championship Plan</h1>
<div class="sub">Deshaun, Don't Touchdown there · <a href="index.html">Weekly dashboard</a> · advice dated Nov 8, 2026</div>
__AGE__</div>
__GEAR__</header>
<nav class="top" aria-label="Sections"><ul>__TOP__</ul></nav>
__SETTINGS__
__BODY__
<p class="foot">This page advises. You set the lineup, the offers, and the claims. Defense ranks are the Nov 3 working file (nflverse Weeks 1–8) and were not rebuilt on Nov 8. The live record and this week's optimizer stay on the weekly dashboard.__PUBLISHED__</p>
</div>
<nav class="bottom" aria-label="Sections"><ul>__BOTTOM__</ul></nav>
<script>__JS__</script></body></html>"""
    page = page.replace("__HEADJS__", render.HEAD_JS)
    page = page.replace("__CSS__", render.CSS)
    page = page.replace("__PLANCSS__", PLAN_CSS)
    page = page.replace("__AGE__", age)
    page = page.replace("__GEAR__", render.settings_button())
    page = page.replace("__TOP__", top)
    page = page.replace("__SETTINGS__", render.settings_panel())
    page = page.replace("__BODY__", body)
    page = page.replace("__PUBLISHED__", published)
    page = page.replace("__BOTTOM__", bottom)
    page = page.replace("__JS__", render.JS)
    return page
