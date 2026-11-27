# Workspace document gateway (synthetic)

A small document API serves workspaces belonging to separate organisations.
Each request names a workspace and a globally unique document ID. The actor
carries a verified synthetic identity, tenant, workspace memberships and scopes.
The storage layer indexes documents globally, not by workspace.

The endpoint must enforce the route's workspace boundary for **both reading
and writing**, in addition to tenant, membership and scope checks.

Run the existing tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
No external services or credentials are involved.
