# #104 — fixed GitHub-hosted model cohort (pre-pilot)

This manifest fixes the model cohort and scope for the OpenCode 2.4.2 comparison. It does **not** attest account-specific free quota, endpoint success, tool-call behaviour or model identity: those are live pilot gates.

| Profile | Role | Exact NVIDIA Chat Completions model ID | Public endpoint evidence |
|---|---|---|---|
| `super` | Primary | `nvidia/nemotron-3.5-super-vl-120b-a12b` | https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b?section=deploy |
| `minimax` | Primary | `minimaxai/minimax-m3.1-flash` | https://build.nvidia.com/minimaxai/minimax-m3.1-flash/build |
| `ultra` | Primary | `nvidia/nemotron-3-ultra-550b-a55b` | https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b |
| `lightning` | Efficiency comparator | `nvidia/nemotron-3.5-lightning-30b-a3b` | https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/build |
| `bolt` | One optional compatibility probe only | `stg/nvidia/nemotron-3.5-bolt-e4b` | https://build.nvidia.com/nvidia/nemotron-3.5-bolt-e4b/apireference |

All five fixed NVIDIA profiles use `https://integrate.api.nvidia.com/v1/chat/completions`. NVIDIA's Bolt API reference specifies a `stg/` prefix for standalone gateway requests; the unprefixed identifier is the Build playground default. No arbitrary route selection or paid fallback is introduced. The existing `super` OpenRouter route remains available for historical compatibility but must **not** be used in #104 scored attempts.

NVIDIA's Build pages advertise prototype/free API access and function calling for these model families. Availability to the configured account, free-only eligibility and the actual returned model identity remain **unverified** until an authorised GitHub-hosted pilot. Do not infer that any provider-returned alias is weight-equivalent to the requested model. An unexpected billed route, unsupported tool schema, exhausted quota or unresolved model identity is a model-specific HOLD.

## Frozen comparison contract

- Agent: `opencode` 2.4.2, installed with the existing pinned download and checksum.
- Public runner: `scripts/hosted-screen.py`, via `.github/workflows/hosted-nemotron.yml`, on GitHub-hosted Ubuntu 24.04.
- Provider: `NVIDIA` exclusively for scored attempts. Relay pins host, path and model ID; no dynamic inference routing.
- Request ceiling: 16 upstream calls per attempt. Agent timeout: 600 seconds. GitHub job timeout: 20 minutes. No automatic retry of a wrong-but-valid candidate.
- Tasks (eight): `root_cause.relay_request_correlation_001`, `feature.minimal_report_format_001`, `review.unsigned_observer_token_001`, `recovery.stale_handover_001`, `diagnostics.ci_failure_investigation_001`, `refactor.backwards_compatible_api_001`, `security.auth_boundary_repair_001`, `performance.incremental_regression_001`.
- `root_cause.incremental_catalog_refresh_001` remains a legacy runner option, **not** part of this eight-task cohort.
- Public evidence: `run.json`, `result.patch`; recorded `source_revision`, `run_id`, `requested_model`, `reported_models`, request status/count, usage where reported, and exit/latency.
- Private grader: unchanged canonical evaluator `405aa5d0d2552834980a01f147a8ef792994ee26`, exact reviewed runner SHA allowlist, 90-point mechanical score, preserved #102 provenance and grade receipts.

At most three primary pilots on the same root-cause task. Only successful, independently graded pilots enter the remainder of the first-pass eight-task cohort: 24 total primary attempts maximum inclusive of pilots. Lightning is separate (up to eight), and Bolt gets at most one optional probe. No automatic repetition.

## Release gates

1. Merge reviewed public profile change; pin its resulting *full* SHA in the **private grader** (retain the original runner SHA strictly for frozen #97 replay).
2. Re-run 16/16 historical parity and the private grader negative tests under GitHub Actions; independently review its exact head.
3. Use trusted main-only GitHub workflow dispatch for new-model pilots. Record source SHA, public run ID, patch SHA-256, and private grading receipt.
4. Pilot outcome gates further attempts. Public artefacts expire after five days: preserve important evidence privately within their retention window.

**Status:** public route identifiers documented; operational access, free quota, observed model identity and runtime tool compatibility not yet established.
