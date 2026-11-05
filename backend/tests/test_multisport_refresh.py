from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

import pytest

from app.ml.features import download_multisport_data as refresh


class Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_fetch_source_retries_transient_failures_with_a_bound():
    calls, delays = [], []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) < 3:
            raise URLError("temporary source failure")
        return Response(b"complete payload")

    result = refresh.fetch_source("https://example.invalid/feed", timeout=7, retries=2,
                                  backoff_seconds=0.25, opener=opener, sleep=delays.append)

    assert result == b"complete payload"
    assert len(calls) == 3
    assert [delay for delay in delays] == [0.25, 0.5]
    assert all(timeout == 7 for _, timeout in calls)


def test_fetch_source_stops_after_configured_attempts():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        raise URLError("provider details must not leak")

    with pytest.raises(RuntimeError, match=r"Source request failed \(URLError\) after 2") as error:
        refresh.fetch_source("https://example.invalid/private?token=hidden", retries=1,
                             opener=opener, sleep=lambda _: None)

    assert len(calls) == 2
    assert "token" not in str(error.value)


def test_refresh_validation_failure_preserves_the_previous_snapshot(tmp_path: Path, monkeypatch):
    output = tmp_path / "nested" / "raw"
    output.mkdir(parents=True)
    games_path = output / "nfl_games.csv"
    games_path.write_bytes(b"previous validated dataset")
    source_path = output / "nfl_source_0.bin"
    source_path.write_bytes(b"previous source payload")
    monkeypatch.setattr(refresh, "SOURCES", {"NFL": ["https://example.invalid/nfl.csv"]})
    monkeypatch.setattr(refresh, "fetch_source", lambda *args, **kwargs: b"not,valid\n")

    with pytest.raises((KeyError, ValueError)):
        refresh.download_datasets(output, retries=0)

    assert games_path.read_bytes() == b"previous validated dataset"
    assert source_path.read_bytes() == b"previous source payload"


def test_snapshot_replaces_only_named_refresh_outputs(tmp_path: Path):
    output = tmp_path / "raw"
    output.mkdir()
    (output / "unrelated.txt").write_text("keep")
    (output / "nfl_games.csv").write_bytes(b"old")

    refresh._replace_snapshot(output, {"nfl_games.csv": b"new", "provenance.json": b"{}"})

    assert (output / "nfl_games.csv").read_bytes() == b"new"
    assert (output / "provenance.json").read_bytes() == b"{}"
    assert (output / "unrelated.txt").read_text() == "keep"
