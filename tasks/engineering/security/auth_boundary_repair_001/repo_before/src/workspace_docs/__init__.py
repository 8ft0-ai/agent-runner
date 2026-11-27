"""Synthetic workspace document API."""
from .models import Actor, Document, Workspace
from .service import DocumentService, PermissionDenied, DocumentNotFound
from .store import InMemoryStore
