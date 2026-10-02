# Sprint 2 Ticket 4: Evaluation, Versioning, and Model Interface

The notes below describe the original PR #15 implementation. The local follow-up
adds real-data evaluation, Brier/log-loss/calibration analysis, immutable model
artifacts, dataset/model/source fingerprints and a validated prediction interface.
See [completion evidence](sprint2_completion_evidence.md) for the current contract.

The evaluation module reports accuracy, precision, recall, F1, test-row count, and a probability-sum check for each sport baseline. It rejects invalid probability outputs and writes JSON evidence containing the sport, model version, source revision, and metrics.

## Model interface

Input is a pandas table containing the six ordered feature columns from Ticket 2: `home_win_rate`, `away_win_rate`, `home_avg_score`, `away_avg_score`, `home_avg_allowed`, and `away_avg_allowed`. Output is an outcome label plus two probabilities ordered by the classifier classes. The model version is derived from the metadata and source revision so results can be traced to the implementation.

## Review limitations

This is an initial binary **home-win versus not-home-win** classifier. A draw is
encoded as 0, not a predicted away win; EPL three-way outcome prediction is not
implemented. Test fixtures are synthetic, not evidence of real NFL/MLB/EPL accuracy.
Features use earlier results in the test period when available, representing
rolling pre-game predictions rather than a fixed-season forecast.

The version identifier fingerprints metadata and a supplied revision, not the
training data or model bytes. Supply the actual Git revision for traceability.
Model/evaluation files currently overwrite the same sport filename; immutable
artifact storage and dataset fingerprints remain follow-up work. Only load pickle
models from a trusted source. Probability sum validation is not a calibration study.
