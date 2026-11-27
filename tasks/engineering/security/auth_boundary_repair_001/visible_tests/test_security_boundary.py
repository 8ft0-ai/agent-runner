from workspace_docs import Actor, Document, DocumentService, InMemoryStore, Workspace
from workspace_docs.service import DocumentNotFound, PermissionDenied


def scenario():
    store = InMemoryStore(
        [Workspace("alpha", "north"), Workspace("beta", "north"), Workspace("gamma", "south")],
        [Document("da", "alpha", "one", 1), Document("db", "beta", "private", 4),
         Document("dc", "gamma", "other-tenant", 2)],
    )
    actor = Actor("user", "north", frozenset({"alpha", "beta"}), frozenset({"docs:read", "docs:write"}))
    return DocumentService(store), store, actor


def blocked(action):
    try:
        action()
    except (DocumentNotFound, PermissionDenied):
        return
    raise AssertionError("cross-workspace operation was allowed")


def test_cross_workspace_document_id_does_not_bypass_route_scope():
    service, _, actor = scenario()
    blocked(lambda: service.read(actor, "alpha", "db"))
    assert service.read(actor, "beta", "db") == {"id": "db", "body": "private", "revision": 4}


def test_cross_workspace_update_is_rejected_without_side_effects():
    service, store, actor = scenario()
    blocked(lambda: service.update(actor, "alpha", "db", "overwritten"))
    assert store.document("db") == Document("db", "beta", "private", 4)
    assert service.update(actor, "beta", "db", "changed") == {"id": "db", "body": "changed", "revision": 5}


def test_requested_workspace_does_not_authorise_foreign_tenant_document():
    service, _, actor = scenario()
    blocked(lambda: service.read(actor, "alpha", "dc"))
    blocked(lambda: service.update(actor, "alpha", "dc", "tamper"))
