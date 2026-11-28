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

## Follow-up diagnostics (28 November 2026; not part of frozen scored cohort)

The first live root-cause task generated 90/90 patches for Super, MiniMax, Ultra and Lightning. Ultra and Lightning exited with code 1 at the original 16-upstream-request ceiling, despite all upstream requests returning 200. A further investigation may distinguish the local 429 budget gate from model failure; no first-pass scores may be replaced.

The `diagnostic` phase, restricted to OpenCode, NVIDIA, the root-cause task and Ultra/Lightning, permits **18 upstream calls** without changing `score` mode's 16-call ceiling or the canonical evaluator. The runner records `request_limit` and `local_budget_rejections`; a diagnostic run is not admitted by the private grader and must not enter the eight-task scoreboard.

The Bolt staging-prefixed one-probe route `stg/nvidia/nemotron-3.5-bolt-e4b` returned HTTP 404 twice. This branch tests the **unprefixed** Build playground ID `nvidia/nemotron-3.5-bolt-e4b` in exactly one additional explicitly authorised diagnostic probe. A failed probe remains HOLD without repeated trials. Model availability and free-tier behaviour are not inferred from documentation.

Super's requested `nvidia/nemotron-3.5-super-vl-120b-a12b` returned `private/nvidia/nemotron-3.5-super-120b-a12b`. Public developer forum reports describe the same mismatch but do not attest equivalence. The result remains identity-unverified pending an authoritative provider confirmation.

### Verified diagnostic outcomes

- **Ultra:** [run 46105182223](https://github.com/8ft0-ai/agent-runner/actions/runs/46105182223) — GitHub Actions SUCCESS, clean exit, public checks passed, 15/18 upstream calls HTTP 200, zero local limit rejections, 41.08 s.
- **Lightning:** [run 46105196267](https://github.com/8ft0-ai/agent-runner/actions/runs/46105196267) — GitHub Actions SUCCESS, clean exit, public checks passed, 14/18 upstream calls HTTP 200, zero local limit rejections, 35.40 s.
- **Bolt:** [run 46105311362](https://github.com/8ft0-ai/agent-runner/actions/runs/46105311362) — unprefixed NVIDIA gateway route SUCCESS, 11/11 upstream calls HTTP 200, exact reported model ID, clean exit, independent compatibility check passed, 13.99 s.

**Interpretation:** Ultra and Lightning completed within the **original 16-request allowance** in these new attempts; raising their diagnostic ceiling to 18 was *not necessary in these particular executions*. This supports run-to-run variation, not proof that the original budget caused the prior failure. Do not retroactively change the original first-pass run outcomes. Bolt's routing problem is fixed for the observed NVIDIA account; the alternate ID is a compatibility correction, not a new benchmark score.

## Provider-transient correction after the MiniMax feature failure

Original failed feature run [46107005162](https://github.com/8ft0-ai/agent-runner/actions/runs/46107005162) is **not silently retried or overwritten**. It had 2 upstream HTTP 429 responses, one transport failure, 11 local budget rejections, and a withheld non-source patch. The bounded diagnostic [46107717332](https://github.com/8ft0-ai/agent-runner/actions/runs/46107717332) reproduced 5 upstream 429s, one 503 and 10 local rejections with 16 upstream calls. The latter generated source-only changes and passing public tests but was not privately graded.

The corrected runner retries an upstream **HTTP 429 or 503 at most twice within the same agent request**. All attempts, including failed responses and connection failures, count against the unchanged **16-upstream-attempt limit** in `score` mode. The retry delay is 1 s then 2 s if the provider supplies no `Retry-After`; supplied valid seconds or HTTP dates are honoured only when the wait is at most 8 s. A longer or malformed `Retry-After` disables internal retries, rather than ignoring provider guidance or waiting indefinitely. Other HTTP statuses are not retried.

After the first *local* over-budget model request the runner records the budget rejection and terminates the isolated agent process group, preventing repeated local 429 loops. It records separate bounded fields for provider statuses, transport exception types, upstream retry count and delay, budget exhaustion, and patch withholding. It does not persist provider bodies, prompts, credentials, hidden grading data or arbitrary agent paths. The **600-second agent timeout** and the canonical private grading evaluator are unchanged.

These are changes to the execution policy for future #104 runs, not corrections to prior immutable results. Comparisons must record the runner SHA and treat earlier raw-provider-error attempts as a distinct execution-policy cohort. No live model rerun should occur until the new runner SHA has been admitted by the private grader after independent CI and parity validation.
