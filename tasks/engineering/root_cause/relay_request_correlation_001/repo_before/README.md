# Simulated OpenCode inference relay

The relay deliberately models a small portion of tool result dispatch:
register outbound requests and deliver asynchronous responses back to their
originating sessions. The fixture is fully offline and has no network client.

Run the existing tests with:

    PYTHONPATH=src python3 -m unittest discover -s tests -v

Review docs/protocol.md and logs/relay.log before changing code.
