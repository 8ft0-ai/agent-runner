# Independent review: offline authentication PR

You are an independent reviewer of the synthetic pull request PR-17.
Read review/PR-17.md, review/PR-17.diff and the actual repository files.
The existing unit tests pass. Do not assume that passing tests mean the
PR is safe. Distinguish material defects from harmless style changes.

Do not modify application code, tests or PR materials. Write only
src/review.json as the review result, with exactly this JSON structure:

{
  "verdict": "GO or CHANGES_REQUIRED",
  "findings": [
    {
      "path": "relative/source/file.py",
      "severity": "high or medium or low",
      "summary": "specific defect",
      "evidence": "observed mechanism or concrete reproduction",
      "recommendation": "smallest necessary repair"
    }
  ],
  "summary": "one concise reason for the verdict"
}

Use one finding per distinct material defect and no speculative findings.
Choose GO only when no changes are required. No source changes or external
services are needed for this review; all data is synthetic and offline.
