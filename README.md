# Fantasy companion

A scheduled collector that pulls your ESPN roster, league-wide injury and
add/drop signal, and NFL headlines, then publishes two things:

- `site/index.html` — a dashboard you open on your phone or PC
- `site/brief.md` — a dense text summary you paste into Claude to ask
  start/sit, waiver, and trade questions

The dashboard has six sections: alerts and your lineup, a lineup optimizer,
position rankings across your league's player pool (QB, RB, WR, TE, D/ST, K),
trade targets, most-added players, and headlines.

## How the analysis works

**Lineup optimizer** reads your league's slot structure off your current
roster, fills every slot with the highest-projected healthy player, and
lists the swaps between that and what you have set.

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

Builds Sunday at 7am and 10am Central, and Wednesday at 8am Central after
waivers clear. Edit the cron lines in `.github/workflows/update.yml` to
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

## Running locally

```bash
pip install -r requirements.txt
export LEAGUE_ID=123456789 TEAM_NAME="Your Team"
export ESPN_S2='...' ESPN_SWID='{...}'
python main.py
open site/index.html
```

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
