"""Workspace-scoped document read and update operations."""
from .access import can_use_workspace
from .models import Actor, Document
from .store import InMemoryStore


class PermissionDenied(Exception):
    pass


class DocumentNotFound(Exception):
    pass


class DocumentService:
    def __init__(self, store: InMemoryStore):
        self.store = store

    def _document_for_request(
        self, actor: Actor, workspace_id: str, document_id: str, scope: str
    ) -> Document:
        workspace = self.store.workspace(workspace_id)
        if workspace is None:
            raise DocumentNotFound(workspace_id)
        if not can_use_workspace(actor, workspace, scope):
            raise PermissionDenied(workspace_id)
        document = self.store.document(document_id)
        if document is None:
            raise DocumentNotFound(document_id)
        return document

    def read(self, actor: Actor, workspace_id: str, document_id: str) -> dict:
        doc = self._document_for_request(actor, workspace_id, document_id, "docs:read")
        return {"id": doc.document_id, "body": doc.body, "revision": doc.revision}

    def update(
        self, actor: Actor, workspace_id: str, document_id: str, body: str
    ) -> dict:
        doc = self._document_for_request(actor, workspace_id, document_id, "docs:write")
        saved = Document(doc.document_id, doc.workspace_id, body, doc.revision + 1)
        self.store.save(saved)
        return {"id": saved.document_id, "body": saved.body, "revision": saved.revision}
