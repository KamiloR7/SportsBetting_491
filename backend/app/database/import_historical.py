"""Local-file historical import CLI; never selects the application database."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from src.normalizers.match_validation import validate_historical_matches
from src.normalizers.multi_sport_normalizer import (
    NormalizationError, normalize_match_row, normalize_mlb_match, normalize_epl_match,
)
from .historical_import import (
    MAX_BATCH_SIZE, historical_ineligibility_reasons, load_historical_matches,
)

logger = logging.getLogger(__name__)


def read_records(path, input_format):
    """Read local CSV, JSON list, or MLB schedule JSON without retrieval."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        if input_format in {"csv", "mlb-csv", "epl-csv"}:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("Missing or duplicate CSV headers")
            rows = list(reader)
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                raise ValueError("Malformed CSV row width")
        else:
            payload = json.load(handle)
            if input_format == "mlb-schedule":
                if not isinstance(payload, dict) or not isinstance(payload.get("dates"), list):
                    raise ValueError("Expected MLB dates/games schedule")
                rows = []
                for day in payload["dates"]:
                    if not isinstance(day, dict) or not isinstance(day.get("games"), list):
                        raise ValueError("Expected MLB dates/games schedule")
                    rows.extend(day["games"])
            else:
                rows = payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty record list")
    return rows


def configured_engine(args):
    """Require explicit local import-only target; never inspect application env."""
    value = os.environ.get(args.database_url_env)
    if not value or not args.allow_write or not args.database_name:
        raise ValueError("Live imports require database URL environment configuration, --database-name and --allow-write")
    try:
        url = make_url(value)
        safe = (url.get_backend_name() == "postgresql" and url.host in {"localhost", "127.0.0.1", "::1"}
                and url.database == args.database_name and url.database.startswith("sportsbetting_import_")
                and not any(word in url.database.lower() for word in ("prod", "shared", "demo"))
                and not url.query)
        if not safe:
            raise ValueError
    except Exception:
        raise ValueError("Database target refused: use an explicitly selected local sportsbetting_import_* database without URL query overrides") from None
    return create_engine(url, hide_parameters=True)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--input", nargs="+", required=True, type=Path)
    result.add_argument("--sport", choices=["NFL", "MLB", "EPL"], required=True)
    result.add_argument("--format", choices=["json", "csv", "mlb-schedule", "mlb-csv", "epl-csv"], required=True)
    result.add_argument("--season", help="Source season context for reduced MLB or EPL CSV records")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE)
    result.add_argument("--database-url-env", default="HISTORICAL_IMPORT_DATABASE_URL")
    result.add_argument("--database-name")
    result.add_argument("--allow-write", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if not 1 <= args.batch_size <= MAX_BATCH_SIZE:
        logger.error("batch-size must be between 1 and %s", MAX_BATCH_SIZE)
        return 2
    if (args.format.startswith("mlb-") and args.sport != "MLB") or (args.format == "epl-csv" and args.sport != "EPL"):
        logger.error("Input format does not match selected sport")
        return 2
    logger.info("Import started at %s sport=%s dry_run=%s files=%s", datetime.now(timezone.utc).isoformat(), args.sport, args.dry_run, [str(path) for path in args.input])
    normalized, errors, locations = [], [], []
    read = 0
    try:
        for path in args.input:
            for index, row in enumerate(read_records(path, args.format)):
                read += 1
                try:
                    if not isinstance(row, dict):
                        raise NormalizationError("Expected a record mapping")
                    if args.format in {"mlb-schedule", "mlb-csv"}:
                        record = normalize_mlb_match(row, season=args.season)
                    elif args.format == "epl-csv":
                        record = normalize_epl_match(row, season=args.season)
                    else:
                        record = normalize_match_row(row)
                    if record["league"] != args.sport:
                        raise NormalizationError("Record league conflicts with selected sport")
                    normalized.append(record)
                    locations.append({"file": str(path), "row": index})
                except (NormalizationError, ValueError, TypeError, KeyError) as exc:
                    errors.append({"file": str(path), "row": index, "reasons": [str(exc)]})
    except (OSError, ValueError, csv.Error):
        logger.error("Input file could not be read or has malformed structure")
        return 2
    validation = validate_historical_matches(normalized)
    for rejected in validation.rejected:
        errors.append(dict(locations[rejected["index"]], reasons=rejected["reasons"]))
    summary = {"records_read": read, "records_accepted": len(validation.accepted),
               "records_rejected": len(errors), "duplicates_collapsed": len(validation.duplicates),
               "records_deferred": 0, "matches_inserted": 0, "matches_updated": 0,
               "dry_run": args.dry_run, "rejected": errors, "deferred": [],
               "duplicates": [dict(locations[item["index"]], kept=locations[item["kept_index"]]) for item in validation.duplicates],
               "transaction_failures": []}
    engine = None
    try:
        if args.dry_run:
            for row in validation.accepted:
                reasons = historical_ineligibility_reasons(row)
                if reasons:
                    summary["deferred"].append({"source": row["source"], "game_id": row["game_id"], "reasons": reasons})
        else:
            try:
                engine = configured_engine(args)
            except Exception:
                logger.error("Missing or unsafe database configuration; no import attempted")
                return 2
            for offset in range(0, len(validation.accepted), args.batch_size):
                try:
                    batch = load_historical_matches(engine, validation.accepted[offset:offset + args.batch_size])
                except Exception as exc:
                    batch = {"transaction_failures": [{"type": type(exc).__name__}]}
                summary["deferred"].extend(batch.get("deferred", []))
                if batch["transaction_failures"]:
                    # Driver messages can include credentials/connection strings.
                    summary["transaction_failures"].extend({"type": item["type"], "reason": "Batch failed; no writes from this batch committed"} for item in batch["transaction_failures"])
                    already_deferred = {(item["source"], item["game_id"]) for item in summary["deferred"]}
                    for pending_index, pending in enumerate(validation.accepted[offset:], offset):
                        if (pending["source"], pending["game_id"]) not in already_deferred:
                            reason = "Batch failed or rolled back" if pending_index < offset + args.batch_size else "Not attempted after earlier batch failure"
                            summary["deferred"].append({"source": pending["source"], "game_id": pending["game_id"], "reasons": [reason]})
                    logger.error("Database batch failed or rolled back; stopping subsequent batches")
                    break
                summary["matches_inserted"] += batch["matches_inserted"]
                summary["matches_updated"] += batch["matches_updated"]
    finally:
        if engine is not None:
            engine.dispose()
    summary["records_deferred"] = len(summary["deferred"])
    for entry in summary["rejected"] + summary["deferred"]:
        logger.warning("Record not loaded: %s", json.dumps(entry))
    logger.info("Sources=%s", sorted({row["source"] for row in validation.accepted}))
    logger.info("Import completed at %s read=%d accepted=%d rejected=%d duplicates=%d deferred=%d inserted=%d updated=%d",
                datetime.now(timezone.utc).isoformat(), read, summary["records_accepted"], len(errors), summary["duplicates_collapsed"], summary["records_deferred"], summary["matches_inserted"], summary["matches_updated"])
    print(json.dumps(summary, sort_keys=True))
    if summary["transaction_failures"]:
        return 3
    return 1 if errors or summary["deferred"] else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
