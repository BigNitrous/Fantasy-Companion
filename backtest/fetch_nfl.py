"""One-off: read NFL.com's public weekly projections pages (allowed by its robots.txt).

Saves every table row as cells (class + text) to backtest/data/nfl_rows.json, and
one raw page (gzipped) so the columns can be identified. Polite: one request a second.
"""

import gzip
import json
import os
import time
from html.parser import HTMLParser

import requests

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
URL = "https://fantasy.nfl.com/research/projections"
UA = {"User-Agent": "Mozilla/5.0 (fantasy-companion backtest; personal use)"}


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.head, self.cur, self.cell, self.in_head = [], [], None, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "thead":
            self.in_head = True
        elif tag == "tr":
            self.cur = []
        elif tag in ("td", "th") and self.cur is not None:
            self.cell = {"c": a.get("class", ""), "t": "", "id": ""}
        elif tag == "a" and self.cell is not None and "playerId=" in (a.get("href") or ""):
            self.cell["id"] = (a.get("href") or "").split("playerId=")[-1].split("&")[0]
        elif tag == "span" and self.cell is not None and "playerId-" in (a.get("class") or ""):
            self.cell["id"] = self.cell["id"] or (a.get("class") or "").split("playerId-")[-1].split()[0]

    def handle_endtag(self, tag):
        if tag == "thead":
            self.in_head = False
        elif tag in ("td", "th") and self.cell is not None and self.cur is not None:
            self.cell["t"] = " ".join(self.cell["t"].split())
            self.cur.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.cur is not None:
            (self.head if self.in_head else self.rows).append(self.cur)
            self.cur = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["t"] += data


def page(week, pos, offset, keep=None):
    r = requests.get(URL, headers=UA, timeout=60, params={
        "position": pos, "statCategory": "projectedStats", "statSeason": 2026,
        "statType": "weekProjectedStats", "statWeek": week, "offset": offset, "sort": "projectedPts"})
    time.sleep(1.0)
    if r.status_code != 200:
        return None, None, r.status_code
    if keep:
        with gzip.open(keep, "wb") as f:
            f.write(r.content)
    p = Rows()
    p.feed(r.text)
    return p.head, p.rows, 200


def main():
    os.makedirs(OUT, exist_ok=True)
    out, heads = [], {}
    plan = [("O", 14), ("7", 2), ("8", 2)]          # offense (~350 players), kickers, defenses
    for week in range(1, 7):
        for pos, pages in plan:
            for i in range(pages):
                keep = os.path.join(OUT, "nfl_sample.html.gz") if (week == 5 and pos == "O" and i == 0) else None
                head, rows, code = page(week, pos, 1 + 25 * i, keep)
                if code != 200 or not rows:
                    print(f"week {week} {pos} page {i}: {code}, {0 if not rows else len(rows)} rows")
                    break
                heads.setdefault(pos, head)
                out += [{"week": week, "pos_group": pos, "cells": r} for r in rows if len(r) > 3]
        print(f"week {week}: {sum(1 for x in out if x['week'] == week)} rows")
    with open(os.path.join(OUT, "nfl_rows.json"), "w") as f:
        json.dump({"heads": heads, "rows": out}, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
