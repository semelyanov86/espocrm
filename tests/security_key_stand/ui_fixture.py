#!/usr/bin/env python3
"""Synthetic fixture for the security-key browser check (D-128; Playwriter, evidence.md).

  python3 tests/security_key_stand/ui_fixture.py create   → turns 2FA on with TOTP and the security key, creates
                                                            synth-sk-ui-key and synth-sk-ui-owner (no 2FA yet: they set
                                                            up keys in the browser — virtual keys, the owner's YubiKey)
                                                            and synth-sk-ui-totp (TOTP set up through the API);
                                                            passwords and the TOTP secret → <private>/ui-users.env (600)
  python3 tests/security_key_stand/ui_fixture.py delete   → removes the users and restores the 2FA settings

<private> is /data/itvolga/espo-private/stand/evidence/security-key (UI_FIXTURE_DIR overrides it), mode 700. Only ids
and counts are printed.
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import METHOD, Client, admin_credentials, must, totp  # noqa: E402

DIR = Path(os.environ.get("UI_FIXTURE_DIR", "/data/itvolga/espo-private/stand/evidence/security-key"))
STATE = DIR / "ui-fixture.json"
USERS_ENV = DIR / "ui-users.env"


def private_write(path, text):
    DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)


def create(admin):
    if STATE.exists():
        raise SystemExit(f"{STATE} exists: run delete first")
    settings = must(admin.get("Settings"), "settings")
    state = {"settings": {k: settings.get(k) for k in ("auth2FA", "auth2FAMethodList", "auth2FAForced")}, "users": {}}
    private_write(STATE, json.dumps(state))
    must(admin.put("Settings", {"auth2FA": True, "auth2FAMethodList": ["Totp", METHOD], "auth2FAForced": False}),
         "turn 2FA on")

    env = []
    for key in ("key", "owner", "totp"):
        password = secrets.token_urlsafe(14) + "Aa1!"
        user = must(admin.post("User", {
            "userName": f"synth-sk-ui-{key}", "firstName": "Ключ", "lastName": f"SYNTH-SK {key}", "type": "regular",
            "isActive": True, "password": password, "passwordConfirm": password, "sendAccessInfo": False}), key)
        state["users"][key] = user["id"]
        private_write(STATE, json.dumps(state))
        env += [f"UI_{key.upper()}_USERNAME=synth-sk-ui-{key}", f"UI_{key.upper()}_PASSWORD={password}"]

    admin_password = admin_credentials()[1]
    uid = state["users"]["totp"]
    setup = must(admin.post("UserSecurity/action/getTwoFactorUserSetupData", {
        "id": uid, "password": admin_password, "auth2FAMethod": "Totp"}), "TOTP setup")
    must(admin.put(f"UserSecurity/{uid}", {"auth2FA": True, "auth2FAMethod": "Totp", "password": admin_password,
                                          "code": totp(setup["auth2FATotpSecret"])}), "TOTP on")
    env.append(f"UI_TOTP_SECRET={setup['auth2FATotpSecret']}")
    private_write(USERS_ENV, "\n".join(env) + "\n")
    print("created users:", len(state["users"]), "->", USERS_ENV)


def delete(admin):
    if not STATE.exists():
        print("nothing to delete")
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    state["users"] = {key: uid for key, uid in state["users"].items()
                      if admin.delete(f"User/{uid}")[0] not in (200, 404)}
    if state["users"]:
        # Keep the state and the passwords: the next delete retries the users left.
        private_write(STATE, json.dumps(state))
        raise SystemExit(f"users not deleted: {len(state['users'])}; settings not restored yet")
    must(admin.put("Settings", state["settings"]), "restore settings")
    STATE.unlink()
    USERS_ENV.unlink(missing_ok=True)
    print("users deleted; settings restored")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("create", "delete"):
        raise SystemExit(__doc__)
    {"create": create, "delete": delete}[sys.argv[1]](Client(*admin_credentials()))
