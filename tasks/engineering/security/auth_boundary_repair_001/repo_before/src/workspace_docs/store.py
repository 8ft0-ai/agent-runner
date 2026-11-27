"""In-memory repository with globally indexed synthetic records."""
from .models import Document, Workspace


class InMemoryStore:
    def __init__(self, workspaces, documents):
        self.workspaces = {item.workspace_id: item for item in workspaces}
        self.documents = {item.document_id: item for item in documents}

    def workspace(self, workspace_id: str) -> Workspace | None:
        return self.workspaces.get(workspace_id)

    def document(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)

    def save(self, document: Document) -> None:
        self.documents[document.document_id] = document
