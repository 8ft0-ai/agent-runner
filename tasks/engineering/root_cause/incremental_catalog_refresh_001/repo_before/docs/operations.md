# Import operations

The caller supplies every active source on each refresh. The importer copies
timestamps from the upstream manifest but can reuse them during recovery.
For a rejected manifest, the display must continue serving the last valid view.
The catalog is an in-memory object and has no persistent database.
