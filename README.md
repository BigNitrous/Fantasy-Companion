# Fantasy companion

A scheduled collector that pulls your ESPN roster, league-wide injury and
add/drop signal, and NFL headlines, then publishes two things:

- `site/index.html` — a dashboard you open on your phone or PC
- `site/brief.md` — a dense text summary you paste into Claude to ask
  start/sit, waiver, and trade questions

The dashboard has six sections: alerts and your lineup, a lineup optimizer,
a waiver wire built from who's actually unclaimed in your league, position
rankings across your league's player pool (QB, RB, WR, TE, D/ST, K), trade
targets, and headlines.

## How the analysis works

**Lineup optimizer** reads your league's slot structure off your current
roster, fills every slot with the highest-projected healthy player, and
lists the swaps between that and what you have set.

**Waiver wire** looks only at players unclaimed in your league. Each free
agent is scored the same way as the rankings and compared with your roster:
START if he'd beat one of your starters this week, STREAM for a kicker or
defense with the better matchup, BENCH if he's better than someone on your
bench right now, STASH if his rest-of-season projection is well ahead of
your most droppable player. Every pickup names the drop that makes room.
Below that: Sleeper's most-added players that are still unclaimed here,
players rivals just dropped (often a panic move), your most droppable
bench players, and the league's recent transactions. The header shows your
waiver priority or FAAB left, standing, and ESPN's playoff odds.

**Usage and role changes.** Projections alone miss who is actually getting
the ball. For every skill player the collector pulls nflverse data (no extra
packages) and works out snap share, target share, carry share, and targets
and carries per game over his last four games, plus last week's line, and
which quarterback is throwing to him and how often his team passes. When a
teammate is out or on IR, his carries and targets are redistributed to the
healthy players at his position (the next man up gets a guaranteed floor)
and converted to projected points. That gain is added to ESPN's projection
at half strength, capped at 6 points, and always shown next to ESPN's
number ("ESPN 13.6 -> 16.1 with the role change"), so you can overrule it.
The optimizer, rankings and waiver wire all use the adjusted number. ESPN
headlines are matched to players by name and attached as evidence.

**Weekly assessment** is the routine check on the whole week:

- *Confidence score* is the chance your lineup outscores this week's
  opponent. Each player is a distribution: mean = projection x chance to play
  (Questionable 70%, Doubtful 15%, Out or bye 0), spread = the measured
  week-to-week variation of his position this season. Add up your team and
  theirs and the gap over the combined spread is a win probability. 50 is a
  coin flip. It also shows what the score becomes if you make the
  recommended changes, and a score for each day (Thursday, Sunday, Monday)
  against an average team's starters.
- *Do this* lists lineup fixes (a starter on a bye or out), swaps, and the
  best pickups. Each pickup is scored by what it actually does to your
  optimal lineup, and names the drop that makes room.
- *Player cards* open under every player on your roster: outlook (chance he
  outscores the average starter at his position), last week's targets,
  catches, carries and snaps against his recent baseline, signed reasons
  (target share up or down, snaps rising, role boost, injury, quarterback
  change) and the news that matters.

It leads with the **Tuesday check-up** on Tuesdays (before waivers), the
**Game-day report** on Sundays (cards open for every player), and a general
outlook otherwise. The workflow runs Tuesday 1pm CT, Wednesday 8am CT, and
Sunday 7am, 10am and 11am CT; use Run workflow and pick a mode to force one.
The same content is written to `site/assessment.md` for Claude to read.

Matchup strength (how good the defense is against a position) is not
modeled; the score is arithmetic on ESPN's projections, not a prediction.

**Position rankings** score everyone in your league (all rosters plus free
agents) as 65% this week's ESPN projection + 35% last season's PPR points
per game. Last-season data comes from nflverse; kicker and D/ST points are
computed with ESPN's default scoring since nflverse doesn't score those.
Your players are highlighted.

**Trade targets** compares your best starter at each position against the
league median starter to find where you're thin, flags bench players of
yours who'd start on other teams, lists players at your need positions on
teams that have more above-median options than starting slots, and marks
buy-low candidates whose projection is well under their 2025 pace.

All of this is heuristic. It's meant to surface candidates for you and
Claude to argue about, not to make the decision for you.

