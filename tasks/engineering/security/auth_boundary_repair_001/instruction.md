# Repair a workspace authorisation boundary

The synthetic `workspace_docs` service checks the requested workspace against
the caller's tenant, memberships and scopes, but an internal report indicates
that supplying a document ID from another workspace can expose or modify that
document. Document IDs are global, while access is workspace-scoped.

Investigate and repair the authorisation boundary for **both read and update**,
without changing the public method signatures, successful response shapes,
revision behaviour, existing legitimate operations or architecture. A caller
authorised for multiple workspaces must still be unable to mix one workspace's
route with another workspace's document.

Use only the standard library. Change implementation files under `src/` only;
do not alter tests, security policy, task contracts, configuration or dependency
files. Explain the failure, the enforcement point and how authorised and
unauthorised requests were verified. This task uses synthetic identities only.
