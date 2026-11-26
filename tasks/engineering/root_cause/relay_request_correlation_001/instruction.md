# Investigate lost tool results in a local inference relay

A simulated inference-only relay serves several OpenCode sessions. Single-request
tests work, but when one session has multiple outstanding tool calls, some
results cannot be delivered. An operator recently saw a provider 429 in the
logs and suggested increasing retries or changing the provider.

Inspect the code, protocol note, logs, and actual tests. Find and repair the
root cause with the smallest justified change. Preserve the public API
and request identity semantics. Do not change provider selection, retry
policy, permissions, documentation or logs. Do not add services/dependencies.

Run the relevant repository tests and explain (briefly) the cause,
correction and evidence that the fix works. All execution is local;
there are no live providers or credentials in this fixture.