No server. It runs on GitHub Actions and costs nothing.

## Setup

**1. Create the repo.** Make a new GitHub repo and push these files to it.

**2. Find your league ID.** Open your league on fantasy.espn.com. The URL
looks like `.../league?leagueId=123456789`. That number is your league ID.

**3. Get your cookies** (private leagues only — skip if your league is
public). While logged in on fantasy.espn.com:

- Chrome or Edge: F12 → Application tab → Storage → Cookies → `https://fantasy.espn.com`
- Safari: enable the Develop menu in Settings → Advanced, then Develop →
  Show Web Inspector → Storage → Cookies

Copy the values of `espn_s2` and `SWID`. The `espn_s2` value is long and
URL-encoded; copy the whole thing. `SWID` includes the curly braces.

**4. Add secrets.** In the repo: Settings → Secrets and variables →
Actions → New repository secret. Add:

| Name | Value |
|---|---|
| `LEAGUE_ID` | the number from step 2 |
| `TEAM_NAME` | your team name as it appears in ESPN |
| `ESPN_S2` | from step 3, private leagues only |
| `ESPN_SWID` | from step 3, private leagues only |

**5. Turn on Pages.** Settings → Pages → Source: **GitHub Actions**.

**6. Run it.** Actions tab → Update dashboard → Run workflow. When it
finishes, your URL is `https://<username>.github.io/<repo>/`.

On your phone, open that URL and use Share → Add to Home Screen. It behaves
like an app after that.

## Schedule

Builds Tuesday at 1pm Central (the waiver check-up), Wednesday at 8am Central
after waivers clear, and Sunday at 7am, 10am and 11am Central. Edit the cron lines in `.github/workflows/update.yml` to
change that, or hit Run workflow any time.

## Using the brief

Open `site/brief.md` in the repo, copy it, and paste it into Claude with
whatever you want to know — which flex to start, whether a bench player has
passed a starter, who's worth a waiver claim. It includes your roster,
your opponent's starters, top free agents, and league-wide add/drop trends,
so you don't have to re-explain your league each week.

## Repo visibility

Pages on a private repo requires a paid GitHub plan. Two options:

- **Public repo.** Your cookies live in Actions secrets and never appear in
  the output, so the only thing exposed is your roster.
- **Private repo + Cloudflare Pages.** Free, and lets you password-protect
  the URL. Point Cloudflare Pages at the repo and set the build output
  directory to `site`.

## Working on it with Claude Code (recommended)

Editing files through GitHub's web UI and waiting on Actions for every
change is slow. Clone the repo to your Mac once and let Claude Code edit,
test, and push:

```bash
git clone https://github.com/BigNitrous/Fantasy-Companion.git
cd Fantasy-Companion
cp .env.example .env      # then fill in your real values
pip3 install -r requirements.txt
python3 test_espn.py      # confirms ESPN works in ~5 seconds
claude                    # opens Claude Code in this folder
```

`.env` is gitignored, so your cookies never leave your machine. Claude
Code can run `python3 test_espn.py` to check a fix, `python3 main.py` to
build the full page, and `git push` to deploy. Every push triggers the
workflow automatically, so you only touch GitHub's website to read the
finished dashboard.

## Diagnosing ESPN problems

`python3 test_espn.py` prints exactly why a connection failed, in plain
English. The dashboard shows the same message at the top of the page when
ESPN is down, so you don't need to dig through Actions logs.

Common causes: a cookie value pasted with a trailing line break (fixed in
code now), `SWID` missing its curly braces, `espn_s2` truncated on copy,
or cookies from a different ESPN account than the one in the league.

## Settings

The gear at the end of the section nav opens a Settings panel with a
theme switch (auto/light/dark) and text size (small to XL). Choices are
saved in the browser on that device only.

## If ESPN fails

ESPN's fantasy API is undocumented and changes without notice. The
collector catches failures and still builds the page from Sleeper and
ESPN's public news feed, so a broken cookie degrades the dashboard rather
than breaking the build. Cookies expire eventually — if your roster
disappears, re-copy them from step 3.

## Not built yet

Podcast transcription. The plan is to pull RSS feeds, transcribe new
episodes with `faster-whisper` on your PC, and summarize only the segments
that mention players on your roster. That needs real compute, so it runs
locally rather than in Actions.
