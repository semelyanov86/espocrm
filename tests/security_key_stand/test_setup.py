"""Setting up the security-key method (D-128): creation options, saving a set of keys, refused registrations."""
import secrets
import subprocess
import time
import unittest

from fixture import EDDSA, ES256, METHOD, ORIGIN, RP_ID, RS256, World, b64u, espo_console, must, unb64u

W = None


def setUpModule():
    global W
    W = World()
    unittest.addModuleCleanup(W.cleanup)
    W.start()


class CreationOptionsTest(unittest.TestCase):
    def test_options_for_any_fido2_key_touch_only(self):
        user = W.user("options")
        data = must(W.setup_options(user), "setup options")
        options = data["publicKey"]

        self.assertEqual(5, data["maxKeys"])
        self.assertEqual(RP_ID, options["rp"]["id"])
        self.assertEqual(32, len(unb64u(options["challenge"])))
        self.assertEqual(user.id.encode(), unb64u(options["user"]["id"]))
        self.assertEqual(user.user_name, options["user"]["name"])
        self.assertEqual([ES256, EDDSA, RS256], [p["alg"] for p in options["pubKeyCredParams"]])
        self.assertEqual("none", options["attestation"])
        self.assertEqual("discouraged", options["authenticatorSelection"]["userVerification"])
        self.assertEqual("discouraged", options["authenticatorSelection"]["residentKey"])
        self.assertNotIn("authenticatorAttachment", options["authenticatorSelection"])
        self.assertEqual([], options["excludeCredentials"])

    def test_the_password_is_checked_again(self):
        user = W.user("password")
        status, _, _ = user.client.post("UserSecurity/action/getTwoFactorUserSetupData", {
            "id": user.id, "password": "wrong-" + secrets.token_hex(4), "auth2FAMethod": METHOD})
        self.assertEqual(403, status)

    def test_a_wrong_rp_id_override_is_a_configuration_error(self):
        user = W.user("rp")
        try:
            saved = espo_console("config:get", "itvolgaSecurityKeyRpId").strip()
        except subprocess.CalledProcessError:
            saved = ""  # not set; restored as null, which the method reads the same way (no override)
        espo_console("config:set", "itvolgaSecurityKeyRpId", "evil.example.test")
        time.sleep(3)
        try:
            status, payload, _ = W.setup_options(user)
            self.assertEqual(403, status)
            self.assertEqual("2faMethodNotConfigured", (payload or {}).get("messageTranslation", {}).get("label"))
        finally:
            if saved in ("", "null", "NULL"):
                espo_console("config:set", "itvolgaSecurityKeyRpId", "null", "--type=json")
            else:
                espo_console("config:set", "itvolgaSecurityKeyRpId", saved)
            time.sleep(3)
        must(W.setup_options(user), "setup options after the restore")


class SaveKeysTest(unittest.TestCase):
    def test_a_set_of_keys_is_saved_in_one_request(self):
        user = W.user("set")
        options = must(W.setup_options(user), "setup options")["publicKey"]
        keys = [W.keys.key(ES256), W.keys.key(EDDSA), W.keys.key(RS256)]
        items = [k.attest(options, ORIGIN, name) for k, name in zip(keys, ["Основной", "Запасной", None])]

        self.assertEqual({"auth2FA": True, "auth2FAMethod": METHOD}, must(W.save_keys(user, items), "save keys"))
        self.assertEqual(3, W.stored_keys(user))
        self.assertEqual({"auth2FA": True, "auth2FAMethod": METHOD}, W.security(user))

    def test_the_administrator_sets_up_a_user(self):
        user = W.user("by-admin")
        options = must(W.setup_options(user, by_admin=True), "setup options")["publicKey"]
        key = W.keys.key(ES256)

        must(W.save_keys(user, [key.attest(options, ORIGIN)], by_admin=True), "save keys")
        self.assertEqual(1, W.stored_keys(user))
        self.assertEqual(200, W.second_step(user, key.code(W.options(user), ORIGIN))[0])

    def test_not_a_list_of_one_to_five_keys(self):
        user = W.user("count")
        options = must(W.setup_options(user), "setup options")["publicKey"]
        items = [W.keys.key().attest(options, ORIGIN) for _ in range(6)]

        self.assertEqual(400, W.save_keys(user, [])[0])
        self.assertEqual(400, W.save_keys(user, items)[0])
        self.assertEqual(400, W.save_keys(user, {"id": "x"})[0])
        self.assertIsNone(W.stored_keys(user))
        self.assertFalse(W.security(user)["auth2FA"])
        # Refused before the challenge is touched: five of the keys still register.
        must(W.save_keys(user, items[:5]), "five keys")
        self.assertEqual(5, W.stored_keys(user))

    def test_refused_registrations_leave_2fa_off(self):
        user = W.user("refused")
        cases = {
            "other origin": lambda o, k: [k.attest(o, "https://evil.example.test")],
            "other RP ID": lambda o, k: [k.attest(o, ORIGIN, rpId="example.test")],
            "other challenge": lambda o, k: [k.attest(o, ORIGIN, challenge=b64u(secrets.token_bytes(32)))],
            "sign-in ceremony": lambda o, k: [k.attest(o, ORIGIN, type="webauthn.get")],
            "no user presence": lambda o, k: [k.attest(o, ORIGIN, flags=0x40)],
            "one key twice": lambda o, k: [k.attest(o, ORIGIN), k.attest(o, ORIGIN)],
            "id not of the key": lambda o, k: [{**k.attest(o, ORIGIN), "id": b64u(secrets.token_bytes(16))}],
            "garbage": lambda o, k: [{"id": "!", "clientDataJSON": "x", "attestationObject": 5}],
            "not an object": lambda o, k: ["key"],
        }
        for case, items in cases.items():
            with self.subTest(case):
                options = must(W.setup_options(user), "setup options")["publicKey"]
                status, payload, _ = W.save_keys(user, items(options, W.keys.key()))
                self.assertEqual(403, status, payload)
                self.assertIsNone(W.stored_keys(user))
                self.assertFalse(W.security(user)["auth2FA"])

    def test_the_challenge_is_used_once_and_expires(self):
        user = W.user("challenge")
        key = W.keys.key()

        options = must(W.setup_options(user), "setup options")["publicKey"]
        self.assertEqual(403, W.save_keys(user, [key.attest(options, "https://evil.example.test")])[0])
        self.assertEqual(403, W.save_keys(user, [key.attest(options, ORIGIN)])[0], "burned by the refused attempt")

        old = must(W.setup_options(user), "setup options")["publicKey"]
        must(W.setup_options(user), "setup options again")
        self.assertEqual(403, W.save_keys(user, [key.attest(old, ORIGIN)])[0], "replaced by a newer one")

        options = must(W.setup_options(user), "setup options")["publicKey"]
        W.age_challenge(user, "ItvolgaSecurityKeySetup", 16)
        self.assertEqual(403, W.save_keys(user, [key.attest(options, ORIGIN)])[0], "expired")

        options = must(W.setup_options(user), "setup options")["publicKey"]
        must(W.save_keys(user, [key.attest(options, ORIGIN)]), "fresh")
        self.assertEqual(1, W.stored_keys(user))


if __name__ == "__main__":
    unittest.main()
