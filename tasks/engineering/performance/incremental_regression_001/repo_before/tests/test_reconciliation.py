import unittest

from stream_merge import Record, reconcile


class ReconciliationBehaviour(unittest.TestCase):
    def test_replacement_and_append(self):
        first = Record("a", 1, "first")
        second = Record("b", 2, "first")
        newest = Record("a", 4, "update")
        tail = Record("c", 3, "update")
        snapshot = [first, second]
        result = reconcile(snapshot, iter([newest, tail]))
        self.assertEqual(result, [newest, second, tail])
        self.assertEqual(snapshot, [first, second])

    def test_repeated_update_wins_without_reordering(self):
        self.assertEqual(
            reconcile([Record("x", 0, "old")],
                      [Record("x", 1, "a"), Record("x", 2, "b")]),
            [Record("x", 2, "b")],
        )

    def test_duplicates_in_existing_remain_in_place(self):
        a = Record("a", 1, "first")
        duplicate = Record("a", 2, "second")
        update = Record("a", 3, "new")
        self.assertEqual(reconcile([a, duplicate], [update]), [update, duplicate])


if __name__ == "__main__":
    unittest.main()
