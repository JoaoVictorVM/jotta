# Workflow: quality

Use for feature, wave, product or pull-request validation.

1. Run the requested computational profile before creating a semantic reviewer.
2. Keep full output under `.harness/runtime/logs/` and pass only the compact receipt to the model.
3. If deterministic checks pass and the active profile requires no semantic review, finish without another agent.
4. Create `final-qa` only for a requested review, high-risk scope, wave review, product review or failing evidence that needs diagnosis.
5. Review behavior, regressions, acceptance, architecture and security in proportion to risk. Visual QA is allowed only for UI acceptance or explicit request.
6. The reviewer reports findings and never edits code. Corrections return to an implementer and the failing checks run again.
7. A product is complete only after the `full` profile and final QA required by its profile pass.
