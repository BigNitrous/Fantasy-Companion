"""ESPN's public site API. No auth, no key."""

from __future__ import annotations
import requests

SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
TIMEOUT = 30


def headlines(limit: int = 15) -> list[dict]:
    try:
        r = requests.get(f"{SITE}/news", params={"limit": limit}, timeout=TIMEOUT)
        r.raise_for_status()
        articles = r.json().get("articles", [])
    except Exception:
        return []

    out = []
    for a in articles:
        link = ""
        links = a.get("links", {}) or {}
        web = links.get("web", {}) or {}
        link = web.get("href", "")
        out.append({
            "headline": a.get("headline", ""),
            "description": a.get("description", ""),
            "published": a.get("published", ""),
            "link": link,
        })
    return out


def league_injuries() -> list[dict]:
    """Every currently-listed injury across the NFL."""
    try:
        r = requests.get(f"{SITE}/injuries", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    out = []
    for team_block in data.get("injuries", []):
        team = team_block.get("displayName", "")
        for item in team_block.get("injuries", []):
            athlete = item.get("athlete", {}) or {}
            out.append({
                "name": athlete.get("displayName", ""),
                "position": (athlete.get("position", {}) or {}).get("abbreviation", ""),
                "team": team,
                "status": item.get("status", ""),
                "detail": (item.get("details", {}) or {}).get("type", ""),
                "comment": item.get("longComment") or item.get("shortComment") or "",
            })
    return out
