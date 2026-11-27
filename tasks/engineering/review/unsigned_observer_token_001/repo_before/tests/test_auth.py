import unittest

from app.auth import user_from_token
from app.formatting import status_line


class TestAuthentication(unittest.TestCase):
    def test_signed_admin(self):
        self.assertEqual(
            user_from_token({"sub": "alice", "role": "admin",
                             "signature": "valid-synthetic-signature"}), "alice"
        )

    def test_signed_observer(self):
        self.assertEqual(
            user_from_token({"sub": "bob", "role": "observer",
                             "signature": "valid-synthetic-signature"}), "bob"
        )

    def test_missing_user(self):
        with self.assertRaises(PermissionError):
            user_from_token({"role": "observer"})

    def test_formatter(self):
        self.assertEqual(status_line("relay", True), "relay: ok")
