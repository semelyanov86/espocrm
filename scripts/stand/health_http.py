#!/usr/bin/env python3
"""HTTP part of the stand health check: web UI, static files, blocked paths, API login.

Reads ESPO_SITE_URL, ESPO_ADMIN_USERNAME, ESPO_ADMIN_PASSWORD, ESPO_VERSION, PHP_VERSION from
the environment (never from argv). Prints one status line per check; exit code = number of FAILs.
No response bodies, tokens or passwords are printed.
"""
import base64
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request

def env(name: str) -> str:
    return os.environ[name]


BASE = env("ESPO_SITE_URL").rstrip("/")
USER = env("ESPO_ADMIN_USERNAME")
PASSWORD = env("ESPO_ADMIN_PASSWORD")
fails = 0


def report(status: str, name: str, detail: str = "") -> None:
    global fails
    if status == "FAIL":
        fails += 1
    print(f"{status:<5} {name:<36} {detail}".rstrip())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # report 3xx as is
        return None


# The login response sets the HttpOnly cookie `auth-token-secret`; token requests must send it back
# (as the browser does), so the opener keeps cookies.
OPENER = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path: str, headers=None, method="GET", body=None):
    req = urllib.request.Request(BASE + path, headers=headers or {}, method=method, data=body)
    try:
        with OPENER.open(req, timeout=20) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()
    except (urllib.error.URLError, OSError) as err:
        return 0, {}, str(err).encode()


def espo_auth(user: str, secret: str) -> str:
    return base64.b64encode(f"{user}:{secret}".encode()).decode()


def main() -> int:
    # 1. Web UI entry page and its main stylesheet (served by Apache from /client/).
    code, _, body = request("/")
    text = body.decode("utf-8", "replace")
    if code == 200 and "loader-params" in text and "<?php" not in text:
        report("OK", "http: GET /", "200, EspoCRM page rendered by PHP-FPM")
    else:
        report("FAIL", "http: GET /", f"status {code}")
    match = re.search(r"href=\"([^\"]+)\"[^>]*id='main-stylesheet'", text)
    if match:
        code, _, _ = request("/" + match.group(1).lstrip("/"))
        report("OK" if code == 200 else "FAIL", "http: main stylesheet", f"status {code}")
    else:
        report("FAIL", "http: main stylesheet", "link not found in the page")

    # 2. Paths that must never be served.
    for path in ("/data/config-internal.php", "/data/config.php", "/application/Espo/Core/Application.php",
                 "/vendor/autoload.php", "/custom/Espo/Custom/.htaccess", "/bootstrap.php",
                 "/install/", "/client/../data/config.php", "/AGENTS.md", "/.git/config",
                 "/deploy/local/stand.conf"):
        code, _, _ = request(path)
        report("OK" if code in (403, 404) else "FAIL", f"http: deny {path}"[:36], f"status {code}")

    # 3. API: anonymous access is rejected, a wrong password is rejected.
    code, _, _ = request("/api/v1/App/user")
    report("OK" if code == 401 else "FAIL", "api: anonymous", f"status {code} (expected 401)")
    code, _, _ = request("/api/v1/App/user", {"Espo-Authorization": espo_auth(USER, PASSWORD + "-wrong")})
    report("OK" if code == 401 else "FAIL", "api: wrong password", f"status {code} (expected 401)")

    # 4. Login exactly like the web client: credentials -> auth token -> token requests.
    code, _, body = request("/api/v1/App/user", {"Espo-Authorization": espo_auth(USER, PASSWORD),
                                                 "Espo-Authorization-By-Token": "false",
                                                 "Espo-Authorization-Create-Token-Secret": "true"})
    token = None
    if code == 200:
        data = json.loads(body)
        token = data.get("token")
        user_type = (data.get("user") or {}).get("type")
        ok = bool(token) and user_type == "admin"
        report("OK" if ok else "FAIL", "api: login", f"200, user type {user_type}, token issued: {bool(token)}")
    else:
        report("FAIL", "api: login", f"status {code}")
    if not token:
        return fails

    token_headers = {"Espo-Authorization": espo_auth(USER, token), "Espo-Authorization-By-Token": "true"}
    code, _, _ = request("/api/v1/App/user", token_headers)
    report("OK" if code == 200 else "FAIL", "api: token session", f"status {code}")

    code, _, body = request("/api/v1/App/about", token_headers)
    version = json.loads(body).get("version") if code == 200 else None
    report("OK" if version == env("ESPO_VERSION") else "FAIL", "api: version", f"{version}")

    # 5. Server-side requirements as seen by the web process (PHP-FPM pool, DB, writable dirs).
    code, _, body = request("/api/v1/Admin/action/systemRequirementList", token_headers)
    if code == 200:
        data = json.loads(body)
        for group in ("php", "database", "permission"):
            items = data.get(group) or {}
            bad = sorted(k for k, v in items.items() if not v.get("acceptable"))
            # Hard failures: versions, connection, writable dirs. Missing optional libs/params: warning
            # (required PHP extensions are enforced by install.sh preflight).
            hard = [k for k in bad if group == "permission" or items[k].get("type") in ("version", "connection")]
            status = "FAIL" if hard else ("WARN" if bad else "OK")
            report(status, f"requirements: {group}",
                   f"{len(items)} checked" + (f", not acceptable: {', '.join(bad)}" if bad else ""))
        php_ver = next((str(v.get("actual")) for v in (data.get("php") or {}).values()
                        if v.get("type") == "version"), "")
        expected = env("PHP_VERSION")
        report("OK" if php_ver.startswith(expected + ".") else "FAIL", "php-fpm: version", f"PHP {php_ver}")
    else:
        report("FAIL", "requirements", f"status {code}")

    # Log out, so repeated health checks do not accumulate active auth tokens.
    code, _, _ = request("/api/v1/App/destroyAuthToken", {**token_headers, "Content-Type": "application/json"},
                         "POST", json.dumps({"token": token}).encode())
    code_after, _, _ = request("/api/v1/App/user", token_headers)
    report("OK" if code == 200 and code_after == 401 else "FAIL", "api: logout",
           f"destroyAuthToken {code}, token afterwards {code_after} (expected 401)")
    return fails


if __name__ == "__main__":
    sys.exit(min(main(), 100))
