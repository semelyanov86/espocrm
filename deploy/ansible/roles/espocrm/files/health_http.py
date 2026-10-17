#!/usr/bin/env python3
"""HTTP part of the server health check of EspoCRM (role espocrm; the server variant of scripts/stand/health_http.py).

Connects to the loopback address of a vhost (127.0.0.1:<port>) with the TLS name of the site, so the check never
depends on outside DNS and never sends anything off the server. Environment (never argv): HEALTH_URL (site URL),
HEALTH_CONNECT (host:port), HEALTH_EXPECT (espocrm | maintenance), HEALTH_CA_FILE (an extra trusted CA — the test CA
of the disposable target; the chain and the name of the certificate are always verified), ESPO_VERSION, PHP_VERSION,
optional HEALTH_USER / HEALTH_PASSWORD (login check). Prints one status line per check; no response bodies, tokens or
passwords are printed.
"""
import base64
import http.client
import json
import os
import re
import socket
import ssl
import sys
from urllib.parse import urlsplit

fails = 0


def report(status, name, detail=""):
    global fails
    if status == "FAIL":
        fails += 1
    print(f"{status:<5} {name:<36} {detail}".rstrip())


URL = urlsplit(os.environ["HEALTH_URL"].rstrip("/"))
CONNECT_HOST, CONNECT_PORT = os.environ["HEALTH_CONNECT"].rsplit(":", 1)
TAG = f"{URL.hostname}:{URL.port or 443}"
CTX = ssl.create_default_context()
if os.environ.get("HEALTH_CA_FILE"):
    CTX.load_verify_locations(cafile=os.environ["HEALTH_CA_FILE"])
COOKIES = {}


class LoopbackHTTPS(http.client.HTTPSConnection):
    """HTTPS to the loopback address with SNI and certificate checks of the site name."""

    def connect(self):
        sock = socket.create_connection((CONNECT_HOST, int(CONNECT_PORT)), self.timeout)
        self.sock = CTX.wrap_socket(sock, server_hostname=URL.hostname)


def request(path, headers=None, method="GET", body=None):
    conn = LoopbackHTTPS(URL.hostname, URL.port or 443, timeout=30)
    hdrs = {"Host": URL.netloc, **(headers or {})}
    if COOKIES:
        hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in COOKIES.items())
    try:
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read()
        for value in resp.headers.get_all("Set-Cookie") or []:
            name, _, rest = value.partition("=")
            COOKIES[name.strip()] = rest.split(";", 1)[0]
        return resp.status, resp.headers, data
    except (OSError, ssl.SSLError, http.client.HTTPException) as err:
        return 0, {}, err.__class__.__name__.encode()
    finally:
        conn.close()


def espo_auth(user, secret):
    return base64.b64encode(f"{user}:{secret}".encode()).decode()


def check_maintenance():
    code, headers, body = request("/")
    ok = code == 503 and b"<html" in body.lower()
    report("OK" if ok else "FAIL", f"http {TAG}: maintenance", f"status {code} (expected 503 page)")
    code, _, _ = request("/api/v1/App/user")
    report("OK" if code == 503 else "FAIL", f"http {TAG}: api closed", f"status {code} (expected 503)")


def check_espocrm():
    code, _, body = request("/")
    text = body.decode("utf-8", "replace")
    ok = code == 200 and "loader-params" in text and "<?php" not in text
    report("OK" if ok else "FAIL", f"http {TAG}: GET /", f"status {code}, page rendered by PHP-FPM: {ok}")
    match = re.search(r"href=\"([^\"]+)\"[^>]*id='main-stylesheet'", text)
    if match:
        code, _, _ = request("/" + match.group(1).lstrip("/"))
        report("OK" if code == 200 else "FAIL", f"http {TAG}: stylesheet", f"status {code}")
    else:
        report("FAIL", f"http {TAG}: stylesheet", "link not found in the page")
    for path in ("/data/config-internal.php", "/data/config.php", "/application/Espo/Core/Application.php",
                 "/vendor/autoload.php", "/custom/Espo/Modules/Itvolga/Resources/module.json", "/bootstrap.php",
                 "/install/", "/client/../data/config.php", "/.espocrm-core", "/command.php"):
        code, _, _ = request(path)
        report("OK" if code in (403, 404) else "FAIL", f"http deny {path}"[:36], f"status {code}")
    code, _, _ = request("/api/v1/App/user")
    report("OK" if code == 401 else "FAIL", "api: anonymous", f"status {code} (expected 401)")

    user, password = os.environ.get("HEALTH_USER"), os.environ.get("HEALTH_PASSWORD")
    if not user or not password:
        report("OK", "api: login", "skipped (no credentials given)")
        return
    code, headers, body = request("/api/v1/App/user", {
        "Espo-Authorization": espo_auth(user, password), "Espo-Authorization-By-Token": "false",
        "Espo-Authorization-Create-Token-Secret": "true"})
    if code == 401 and headers.get("X-Status-Reason") == "second-step-required":
        report("OK", "api: login", "password accepted, second factor required (2FA of the account)")
        return
    if code != 200:
        report("WARN", "api: login", f"status {code} (password of the vault differs or the account is blocked)")
        return
    data = json.loads(body)
    token = data.get("token")
    report("OK" if token else "FAIL", "api: login", f"200, token issued: {bool(token)}")
    if not token:
        return
    token_headers = {"Espo-Authorization": espo_auth(user, token), "Espo-Authorization-By-Token": "true"}
    code, _, body = request("/api/v1/App/about", token_headers)
    version = json.loads(body).get("version") if code == 200 else None
    report("OK" if version == os.environ["ESPO_VERSION"] else "FAIL", "api: version", f"{version}")
    if (data.get("user") or {}).get("type") == "admin":
        code, _, body = request("/api/v1/Admin/action/systemRequirementList", token_headers)
        if code == 200:
            req = json.loads(body)
            for group in ("php", "database", "permission"):
                items = req.get(group) or {}
                bad = sorted(k for k, v in items.items() if not v.get("acceptable"))
                hard = [k for k in bad if group == "permission" or items[k].get("type") in ("version", "connection")]
                report("FAIL" if hard else ("WARN" if bad else "OK"), f"requirements: {group}",
                       f"{len(items)} checked" + (f", not acceptable: {', '.join(bad)}" if bad else ""))
            php_ver = next((str(v.get("actual")) for v in (req.get("php") or {}).values()
                            if v.get("type") == "version"), "")
            report("OK" if php_ver.startswith(os.environ["PHP_VERSION"] + ".") else "FAIL", "php-fpm: version",
                   f"PHP {php_ver}")
        else:
            report("FAIL", "requirements", f"status {code}")
    code, _, _ = request("/api/v1/App/destroyAuthToken", {**token_headers, "Content-Type": "application/json"},
                         "POST", json.dumps({"token": token}).encode())
    after, _, _ = request("/api/v1/App/user", token_headers)
    report("OK" if code == 200 and after == 401 else "FAIL", "api: logout", f"{code}, token afterwards {after}")


def main():
    if CONNECT_HOST not in ("127.0.0.1", "::1"):
        report("FAIL", "http: target", f"{CONNECT_HOST}: not loopback, nothing sent")
        return
    if os.environ.get("HEALTH_EXPECT") == "maintenance":
        check_maintenance()
    else:
        check_espocrm()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # the failure without request details
        report("FAIL", "http: checks aborted", exc.__class__.__name__)
    print("# http checks completed")
    sys.exit(min(fails, 100))
