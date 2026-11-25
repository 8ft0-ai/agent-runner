# Agent Runner

A manual GitHub Actions experiment runs OpenCode 1.2.15 against NVIDIA Nemotron on a standard Ubuntu runner. The synthetic task asks the agent to add JSON output to a Python status command.

Configure the repository Actions secret `NVIDIA_API_KEY` for the free NVIDIA endpoint. After the workflow is reviewed and merged, select **Actions → Hosted Nemotron pilot → Run workflow**. Each dispatch runs one task with a 20-minute job limit.

Download the workflow artifact to inspect the patch, tool completion trace, public test exit codes and run metadata. Final benchmark acceptance requires independent private grading against the matching starter revision.
