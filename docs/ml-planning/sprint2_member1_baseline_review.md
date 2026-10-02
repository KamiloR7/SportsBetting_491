# Sprint 2 Member 1 Baseline Review

The repository contains an NFL-only Logistic Regression baseline. Its preparation path creates chronological prior-game team features, uses an 80/20 chronological split, and reports accuracy and win probabilities.

The Sprint 2 requirement is broader: real NFL, MLB, and EPL data. MLB and EPL raw training files are not currently present, so this implementation does not invent data or claim those datasets are ready. It establishes the shared validation gate that they must pass before training.

Each dataset must contain unique `game_id`, parseable `game_date`, `home_team`, `away_team`, `home_score`, and `away_score`. The loader rejects missing or duplicate records and sorts rows chronologically.

Completion evidence: existing NFL baseline reviewed; shared loader committed; deterministic tests cover NFL, MLB, and EPL; missing-column and duplicate-ID failures are tested. Source provenance will be recorded when MLB and EPL files are added.
