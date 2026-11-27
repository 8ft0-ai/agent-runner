"""Records and verified synthetic request identity."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    subject: str
    tenant_id: str
    workspace_ids: frozenset[str]
    scopes: frozenset[str]


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    tenant_id: str


@dataclass(frozen=True)
class Document:
    document_id: str
    workspace_id: str
    body: str
    revision: int
