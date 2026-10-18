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
is final on ESPN's scoreboard, use the next) -> ESPN fetch (`load_roster_week` for
that week; league slots and scoring from settings) -> slate (ESPN scoreboard:
opponents, byes, game days) -> news -> sources (Sleeper projection scored with
the league's rules, averaged with ESPN's into `projected`; ESPN's own number in
`projected_espn`, each source in `sources`) -> roles (vacated opportunity, small
boost added to `projected`) -> optimizer -> rankings -> trades -> waivers ->
assessment -> render / brief / assessment.md.

## Modules (collector/)
config, espn_source, sleeper_source, news_source, schedule_source, sources
(Sleeper/RotoWire projections + ffopportunity usage number, blend), history
(2025 season, nflreadpy), usage (nflverse CSVs: snap/target/carry share, QB
volume, measured variance), roles (role boost, QB notes, news matching),
expect (per-player expected points: P(play), momentum, kickoff-aware backups),
optimizer, rankings, trades, waivers, assess (confidence, cards, actions),
brief, render.

## Design decisions
- Projection = plain average of ESPN and Sleeper (RotoWire's numbers; Sleeper
  publishes projected stats, scored here with the league's rules). Backtest,
  2026 wks 1-5, players who played: ESPN missed by 6.16 pts, Sleeper 6.07; wks
  3-5 average 5.99 vs ESPN 6.05. Fitted weights swung week to week, so equal
  weights (Clemen 1989; Armstrong 2001). ffopportunity expected points ("usage
  X/g") tested worse (6.43) and adding it didn't help: shown, not blended.
  NFL.com has no public projections any more (old research page redirects; the
  v1 API 404s). A source split (3+ pts apart) is shown but did not predict
  bigger misses, so it doesn't widen the spread.
- Role boost = 15% of the usage-implied gain, capped at 6 (was 50%). On top of
  the blend only ~13% showed up (95% range -40% to 65%). Role watch and the
  waiver "bigger role" note use inherited carries+targets (2+/game) instead.
- Usage momentum is off (MOMENTUM_WEIGHT 0): players whose usage jumped did
  ~1.9 pts worse than projected next week, drops ~2.5 better (both weeks, WRs
  most). Don't turn it back on without a new backtest.
- Backtest data and scripts live on the `backtest` branch (GitHub job saves
  ESPN box scores, Sleeper projections, league scoring). The `preview` branch
  runs a full build with the secrets and commits the output, without deploying:
  push a branch to `preview` to test changes on real data.
- One expected-points model (`collector/expect.py`) drives the optimizer, the
  waiver wire and the confidence meter, so a recommended move never lowers the
  meter. Player mean = projection x P(play) x LIMITED (Questionable .74, QB
  Questionable .40, Doubtful .02, Out/bye 0; a tagged player who plays scores
  .85 of his projection). From 2022-26 injury reports + snap counts:
  starters tagged Questionable played 74% (RB/WR/TE), QBs 40%, Doubtful 1%;
  Q players who played scored 80-84% of normal. Friday practice also predicts
  play (full 88%, limited 70%, none 53%) - not used yet. A starter who might not play is credited with a
  bench backup only if the backup's game kicks off at or after his (swap at
  inactives); otherwise he counts at P(play). Example that drove this: McLaurin
  (Questionable, Monday night, no later backup) vs Bernard (Sunday) - raw
  projections said start McLaurin, the meter said that lowered the win chance.
  The optimizer tries uncertain players in and out (up to 2^6 lineups).
- Confidence = chance the lineup outscores the opponent, from those means; spread
  is measured from this season's nflverse points (backtest: QB-TE spreads match
  real misses; K 5.6 and D/ST 5.4 are measured fallbacks); sums over both lineups (the
  opponent's backups are credited the same way). Under the meter, "Injury risk"
  lines say how each uncertain starter is counted and what starting a benched
  questionable player would do to the win chance (`assess.risk_lines`).
  Outlook = chance a player beats the average starter at his position (no
  backup credit).
- Week choice (`main._week_finished`): advance past Sleeper's week only when
  ESPN's scoreboard shows every game final. The old test (latest week in the
  nflverse stats) fired after Thursday night's game, so Fri-Sun builds,
  including the Sunday game-day runs, assessed next week. Fixed 2026-10-16.
- Waivers (`waivers._judge`): each add/drop pair is judged by re-running the
  optimizer with the swap made (week_gain) plus the rest-of-season change
  (ros_gain). The verdict rules are antisymmetric, so following the advice
  can't make the next build reverse it. Don't put the 2025-blended rankings
  score back into waiver decisions: it rated rookies (no 2025 games) below
  7-point veterans and made advice flip-flop (old logic reversed itself in
  704 of 1500 random test leagues; the new logic in 0). "Empty slot" means the
  best lineup can't fill it, not that nobody is set there.
- Players whose game has kicked off are `locked` (scoreboard `started`): they
  keep their slot, can't be moved in, added or dropped for this week.
- Optimizer slots come from the league settings (`optimizer.set_league_slots`).
  Inferring them from the roster hid an empty K slot once; don't revert that.
- Matchup strength is only what ESPN's and Sleeper's projections include; the
  dashboard adds none of its own. Say so; don't oversell the score.

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
