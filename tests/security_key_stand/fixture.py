"""Shared helpers of the security-key acceptance tests (D-128) on the local stand, synthetic users and keys.

Every test module builds its own World in setUpModule and registers World.cleanup with unittest.addModuleCleanup
before anything is created. The World turns 2FA on with the security-key method (the settings are restored by the
cleanup), creates synthetic users with random passwords (never printed) and drives software security keys
(authenticator.py: key pairs live in one PHP process of the run). Stored keys are inspected through SQL counts only.

The core limits failed sign-ins (AuthLog): more than 10 denials from one IP in 60 s block every login from loopback,
more than 10 wrong second-factor codes of one user in 5 minutes block that user. Tests that expect a denial call
World.denial() first, which waits while the stand's log already holds IP_DENIALS denials of the window (other modules
and earlier runs count too), and spread their denials over several users.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage03"))
from espo import BASE, Client, admin_credentials, espo_console, sql  # noqa: E402,F401

from authenticator import EDDSA, ES256, RS256, Authenticators, b64u, unb64u  # noqa: E402,F401

METHOD = "ItvolgaSecurityKey"
ORIGIN = "{0.scheme}://{0.netloc}".format(urlsplit(BASE))
RP_ID = urlsplit(BASE).hostname
IP_DENIALS = 8          # per window, below the core limit of 10
IP_WINDOW = 62          # seconds; the core window is 60


def must(result, what):
    status, payload, _ = result
    if status != 200:
        raise AssertionError(f"{what}: HTTP {status} {payload}")
    return payload


def totp(secret_base32, at=None):
    """RFC 6238 code of a base32 secret (SHA-1, 30 s, 6 digits), as the core TOTP method expects."""
    key = base64.b32decode(secret_base32 + "=" * (-len(secret_base32) % 8))
    counter = int((time.time() if at is None else at) // 30)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    return f"{(struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000:06d}"


class User:
    def __init__(self, uid, user_name, password):
        self.id, self.user_name = uid, user_name
        self.client = Client(user_name, password)
        self._login = (user_name, password)

    def secret(self):
        """The password for request bodies (UserSecurity asks for it again)."""
        return self._login[1]


class World:
    def __init__(self):
        self.run_id = secrets.token_hex(3)
        self.tag = f"SYNTH-{self.run_id}"
        self.admin = Client(*admin_credentials())
        self.keys = None
        self.user_ids = []
        self._saved = None

    def start(self):
        self.denial(0)  # right after another run: wait for the window of its denials
        settings = must(self.admin.get("Settings"), "settings")
        self._saved = {k: settings.get(k) for k in ("auth2FA", "auth2FAMethodList", "auth2FAForced")}
        methods = list(dict.fromkeys([*(settings.get("auth2FAMethodList") or []), "Totp", METHOD]))
        must(self.admin.put("Settings", {"auth2FA": True, "auth2FAMethodList": methods, "auth2FAForced": False}),
             "turn 2FA on")
        self.keys = Authenticators()

    def cleanup(self):
        failures = []
        for uid in reversed(self.user_ids):
            status = self.admin.delete(f"User/{uid}")[0]
            if status not in (200, 404):
                failures.append(f"User/{uid}: HTTP {status}")
        if self._saved is not None:
            status = self.admin.put("Settings", self._saved)[0]
            if status != 200:
                failures.append(f"Settings: HTTP {status}")
        if self.keys:
            self.keys.close()
        if failures:
            raise AssertionError("cleanup failed: " + ", ".join(failures))

    # --- users -----------------------------------------------------------------------------------------------
    def user(self, key):
        password = secrets.token_urlsafe(18) + "Aa1!"
        user_name = f"synth-sk-{self.run_id}-{key}"
        payload = must(self.admin.post("User", {
            "userName": user_name, "firstName": "Ключ", "lastName": f"{self.tag} {key}", "type": "regular",
            "isActive": True, "password": password, "passwordConfirm": password, "sendAccessInfo": False,
        }), f"user {key}")
        self.user_ids.append(payload["id"])
        return User(payload["id"], user_name, password)

    def admin_password(self):
        return admin_credentials()[1]

    # --- setup -----------------------------------------------------------------------------------------------
    def setup_options(self, user, reset=False, by_admin=False, client=None):
        """POST UserSecurity/action/getTwoFactorUserSetupData as the user (password sign-in, or the given session
        client) or as the administrator (by_admin)."""
        client, body = (self.admin, self.admin_password()) if by_admin else (client or user.client, user.secret())
        return client.post("UserSecurity/action/getTwoFactorUserSetupData",
                           {"id": user.id, "password": body, "auth2FAMethod": METHOD, "reset": reset})

    def save_keys(self, user, items, by_admin=False, client=None):
        """PUT UserSecurity/:id with the registered keys, as the setup modal saves its model."""
        client, body = (self.admin, self.admin_password()) if by_admin else (client or user.client, user.secret())
        return client.put(f"UserSecurity/{user.id}", {"auth2FA": True, "auth2FAMethod": METHOD, "password": body,
                                                      "itvolgaSecurityKeys": items})

    def enable(self, user, *keys):
        """Registers the keys for the user through the setup path; returns the keys."""
        options = must(self.setup_options(user), "setup options")["publicKey"]
        must(self.save_keys(user, [k.attest(options, ORIGIN, f"Ключ {i + 1}") for i, k in enumerate(keys)]),
             "save keys")
        return keys

    def security(self, user):
        return must(self.admin.get(f"UserSecurity/{user.id}"), "user security")

    # --- sign-in ---------------------------------------------------------------------------------------------
    def first_step(self, user):
        """GET App/user with the password only: (status, payload, X-Status-Reason)."""
        status, payload, headers = user.client.request("GET", "App/user",
                                                       headers={"Espo-Authorization-By-Token": "false"})
        return status, payload, headers.get("X-Status-Reason")

    def options(self, user):
        status, payload, reason = self.first_step(user)
        if status != 401 or reason != "second-step-required" or payload["data"].get("state") != "ready":
            raise AssertionError(f"first step: HTTP {status} {reason}")
        return payload["data"]["publicKey"]

    def second_step(self, user, code, expect_denial=False, browser_cookie=True):
        """GET App/user with the password and the code: (status, payload)."""
        if expect_denial:
            self.denial()
        headers = {"Espo-Authorization-By-Token": "false", "Espo-Authorization-Code": code}
        if browser_cookie:
            headers["Espo-Authorization-Create-Token-Secret"] = "true"
        status, payload, _ = user.client.request("GET", "App/user", headers=headers)
        return status, payload

    def session(self, user, key):
        """Signs in with the key and returns a client of the session (the auth token, as the browser keeps it; with
        a token the core does not ask for the second factor again)."""
        status, payload = self.second_step(user, key.code(self.options(user), ORIGIN), browser_cookie=False)
        if status != 200:
            raise AssertionError(f"sign-in: HTTP {status}")
        return Client(user.user_name, payload["token"])

    def denial(self, count=1):
        """Waits until `count` more denials stay within the budget below the core IP limit (denials of the window in
        the stand's log)."""
        while True:
            logged = int(sql(f"SELECT COUNT(*) FROM auth_log_record WHERE is_denied = 1 "
                             f"AND request_time > UNIX_TIMESTAMP() - {IP_WINDOW}")[0][0])
            if logged + count <= IP_DENIALS:
                return
            time.sleep(2)

    # --- stored state (counts and synthetic values only) --------------------------------------------------------
    def stored_keys(self, user):
        """Number of stored keys of the user (None when the field is empty)."""
        rows = sql(f"SELECT JSON_LENGTH(c_security_keys) FROM user_data "
                   f"WHERE user_id = '{_id(user.id)}' AND deleted = 0")
        value = rows[0][0] if rows else "NULL"
        return None if value == "NULL" else int(value)

    def stored_counters(self, user):
        rows = sql(f"SELECT JSON_EXTRACT(c_security_keys, '$[*].signCount') FROM user_data "
                   f"WHERE user_id = '{_id(user.id)}' AND deleted = 0")
        return rows[0][0] if rows else None

    def live_challenges(self, user, purpose):
        return int(sql(f"SELECT COUNT(*) FROM two_factor_code WHERE user_id = '{_id(user.id)}' "
                       f"AND method = '{purpose}' AND is_active = 1 AND deleted = 0")[0][0])

    def age_challenge(self, user, purpose, minutes):
        """Moves the user's live challenge of the purpose back in time."""
        sql(f"UPDATE two_factor_code SET created_at = created_at - INTERVAL {int(minutes)} MINUTE "
            f"WHERE user_id = '{_id(user.id)}' AND method = '{purpose}' AND is_active = 1")

    def drop_stored_keys(self, user):
        sql(f"UPDATE user_data SET c_security_keys = NULL WHERE user_id = '{_id(user.id)}'")


def _id(value):
    if not value.isalnum():
        raise ValueError("unexpected id")
    return value
