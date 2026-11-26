# Agent Runner

A manual GitHub Actions experiment runs OpenCode 2.4.2 against NVIDIA Nemotron on a standard Ubuntu runner. The synthetic task asks the agent to add JSON output to a Python status command.

Configure the repository Actions secret `NVIDIA_API_KEY` for the free NVIDIA endpoint. After the workflow is reviewed and merged, select **Actions → Hosted Nemotron pilot → Run workflow**. Each dispatch runs one task with a 20-minute job limit.

Download the workflow artifact to inspect the patch, tool completion trace, public test exit codes and run metadata. Final benchmark acceptance requires independent private grading against the matching starter revision.

For the OpenRouter comparison, configure the Actions secret `OPENROUTER_API_KEY` and select **OpenRouter** at dispatch. This selects the fixed model `nvidia/nemotron-3.5-super-vl:free` with the same agent, fixture and checks.

Select `root_cause.relay_request_correlation_001` at dispatch to test a repair to the simulated relay. The private grader uses the corresponding fixture.

The run record includes the OpenCode exit code and runtime, terminal error classification and HTTP status when supplied, retry-event count and latest retry, and the latest successful tool and its timestamp. The workflow reports its own deadline separately. The artifact includes tool summaries, public-check exit codes and the candidate patch when available. Raw model messages, tool payloads and provider response bodies stay out of the diagnostics.

## Codex relay comparison

[OpenCode Eval #86](https://github.com/8ft0-ai/opencode-eval/issues/86) uses the
same relay starter and public checks with Codex CLI 0.172.0. The dedicated
workflow verifies the Linux archive and binary digests and runs a local-tool
smoke check without provider credentials. For a live run, select `probe`
first and use `score` once that endpoint completes the probe. Only dispatch
Groq with a confirmed free credential or expenditure approval.

The workflow uses the native Responses API at the same provider base URL and
exact model ID for OpenRouter and Groq. Their OpenCode baselines used Chat
Completions. NVIDIA direct and Gemini Developer API are outside this runner
because the compared routes have no established native Responses interface.
The run uses a network-disabled workspace-write shell. OpenCode instead allowed
only its read, glob, grep and edit tools and used a 16-step limit. Codex uses
the same 600-second agent timeout with both request and stream retries set to
zero. The probe has a 90-second agent deadline.

Evidence includes only the candidate text patch, allowlisted tool summaries,
public-check exit codes, and synthesised numeric and categorical metadata.
Codex shell command labels are inferred. Tool timestamps are observed by the
harness. Served model and cost are left unknown when absent from the CLI
event stream. The independent private grader determines final correctness and
patch scope.
