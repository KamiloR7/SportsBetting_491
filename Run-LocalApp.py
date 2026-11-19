"""Windows/macOS local launcher. First follow docs/team-local-setup.md.
Uses your current Python environment and an already running local PostgreSQL.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def reachable(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def preflight():
    errors = []
    if not (ROOT / "backend/.env").is_file():
        errors.append("Missing backend/.env. Follow docs/team-local-setup.md.")
    for package in ("dotenv", "uvicorn", "fastapi", "sqlalchemy", "psycopg2"):
        if importlib.util.find_spec(package) is None:
            errors.append(f"Missing {package}; install backend requirements using this Python environment.")
    node = shutil.which("node")
    if not node:
        errors.append("Node.js is missing from PATH; use Node 22.12+ per the setup guide.")
    else:
        version = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v").split(".")
        major, minor = map(int, version[:2])
        if not ((major == 20 and minor >= 19) or (major == 22 and minor >= 12) or major > 22):
            errors.append("Node version does not satisfy Vite: ^20.19.0 or >=22.12.0.")
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if not vite.is_file():
        errors.append("Frontend dependencies missing. Run npm --prefix frontend ci from the repository root.")
    for port in (8000, 5173):
        if reachable("127.0.0.1", port):
            errors.append(f"Port {port} is already in use. This launcher will not stop another process.")
    if not errors:
        from dotenv import dotenv_values
        config = {**dotenv_values(ROOT / "backend/.env"), **os.environ}
        host = config.get("DATABASE_HOST", "127.0.0.1")
        if host not in {"localhost", "127.0.0.1", "::1"}:
            errors.append("This launcher is for a local database only.")
        else:
            try:
                port = int(config.get("DATABASE_PORT", "5432"))
                if not 1 <= port <= 65535:
                    raise ValueError("Invalid port")
                if not reachable(host, port):
                    errors.append("PostgreSQL is not running at the configured local host/port. Start it first.")
            except (TypeError, ValueError):
                errors.append("DATABASE_PORT must be a number in backend/.env.")
    return errors, node, vite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check prerequisites without starting services")
    args = parser.parse_args()
    errors, node, vite = preflight()
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.check:
        print("Basic prerequisites passed. This checks DB reachability, not credentials, schema, data or models.")
        return 0
    children = []
    try:
        children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT / "backend"))
        children.append(subprocess.Popen([node, str(vite), "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=ROOT / "frontend"))
        print("Starting http://127.0.0.1:5173/dashboard — keep this terminal open; Ctrl+C stops the app.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
        print("An app service exited; see its messages above. Stopping the other service.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        print("App stopped. PostgreSQL is managed separately; its database files were preserved.")


if __name__ == "__main__":
    raise SystemExit(main())
