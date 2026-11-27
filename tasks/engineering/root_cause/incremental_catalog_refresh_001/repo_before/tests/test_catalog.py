import unittest

from catalog import Catalog, Source


class CatalogTests(unittest.TestCase):
    def test_empty_catalog(self):
        self.assertEqual(Catalog().view(), {})

    def test_combined_sorted_output(self):
        catalog = Catalog()
        result = catalog.refresh({"one": Source(1, b"Z|2\nA|4"), "two": Source(2, b"Z|3")})
        self.assertEqual(list(result.items()), [("A", 4), ("Z", 5)])

    def test_bad_quantities_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid quantity"):
            Catalog().refresh({"one": Source(1, b"A|-1")})
