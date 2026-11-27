"""Access to a requested workspace; does not resolve document ownership."""
from .models import Actor, Workspace


def can_use_workspace(actor: Actor, workspace: Workspace, scope: str) -> bool:
    return (
        actor.tenant_id == workspace.tenant_id
        and workspace.workspace_id in actor.workspace_ids
        and scope in actor.scopes
    )
