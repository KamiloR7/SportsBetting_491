# Sprint 2 Ticket 3: Sport-Specific Baselines

The baseline trainer uses the Ticket 2 feature columns and chronological split. It supports NFL, MLB, and EPL through one consistent Logistic Regression pipeline while keeping each sport's model and metadata separate.

Every saved model is accompanied by JSON metadata containing the sport, model type, feature order, row counts, split strategy, and random seed. The trainer requires both outcome classes in the training partition so invalid data fails instead of producing a misleading model.
