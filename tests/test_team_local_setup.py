"""Offline checks for fresh-install catalogue and owned-process launcher behavior."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from app.database.seed_nfl_catalog import seed_nfl_catalog

spec = importlib.util.spec_from_file_location("team_launcher", Path(__file__).resolve().parents[1] / "Run-LocalApp.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_fresh_nfl_catalog_is_complete_and_repeatable():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE sports(id INTEGER PRIMARY KEY,slug TEXT)"))
        conn.execute(text("INSERT INTO sports VALUES(1,'american-football')"))
        conn.execute(text("CREATE TABLE teams(id INTEGER PRIMARY KEY,sport_id INTEGER,name TEXT,abbreviation TEXT,active BOOLEAN)"))
    seed_nfl_catalog(engine)
    seed_nfl_catalog(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM teams")).scalar_one() == 32
        assert conn.execute(text("SELECT name FROM teams WHERE abbreviation='WSH'")).scalar_one() == 'Washington Commanders'
        assert conn.execute(text("SELECT name FROM teams WHERE abbreviation='LAR'")).scalar_one() == 'Los Angeles Rams'


def test_conflicting_catalog_mapping_is_not_overwritten():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE sports(id INTEGER PRIMARY KEY,slug TEXT)"))
        conn.execute(text("INSERT INTO sports VALUES(1,'american-football')"))
        conn.execute(text("CREATE TABLE teams(id INTEGER PRIMARY KEY,sport_id INTEGER,name TEXT,abbreviation TEXT,active BOOLEAN)"))
        conn.execute(text("INSERT INTO teams VALUES(1,1,'Wrong team','ARI',true)"))
    with pytest.raises(ValueError, match='Conflicting'):
        seed_nfl_catalog(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name FROM teams")).scalars().all() == ['Wrong team']


def test_missing_prerequisites_report_instead_of_starting_services(tmp_path):
    with patch.object(launcher, 'ROOT', tmp_path), patch.object(launcher.shutil, 'which', return_value=None), patch.object(launcher.importlib.util, 'find_spec', return_value=None), patch.object(launcher, 'reachable', return_value=False):
        errors, _, _ = launcher.preflight()
    assert any('backend/.env' in error for error in errors)
    assert any('Node.js' in error for error in errors)
    assert any('Frontend dependencies' in error for error in errors)


def test_failed_child_cleans_up_only_launched_children():
    class Child:
        def __init__(self, exited):
            self.exited = exited
            self.terminated = False
        def poll(self): return 1 if self.exited else None
        def terminate(self): self.terminated = True; self.exited = True
        def wait(self, timeout=None): return 0
    backend, frontend = Child(True), Child(False)
    with patch.object(launcher, 'preflight', return_value=([], 'node', Path('vite.js'))), patch.object(launcher.subprocess, 'Popen', side_effect=[backend, frontend]), patch.object(launcher.sys, 'argv', ['Run-LocalApp.py']):
        assert launcher.main() == 1
    assert not backend.terminated
    assert frontend.terminated
