"""Minimal client for the local EspoCRM stand used by the stage-03 tests (stdlib only).

Credentials never come from argv and are never printed: the admin password is read from the private stand
file (/data/itvolga/espo-private/stand/local.env); synthetic users get random passwords per run. Requests go
only to a loopback address, proxies are ignored (the same rule as scripts/stand/health_http.py).
"""
import base64
import ipaddress
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlsplit

REPO = Path(__file__).resolve().parents[2]
PRIVATE_ENV = Path(os.environ.get("STAND_PRIVATE_ENV", "/data/itvolga/espo-private/stand/local.env"))
BASE = os.environ.get("ESPO_SITE_URL", "http://crm.itvolga.test").rstrip("/")
MYSQL_SOCKET = os.environ.get("MYSQL_SOCKET", "/run/itvolga-espo-mysql/mysqld.sock")
DB_NAME = os.environ.get("DB_NAME", "espocrm")

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _assert_loopback():
    host = urlsplit(BASE).hostname
    addrs = {info[4][0] for info in socket.getaddrinfo(host, 80, proto=socket.IPPROTO_TCP)}
    if not addrs or not all(ipaddress.ip_address(a).is_loopback for a in addrs):
        raise SystemExit(f"{host} does not resolve to loopback only: refusing to send credentials")


def admin_credentials():
    values = {}
    for line in PRIVATE_ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip("'\"")
    return values["ESPO_ADMIN_USERNAME"], values["ESPO_ADMIN_PASSWORD"]


class Client:
    def __init__(self, username, password):
        _assert_loopback()
        self.username = username
        self._auth = base64.b64encode(f"{username}:{password}".encode()).decode()

    def request(self, method, path, body=None, params=None, headers=None):
        url = f"{BASE}/api/v1/{path.lstrip('/')}"
        if params:
            url += "?" + urlencode(params, doseq=True)
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Espo-Authorization": self._auth, "Content-Type": "application/json", "Accept": "application/json",
            **(headers or {})})
        try:
            with _OPENER.open(req, timeout=30) as resp:
                raw = resp.read()
                if raw and "json" not in resp.headers.get("Content-Type", ""):
                    return resp.status, raw, dict(resp.headers)  # file downloads
                return resp.status, (json.loads(raw) if raw else None), dict(resp.headers)
        except urllib.error.HTTPError as err:
            raw = err.read()
            try:
                payload = json.loads(raw) if raw else None
            except ValueError:
                payload = None
            return err.code, payload, dict(err.headers)

    def get(self, path, **params):
        return self.request("GET", path, params=params or None)

    def post(self, path, body=None, skip_duplicate_check=True):
        # synthetic records share name prefixes: the standard duplicate check is not what these tests verify
        headers = {"X-Skip-Duplicate-Check": "true"} if skip_duplicate_check else None
        return self.request("POST", path, body or {}, headers=headers)

    def put(self, path, body):
        return self.request("PUT", path, body)

    def delete(self, path):
        return self.request("DELETE", path)


def sql(query):
    """Run SQL on the stand database (MySQL root via auth_socket); returns rows as lists of strings."""
    out = subprocess.run(["sudo", "-n", "mysql", f"--socket={MYSQL_SOCKET}", "-N", "-B", DB_NAME, "-e", query],
                         check=True, capture_output=True, text=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def espo_console(*args):
    """task espo -- <args>: EspoCRM console as the stand user (scripts/stand/espo.sh)."""
    return subprocess.run([str(REPO / "scripts/stand/espo.sh"), *args], check=True, capture_output=True,
                          text=True).stdout
