import unittest

from workspace_docs import Actor, Document, DocumentService, InMemoryStore, Workspace
from workspace_docs.service import PermissionDenied


class AuthorisedOperations(unittest.TestCase):
    def setUp(self):
        self.actor = Actor("analyst", "north", frozenset({"alpha"}), frozenset({"docs:read", "docs:write"}))
        self.store = InMemoryStore([Workspace("alpha", "north")], [Document("r-1", "alpha", "draft", 1)])
        self.service = DocumentService(self.store)

    def test_read(self):
        self.assertEqual(self.service.read(self.actor, "alpha", "r-1"),
                         {"id": "r-1", "body": "draft", "revision": 1})

    def test_update(self):
        self.assertEqual(self.service.update(self.actor, "alpha", "r-1", "approved")["revision"], 2)
        self.assertEqual(self.service.read(self.actor, "alpha", "r-1")["body"], "approved")

    def test_scope(self):
        actor = Actor("analyst", "north", frozenset({"alpha"}), frozenset({"docs:read"}))
        with self.assertRaises(PermissionDenied):
            self.service.update(actor, "alpha", "r-1", "denied")


if __name__ == "__main__":
    unittest.main()
