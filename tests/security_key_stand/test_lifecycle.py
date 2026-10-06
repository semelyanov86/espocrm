"""The life of a user's keys (D-128): Reset, the administrator's recovery, another method, no keys, no exposure."""
import unittest

from fixture import ES256, METHOD, ORIGIN, World, must, totp

W = None


def setUpModule():
    global W
    W = World()
    unittest.addModuleCleanup(W.cleanup)
    W.start()


class LifecycleTest(unittest.TestCase):
    def test_reset_replaces_the_keys(self):
        user = W.user("reset")
        old, = W.enable(user, W.keys.key(ES256))
        session = W.session(user, old)

        options = must(W.setup_options(user, reset=True, client=session), "reset")["publicKey"]
        # The core Reset turns 2FA off at once; the hook drops the keys with it.
        self.assertEqual({"auth2FA": False, "auth2FAMethod": None}, W.security(user))
        self.assertIsNone(W.stored_keys(user))
        self.assertEqual(200, W.first_step(user)[0], "the password alone signs in while 2FA is off")

        new = W.keys.key(ES256)
        must(W.save_keys(user, [new.attest(options, ORIGIN)], client=session), "save the new key")
        self.assertEqual(1, W.stored_keys(user))
        self.assertEqual(401, W.second_step(user, old.code(W.options(user), ORIGIN), expect_denial=True)[0])
        self.assertEqual(200, W.second_step(user, new.code(W.options(user), ORIGIN))[0])

    def test_the_administrator_turns_2fa_off_when_keys_are_lost(self):
        user = W.user("recovery")
        W.enable(user, W.keys.key(ES256))

        must(W.admin.put(f"UserSecurity/{user.id}", {"auth2FA": False, "password": W.admin_password()}), "turn off")
        self.assertIsNone(W.stored_keys(user))
        self.assertEqual(200, W.first_step(user)[0])

    def test_another_method_drops_the_keys_and_its_step_still_works(self):
        user = W.user("totp")
        W.enable(user, W.keys.key(ES256))

        setup = must(W.admin.post("UserSecurity/action/getTwoFactorUserSetupData", {
            "id": user.id, "password": W.admin_password(), "auth2FAMethod": "Totp"}), "TOTP setup")
        must(W.admin.put(f"UserSecurity/{user.id}", {"auth2FA": True, "auth2FAMethod": "Totp",
                                                    "code": totp(setup["auth2FATotpSecret"]),
                                                    "password": W.admin_password()}), "switch to TOTP")
        self.assertIsNone(W.stored_keys(user))

        status, payload, reason = W.first_step(user)
        self.assertEqual((401, "second-step-required", "enterTotpCode", None),
                         (status, reason, payload["message"], payload["view"]))
        self.assertEqual(200, W.second_step(user, totp(setup["auth2FATotpSecret"]))[0])

    def test_a_user_without_keys_is_not_let_through(self):
        user = W.user("no-keys")
        key, = W.enable(user, W.keys.key(ES256))
        W.drop_stored_keys(user)

        status, payload, reason = W.first_step(user)
        self.assertEqual((401, "second-step-required"), (status, reason))
        self.assertEqual(("itvolgaSecurityKeyNone", "noKeys"), (payload["message"], payload["data"]["state"]))
        self.assertNotIn("publicKey", payload["data"])
        self.assertEqual(401, W.second_step(user, key.code({"rpId": "x", "challenge": "AAAA"}, ORIGIN), True)[0])

    def test_keys_are_not_exposed(self):
        user = W.user("exposure")
        W.enable(user, W.keys.key(ES256))

        record = must(W.admin.get(f"User/{user.id}"), "user")
        self.assertEqual([], [name for name in record if "securitykey" in name.lower()])
        self.assertEqual({"auth2FA": True, "auth2FAMethod": METHOD}, W.security(user))
        self.assertIn(W.admin.get("UserData")[0], (403, 404))


if __name__ == "__main__":
    unittest.main()
