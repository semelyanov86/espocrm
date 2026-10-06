"""Signing in with a security key (D-128): the first step, accepted answers, the counter, refused answers."""
import json
import secrets
import unittest
from concurrent.futures import ThreadPoolExecutor

from fixture import EDDSA, ES256, ORIGIN, RP_ID, World, b64u

W = None


def setUpModule():
    global W
    W = World()
    unittest.addModuleCleanup(W.cleanup)
    W.start()


class SignInTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = W.user("sign-in")
        cls.k1, cls.k2 = W.enable(cls.user, W.keys.key(ES256), W.keys.key(EDDSA))

    def test_the_first_step_asks_for_the_registered_keys(self):
        status, payload, reason = W.first_step(self.user)

        self.assertEqual((401, "second-step-required"), (status, reason))
        self.assertEqual("itvolga:views/login-security-key", payload["view"])
        self.assertEqual("itvolgaSecurityKeyTouch", payload["message"])
        self.assertEqual("ready", payload["data"]["state"])
        options = payload["data"]["publicKey"]
        self.assertEqual(RP_ID, options["rpId"])
        self.assertEqual("discouraged", options["userVerification"])
        self.assertEqual({self.k1.id, self.k2.id}, {c["id"] for c in options["allowCredentials"]})
        self.assertEqual({("public-key", ("usb",))},
                         {(c["type"], tuple(c["transports"])) for c in options["allowCredentials"]})

    def test_each_key_signs_in_and_its_counter_is_stored(self):
        for key in (self.k1, self.k2):
            status, payload = W.second_step(self.user, key.code(W.options(self.user), ORIGIN))
            self.assertEqual(200, status)
            self.assertEqual(self.user.id, payload["user"]["id"])

        self.assertEqual([self.k1.counter, self.k2.counter], json.loads(W.stored_counters(self.user)))

    def test_an_answer_is_used_once(self):
        """With a counter the replay is refused twice over; a key without one (always zero) relies on the challenge."""
        code = self.k1.code(W.options(self.user), ORIGIN)

        self.assertEqual(200, W.second_step(self.user, code)[0])
        self.assertEqual(401, W.second_step(self.user, code, expect_denial=True)[0])

        user = W.user("no-counter")
        key, = W.enable(user, W.keys.key(EDDSA))
        code = key.code(W.options(user), ORIGIN, sign_count=0)

        self.assertEqual(200, W.second_step(user, code)[0])
        self.assertEqual(401, W.second_step(user, code, expect_denial=True)[0])

    def test_a_refused_answer_burns_the_challenge(self):
        options = W.options(self.user)

        self.assertEqual(401, W.second_step(self.user, self.k1.code(options, ORIGIN, tamper=True), True)[0])
        self.assertEqual(401, W.second_step(self.user, self.k1.code(options, ORIGIN), True)[0])
        self.assertEqual(200, W.second_step(self.user, self.k1.code(W.options(self.user), ORIGIN))[0])

    def test_a_newer_first_step_replaces_the_challenge(self):
        old = W.options(self.user)
        W.options(self.user)

        self.assertEqual(401, W.second_step(self.user, self.k2.code(old, ORIGIN), True)[0])

    def test_first_steps_at_once_leave_one_live_challenge(self):
        """Issuing is serialized per user: a superseded challenge never stays usable next to the newest one."""
        user = W.user("issue-race")
        W.enable(user, W.keys.key(ES256))

        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda _: W.first_step(user)[0], range(12)))

        self.assertEqual([401] * 12, statuses)
        self.assertEqual(1, W.live_challenges(user, "ItvolgaSecurityKey"))

    def test_an_expired_challenge(self):
        options = W.options(self.user)
        W.age_challenge(self.user, "ItvolgaSecurityKey", 6)

        self.assertEqual(401, W.second_step(self.user, self.k2.code(options, ORIGIN), True)[0])


class RefusedAnswersTest(unittest.TestCase):
    """Every answer gets a fresh challenge; at most five refusals per user (the core blocks a user after ten)."""

    CASES = {
        "other origin": dict(origin="https://evil.example.test"),
        "other RP ID": dict(rpId="example.test"),
        "registration ceremony": dict(type="webauthn.create"),
        "no user presence": dict(flags=0x00),
        "tampered signature": dict(tamper=True),
        "unknown key": dict(credentialId=b64u(secrets.token_bytes(48))),
        "other user handle": dict(userHandle=b64u(b"other-user")),
        "attested data in a sign-in": dict(flags=0x41),
    }

    def test_spoiled_answers(self):
        cases = list(self.CASES.items())

        for part in (cases[:4], cases[4:]):
            user = W.user(f"refused-{secrets.token_hex(2)}")
            key, = W.enable(user, W.keys.key(ES256))

            for case, spoil in part:
                with self.subTest(case):
                    code = key.code(W.options(user), ORIGIN, **spoil)
                    self.assertEqual(401, W.second_step(user, code, expect_denial=True)[0])

            self.assertEqual(200, W.second_step(user, key.code(W.options(user), ORIGIN))[0], "the key still works")

    def test_codes_that_are_not_answers(self):
        user = W.user("garbage")
        key, = W.enable(user, W.keys.key(ES256))

        for case, code in {"not base64url": "abc!", "not JSON": b64u(b"{"), "oversized": "A" * 7000}.items():
            with self.subTest(case):
                W.options(user)
                self.assertEqual(401, W.second_step(user, code, expect_denial=True)[0])

        self.assertEqual(200, W.second_step(user, key.code(W.options(user), ORIGIN))[0])

    def test_the_counter_must_grow(self):
        user = W.user("counter")
        key, = W.enable(user, W.keys.key(ES256))

        self.assertEqual(200, W.second_step(user, key.code(W.options(user), ORIGIN, sign_count=5))[0])
        self.assertEqual(401, W.second_step(user, key.code(W.options(user), ORIGIN, sign_count=5), True)[0])
        self.assertEqual(401, W.second_step(user, key.code(W.options(user), ORIGIN, sign_count=0), True)[0])
        self.assertEqual(200, W.second_step(user, key.code(W.options(user), ORIGIN, sign_count=6))[0])
        self.assertEqual([6], json.loads(W.stored_counters(user)))


    def test_one_answer_sent_at_once_passes_once(self):
        """Keys without a counter (always zero) rely on the challenge alone: it is consumed by one request only."""
        user = W.user("race")
        key, = W.enable(user, W.keys.key(ES256))
        code = key.code(W.options(user), ORIGIN, sign_count=0)
        W.denial(4)

        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = sorted(pool.map(lambda _: W.second_step(user, code)[0], range(5)))

        self.assertEqual([200, 401, 401, 401, 401], statuses)


if __name__ == "__main__":
    unittest.main()
