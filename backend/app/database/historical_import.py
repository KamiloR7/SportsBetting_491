"""Validated, bounded historical imports; no implicit database configuration."""
from __future__ import annotations

from sqlalchemy import text
from src.normalizers.match_validation import validate_historical_matches
from .match_ingestion import ReferenceResolutionError, resolve_match_references, upsert_match

# Stable shared namespace: all cooperating historical importers use this lock.
HISTORICAL_IMPORT_LOCK = 491025
MAX_BATCH_SIZE = 1000


def historical_ineligibility_reasons(row):
    """Pure eligibility checks shared with the no-database CLI dry run."""
    reasons = []
    if row["status"] != "completed":
        reasons.append(f"Historical import requires completed status; got {row['status']}")
    if not row.get("kickoff_utc"):
        reasons.append("Date-only record: actual kickoff timestamp required")
    if row.get("season") is None:
        reasons.append("Season reference required")
    return reasons


def load_historical_matches(engine, records):
    """Load up to MAX_BATCH_SIZE canonical records in one transaction.

    Validation/reference failures are reported; unexpected transaction failures
    roll back every write and return zero committed insert/update counts.
    No configured/default engine is imported; the caller chooses the database.
    """
    rows = []
    for row in records:
        rows.append(row)
        if len(rows) > MAX_BATCH_SIZE:
            raise ValueError(f"Historical batches are limited to {MAX_BATCH_SIZE} records")
    validation = validate_historical_matches(rows)
    report = {"records_read": validation.records_read, "records_accepted": len(validation.accepted),
              "records_rejected": len(validation.rejected), "duplicates_collapsed": len(validation.duplicates),
              "validation": validation.to_dict(), "deferred": [], "matches_inserted": 0,
              "matches_updated": 0, "transaction_failures": [], "committed": False}
    candidates = []
    for row in validation.accepted:
        reasons = historical_ineligibility_reasons(row)
        if reasons:
            report["deferred"].append({"source": row["source"], "game_id": row["game_id"], "reasons": reasons})
        else:
            candidates.append(row)
    if not candidates:
        report["records_deferred"] = len(report["deferred"])
        return report
    try:
        inserted = updated = 0
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": HISTORICAL_IMPORT_LOCK})
            eligible = []
            for row in candidates:
                try:
                    refs = resolve_match_references(conn, row, require_season=True)
                except ReferenceResolutionError as exc:
                    report["deferred"].append({"source": row["source"], "game_id": row["game_id"], "reasons": [str(exc)]})
                else:
                    eligible.append((row, refs))
            for row, refs in eligible:
                _, action = upsert_match(conn, row, references=refs, return_action=True)
                inserted += action == "inserted"
                updated += action == "updated"
        report.update(matches_inserted=inserted, matches_updated=updated, committed=True)
    except Exception as exc:
        # Includes commit failures. Never report attempted writes as committed.
        report["transaction_failures"].append({"type": type(exc).__name__, "reason": str(exc)})
    report["records_deferred"] = len(report["deferred"])
    return report
