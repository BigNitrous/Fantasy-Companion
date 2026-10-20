# Why the dashboard does not try to predict breakouts (weeks 2-6, 2026)

`master.csv`: 771 rostered QB/RB/WR/TE player-games that were played (351 on a bench), with
ESPN's and Sleeper's projections, the actual PPR points, and only pre-game features
(prior-week usage and variance, Vegas implied totals, opponent defense vs position).
`build_master.py` rebuilds it (inputs from the `backtest` branch tooling and nflverse).

Question: Week 6, Tucker (+16.4), Bernard (+15.8), Tate (+8.1) and Stroud (+7.1) on the bench
beat their projections. Could the dashboard have seen it coming?

Method: leave-one-week-out validation against the plain ESPN+Sleeper average ("blend", MAE 5.55),
paired-bootstrap CIs, then independent verifiers (leave-one-team-out split, permutation test,
leakage audit) trying to refute each finding.

Result, all do-not-ship (every CI includes zero):
- Matchup (defense points allowed to the position): MAE -0.005, 2/5 weeks, bench AUC 0.54.
- Vegas (implied team total, spread, total, home): -0.011 to -0.024, 3/5 weeks, AUC 0.52-0.54.
- Usage (target/snap/air-yards/carry share, WOPR, teammate absences): -0.007, AUC 0.52.
  Momentum was null here (earlier work found it harmful); keep it off.
- Bench selection / recent form vs projection: worse than the blend.
- Player-specific variance as a ceiling: a player's own sd had 0.03 correlation with his misses.
- Everything combined with nested ridge: 5.5447 vs 5.5495, collapses to the intercept.
The projections already include these. Blend over-projects by ~0.3 on average, not reliable.

What the data does support: bench players beat their projection by 8+ about 9% of the time
(starters 17%); about 1 bench player in 11 booms per week. Seven bench players producing four 7+ games
in one week is ~0.8% (about 4% over five weeks): a real outlier, but unforecastable variance.
Shipped instead (display only, `assess.outcome_range` / `assess.boom_prob`): the middle-80% outcome range per
player and a low-confidence "higher upside" note on bench cards (flag at 15%: 1.6x lift, weak).

Revisit with 12+ weeks or 2025 data. The `inj` column in the ESPN box scores is a post-game snapshot, so
it can't be used as a pre-game feature.
