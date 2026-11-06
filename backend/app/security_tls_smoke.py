"""Real loopback HTTPS/certificate/cookie smoke; emits no credentials or tokens.

Run with PYTHONPATH=backend python -m app.security_tls_smoke. The temporary
test certificate is explicitly trusted by the client, never verify=False.
"""

import argparse
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time

import httpx2 as httpx


def run():
    with tempfile.TemporaryDirectory(prefix="vigor-auth-tls-") as directory:
        folder = Path(directory)
        config = folder / "openssl.cnf"
        config.write_text("""[req]
distinguished_name=dn
x509_extensions=ext
prompt=no
[dn]
CN=localhost
[ext]
subjectAltName=DNS:localhost,IP:127.0.0.1
basicConstraints=critical,CA:TRUE
keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign
extendedKeyUsage=serverAuth
""")
        cert, key = folder / "cert.pem", folder / "key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
            "-days", "1", "-config", str(config), "-out", str(cert), "-keyout", str(key),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        context = ssl.create_default_context(cafile=str(cert))
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.database.auth_demo:app",
            "--fd", str(listener.fileno()), "--ssl-certfile", str(cert),
            "--ssl-keyfile", str(key), "--no-access-log", "--log-level", "warning",
        ], pass_fds=(listener.fileno(),), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        listener.close()
        try:
            with httpx.Client(base_url=f"https://127.0.0.1:{port}", verify=context, trust_env=False, timeout=2) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Synthetic HTTPS server stopped before readiness")
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
                else:
                    raise RuntimeError("Synthetic HTTPS server did not become ready")
                assert client.get("/auth/me").status_code == 401
                challenge = client.get("/auth/csrf").json()["csrf_token"]
                response = client.post("/auth/login", json={"email": "alice@example.com", "password": "SyntheticDemo123!"}, headers={"X-CSRF-Token": challenge})
                assert response.status_code == 200
                cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith("__Host-vigor_session="))
                assert all(flag in cookie for flag in ["HttpOnly", "Secure", "SameSite=strict", "Max-Age=1800", "Path=/"])
                assert client.get("/auth/me").status_code == 200
                assert client.get("/auth/assessment/records/2").status_code == 403
                assert client.patch("/auth/assessment/records/1", json={"note": "unauthorized"}).status_code == 403
                csrf = client.get("/auth/csrf").json()["csrf_token"]
                assert client.patch("/auth/assessment/records/1", json={"note": "synthetic TLS write"}, headers={"X-CSRF-Token": csrf}).status_code == 200
                assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
                assert client.get("/auth/me").status_code == 401
                return {
                    "result": "pass", "transport": "real loopback HTTPS; generated test certificate explicitly verified",
                    "database": "ephemeral SQLite", "data": "synthetic only",
                    "checks": ["anonymous denial", "login", "Secure/HttpOnly/SameSite cookie", "authorized read",
                               "cross-account denial", "CSRF denial", "authorized write", "logout revocation"],
                    "source_commit": os.environ.get("GITHUB_SHA", "see evidence index"),
                }
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/sprint4/tls-smoke.json"))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
