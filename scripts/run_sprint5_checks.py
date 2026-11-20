"""Timestamped local QA evidence; never targets an application database.

Run from repository root using your backend Python environment.
Default: frontend tests/lint/build. Add --browser and/or --backend as needed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--backend', action='store_true')
    parser.add_argument('--auth', action='store_true', help='Isolated auth/session/CSRF regression tests')
    parser.add_argument('--tls', action='store_true', help='Verified loopback HTTPS cookie smoke')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    started = datetime.now(timezone.utc)
    folder = root / 'build/sprint5-qa/runs' / started.strftime('%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True, exist_ok=True)
    npm = shutil.which('npm') or 'npm'
    checks = [('components', [npm, 'test'], root / 'frontend'),
              ('lint', [npm, 'run', 'lint'], root / 'frontend'),
              ('build', [npm, 'run', 'build'], root / 'frontend')]
    if args.browser:
        checks.append(('browser-mock-api', [npm, 'run', 'test:e2e'], root / 'frontend'))
    if args.backend:
        checks.append(('backend-regression', [sys.executable, '-m', 'pytest', '-q',
                       f'--junitxml={folder / "backend-results.xml"}'], root))
    if args.auth:
        checks.append(('login-api', [sys.executable, '-m', 'pytest', '-q',
                       'backend/tests/test_auth_security.py', 'backend/tests/test_sprint4_auth_api.py',
                       f'--junitxml={folder / "login-api-results.xml"}'], root))
    if args.tls:
        checks.append(('login-https', [sys.executable, '-m', 'app.security_tls_smoke',
                       '--output', str(folder / 'login-tls-smoke.json')], root))
    summary = {
        'started_utc': started.isoformat(),
        'started_local': started.astimezone(ZoneInfo('America/Los_Angeles')).isoformat(),
        'timezone': 'America/Los_Angeles',
        'executor': 'Automated execution; not a student-operated dry-run',
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'source_state': 'See git diff and submission source manifest; local changes may be uncommitted',
        'checks': [],
    }
    env = {**os.environ, 'PYTHONPATH': str(root / 'backend') + os.pathsep + str(root / 'src'),
           'PYTHONDONTWRITEBYTECODE': '1', 'SPRINT5_REPORT_DIR': str(folder)}
    for label, command, cwd in checks:
        start = datetime.now(timezone.utc)
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
        log = folder / f'{label}.log'
        log.write_text(result.stdout + result.stderr)
        summary['checks'].append({'name': label, 'started_utc': start.isoformat(),
                                  'finished_utc': datetime.now(timezone.utc).isoformat(),
                                  'exit_code': result.returncode, 'log': log.name})
        print(f'{label}: {"PASS" if result.returncode == 0 else "FAIL"} (see {log.relative_to(root)})', flush=True)
        (folder / 'run-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (folder / 'run-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(any(check['exit_code'] for check in summary['checks']))


if __name__ == '__main__':
    raise SystemExit(main())
