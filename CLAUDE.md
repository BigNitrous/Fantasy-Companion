# Fantasy Companion

Static dashboard for one ESPN fantasy football league. GitHub Actions runs
`python main.py`, which writes `site/index.html`, `site/brief.md` and
`site/assessment.md`; Pages publishes them at
https://bignitrous.github.io/Fantasy-Companion/.

## Commands
```bash
python3 test_espn.py                            # ESPN connectivity check (~5s)
python3 main.py                                 # full build into site/ (gitignored)
python3 -m py_compile collector/*.py main.py    # fast syntax check
```

## Constraints (learned the hard way)
- Local Python is Apple's 3.9.6, CI is 3.12. Keep code 3.9-safe: no reused
  quote type and no backslashes inside f-string `{}`; compute the value first.
  `nflreadpy` needs 3.10+ (gated in requirements.txt), so local builds have
  no last-season data; CI does.
- Secrets: `.env` locally (gitignored) and Actions secrets LEAGUE_ID,
  TEAM_NAME, ESPN_S2, ESPN_SWID. Never print or commit them. Before every
  commit scan `git diff --cached` for cookie values.
- Every push to main redeploys; the workflow cancels an in-flight run. Use
  `[skip ci]` in the message for docs-only commits.
- GitHub *scheduled* runs for this repo start 4-6 hours late. Runs from a push
  or Run workflow (workflow_dispatch) start immediately.
- CSS class names collide easily (`.wrap`, `.swap`, `.m`, `.nm`): check the
  existing stylesheet in collector/render.py before adding one.

## Pipeline (main.py order)
usage (nflverse) -> choose the upcoming week (if every game of Sleeper's week
is already in the stats, use the next) -> ESPN fetch (`load_roster_week` for
that week; league slots from settings) -> slate (ESPN scoreboard: opponents,
byes, game days) -> news -> roles (vacated opportunity, adjusted `projected`,
ESPN's number kept as `projected_espn`) -> optimizer -> rankings -> trades ->
waivers -> assessment -> render / brief / assessment.md.

## Modules (collector/)
config, espn_source, sleeper_source, news_source, schedule_source, history
(2025 season, nflreadpy), usage (nflverse CSVs: snap/target/carry share, QB
volume, measured variance), roles (role boost, QB notes, news matching),
optimizer, rankings, trades, waivers, assess (confidence, cards, actions),
brief, render.

## Design decisions
- Role boost = half of the usage-implied gain (ESPN already reacts to injuries),
  capped at 6 points, always displayed next to ESPN's number.
- Confidence = chance the lineup outscores the opponent. Player mean =
  projection x P(play) (Questionable .70, Doubtful .15, Out/bye 0); spread is
  measured from this season's nflverse points; sums over both lineups.
  Outlook = chance a player beats the average starter at his position.
- Optimizer slots come from the league settings (`optimizer.set_league_slots`).
  Inferring them from the roster hid an empty K slot once; don't revert that.
- Not modeled: defensive matchup strength. Say so; don't oversell the score.

## Schedule
Actions cron (UTC): Tue 18:00 (waiver check-up), Wed 13:00, Thu 21:07, Sun
12:00 / 15:00 / 16:00. `ASSESS_MODE` (auto, checkup, gameday, midweek) picks
the lead report; auto = Tuesday check-up, Sunday game day.
Three read-only Claude cloud routines (claude.ai/code/routines, environment
"Test", model claude-sonnet-5-5, no connectors) read the published
assessment.md / brief.md and write a narrative; they run in Anthropic's cloud,
so the Mac does not need to be on:
- Tuesday waiver check-up, cron `0 18 * * 2` UTC (trig_018NShwr3pQX7UU7nbeWqX2N)
- Thursday update, `0 21 * * 4` UTC (trig_01TCdrEbDKHN6d3PN4h1i4Hi)
- Sunday game-day deep dive, `0 16 * * 0` UTC (trig_01JRpdC7QiYVSPnTHRsVcpQT)
Cron is UTC and does not follow daylight saving: after Nov 1 they land an
hour earlier local time; update them then. The two older local Mac tasks
(fantasy-tuesday-checkup, fantasy-sunday-deepdive) are paused.

## Open items
- The cloud routines read whatever the site last built, and GitHub's scheduled
  rebuilds run 4-6 hours late, so a report can be stale (the prompts wait up to
  15 minutes, then label the data's age). Diagnostic of the cloud sandbox
  (2026-10-14): it can read the dashboard and reach ESPN, Sleeper, nflverse and
  PyPI; `gh` has an invalid GH_TOKEN; no LEAGUE_/ESPN_ env vars are set. Its
  GitHub connector reportedly exposes `actions_run_trigger` (untested): if that
  works, make "trigger Update dashboard and wait for it" step 1 of each routine.
  Alternative: put LEAGUE_ID, TEAM_NAME, ESPN_S2, ESPN_SWID in the cloud
  environment so a routine can run `python main.py` itself (user must add them).
- After the first Thursday 21:07 UTC run, compare its start time with the
  top-of-the-hour crons to see whether offsetting the minute helps.
