# Agent Runner

A manual GitHub Actions experiment runs OpenCode 2.4.2 against NVIDIA Nemotron on a standard Ubuntu runner. The synthetic task asks the agent to add JSON output to a Python status command.

Configure the repository Actions secret `NVIDIA_API_KEY` for the free NVIDIA endpoint. After the workflow is reviewed and merged, select **Actions → Hosted Nemotron pilot → Run workflow**. Each dispatch runs one task with a 20-minute job limit.

Download the workflow artifact to inspect the patch, tool completion trace, public test exit codes and run metadata. Final benchmark acceptance requires independent private grading against the matching starter revision.

For the OpenRouter comparison, configure the Actions secret `OPENROUTER_API_KEY` and select **OpenRouter** at dispatch. This selects the fixed model `nvidia/nemotron-3.5-super-vl:free` with the same agent, fixture and checks.

Select `root_cause.relay_request_correlation_001` at dispatch to test a repair to the simulated relay. The private grader uses the corresponding fixture.

For the Gemini comparison, set `GEMINI_API_KEY` to a key from a Gemini API Free-tier project with Cloud Billing disabled. Select **Gemini** to run `gemini-3.6-flash` through the Gemini Developer API.

The run record includes the OpenCode exit code and runtime, terminal error classification and HTTP status when supplied, retry-event count and latest retry, and the latest successful tool and its timestamp. The workflow reports its own deadline separately. The artifact includes tool summaries, public-check exit codes and the candidate patch when available. Raw model messages, tool payloads and provider response bodies stay out of the diagnostics.
