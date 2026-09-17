"""Sleeper's API is public, unauthenticated, and unmetered. It's the best
free source for league-wide add/drop signal and injury designations."""

from __future__ import annotations
import requests

BASE = "https://api.sleeper.app/v1"
TIMEOUT = 30

_players_cache = None


def current_week() -> int:
    try:
        r = requests.get(f"{BASE}/state/nfl", timeout=TIMEOUT)
        r.raise_for_status()
        state = r.json()
        return int(state.get("week") or state.get("display_week") or 1)
    except Exception:
        return 1


def all_players() -> dict:
    """~5MB payload. Fetched once per run and reused."""
    global _players_cache
    if _players_cache is not None:
        return _players_cache
    try:
        r = requests.get(f"{BASE}/players/nfl", timeout=90)
        r.raise_for_status()
        _players_cache = r.json()
    except Exception:
        _players_cache = {}
    return _players_cache


def _index_by_name(players: dict) -> dict:
    idx = {}
    for pid, p in players.items():
        name = (p.get("full_name") or "").strip().lower()
        if name:
            idx[name] = p
    return idx


def injuries_for(names: list[str]) -> dict:
    """Maps player name -> injury detail from Sleeper."""
    idx = _index_by_name(all_players())
    out = {}
    for n in names:
        p = idx.get(n.strip().lower())
        if not p:
            continue
        status = p.get("injury_status")
        if status:
            out[n] = {
                "status": status,
                "body_part": p.get("injury_body_part") or "",
                "notes": p.get("injury_notes") or "",
            }
    return out


def trending(kind: str = "add", hours: int = 48, limit: int = 25) -> list[dict]:
    players = all_players()
    try:
        r = requests.get(
            f"{BASE}/players/nfl/trending/{kind}",
            params={"lookback_hours": hours, "limit": limit},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        rows = r.json()
    except Exception:
        return []

    out = []
    for row in rows:
        p = players.get(str(row.get("player_id")), {})
        if not p.get("full_name"):
            continue
        out.append({
            "name": p["full_name"],
            "position": p.get("position", ""),
            "team": p.get("team", "") or "FA",
            "count": row.get("count", 0),
            "injury": p.get("injury_status") or "",
        })
    return out
