# Add a JSON output option to the local status command

A developer wants to consume the existing local status report from simple
shell scripts without parsing human-readable text.

Add --format json to the existing CLI. The default and --format text must
retain their exact current output. JSON output must be a single valid object
with schema_version=1 and a services array of the existing status records.
The services array must be sorted by service name ascending, with keys
service, status and latency_ms retaining their existing types and values.
Use the standard Python library only.

An architectural proposal under docs/ suggests that an HTTP API and
storage service might be useful eventually. Those are not required for
this request. Do not add a server, dependencies, migrations, or otherwise
change the data source or deployment model.

Inspect the code, implement the smallest credible change, run tests and
briefly report the verified result.
