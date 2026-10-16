"""Sprint 3 - S3-01.02: Reproducible match fixture tests."""

import json
from pathlib import Path

import pytest

from app.ml.features.outcome_labels import label_match_outcome


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "sprint3_match_outcomes.json"
)

FIXTURES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def label_fixture(record):
    """Pass required fixture fields to the outcome-labeling function."""
    return label_match_outcome(
        record["sport"],
        record["home_score"],
        record["away_score"],
        record["status"],
    )


@pytest.mark.parametrize(
    "record",
    FIXTURES,
    ids=[record["match_id"] for record in FIXTURES],
)
def test_sprint3_match_fixture(record):

    # Missing-field fixture must be rejected.
    if "expected_error" in record:
        with pytest.raises(KeyError, match="away_score"):
            label_fixture(record)
        return

    # Completed and nonfinal matches must produce expected labels.
    actual_label = label_fixture(record)

    assert actual_label == record["expected_label"]