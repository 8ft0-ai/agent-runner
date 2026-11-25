import unittest

from briefing.cli import run


class TestText(unittest.TestCase):
    def test_default_text_output(self):
        self.assertEqual(run([]), "relay: degraded (90 ms)\nobserver: ok (32 ms)")

    def test_explicit_text_output(self):
        self.assertEqual(run(["--format", "text"]), run([]))
