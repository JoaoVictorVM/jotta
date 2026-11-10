---
name: final-qa
description: Validate a feature, wave, product or pull request from compact computational evidence and applicable acceptance criteria. Use for requested, high-risk or final review, not every ordinary lean feature.
---

# Final QA

Read `.harness/workflows/quality.md`, the reviewer role and only the applicable review rubrics.

1. Require the compact quality receipt and paths to full logs. Do not load full logs unless the receipt is insufficient.
2. Read the scoped acceptance criteria, changed files and bounded diff.
3. Check behavior, regression, scope, architecture, security and evidence in proportion to risk.
4. Visual QA is conditional on UI acceptance or explicit request.
5. Return actionable findings with file, line, evidence, severity and expected correction.
6. Do not edit code, approve through another identity or merge.
7. Return `approved` only when mandatory checks pass and no blocking finding remains.
