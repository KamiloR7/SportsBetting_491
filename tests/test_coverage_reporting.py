"""Exercise the real coverage tools without altering the outer suite's data."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.parametrize("failing_test", [False, True], ids=["passing-suite", "failing-suite"])
def test_coverage_reports_include_branches_and_unimported_files(tmp_path, failing_test):
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copyfile(repo_root / ".coveragerc", tmp_path / ".coveragerc")
    source_dir = tmp_path / "backend" / "app" / "ml"
    source_dir.mkdir(parents=True)
    package_dir = tmp_path / "src" / "sportsbetting"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "untested.py").write_text("VALUE = 42\n", encoding="utf-8")
    (source_dir / "unimported.py").write_text("VALUE = 7\n", encoding="utf-8")
    (source_dir / "sample.py").write_text(
        "def classify(value):\n"
        "    if value > 0:\n"
        "        return 'positive'\n"
        "    return 'nonpositive'\n",
        encoding="utf-8",
    )
    assertion = "assert False, 'intentional test failure'" if failing_test else "assert True"
    (tmp_path / "test_sample.py").write_text(
        "from backend.app.ml.sample import classify\n\n"
        "def test_sample():\n"
        "    assert classify(1) == 'positive'\n"
        f"    {assertion}\n",
        encoding="utf-8",
    )

    # Nested pytest must not write into the coverage database of this outer run.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COV_CORE_", "COVERAGE_", "PYTEST_"))
    }
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-p", "pytest_cov", "-q", "test_sample.py",
            "--junitxml=build/test-results.xml", "--cov", "--cov-config=.coveragerc",
            "--cov-report=term-missing", "--cov-report=xml", "--cov-report=html",
        ],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == (1 if failing_test else 0), result.stdout + result.stderr
    assert "TOTAL" in result.stdout

    report = ET.parse(tmp_path / "build" / "coverage.xml").getroot()
    assert 0 < float(report.attrib["line-rate"]) < 1
    assert 0 < float(report.attrib["branch-rate"]) < 1
    assert int(report.attrib["branches-valid"]) == 2
    classes = report.findall(".//class")
    for filename in ("unimported.py", "untested.py"):
        untested = next(item for item in classes if item.attrib["filename"].endswith(filename))
        assert float(untested.attrib["line-rate"]) == 0
    assert (tmp_path / "build" / "coverage-html" / "index.html").is_file()
    suite = ET.parse(tmp_path / "build" / "test-results.xml").getroot().find("testsuite")
    assert int(suite.attrib["failures"]) == int(failing_test)

    summary = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--format=markdown"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert summary.returncode == 0, summary.stderr
    assert "**TOTAL**" in summary.stdout
    assert "Branch" in summary.stdout
