# Lean spec contract

Use only for a complete `HARNESS_RUN` with `profile: lean`.

## Inputs

Read the prepared context packet, the target feature excerpt, current code patterns listed by the packet and existing dependency outcomes. Open additional project files only when a concrete decision cannot be made from those inputs. Do not rescan the whole repository and do not repeat discovery already recorded for the current wave.

## Output

Create `spec.md` and `plan.md` under `.planning/features/<feature-id>-<slug>/`.

The spec contains only applicable sections: scope, existing patterns, components and exact paths, contracts or data model, business and error rules, acceptance tests, assumptions and risks. The plan contains 1 to 5 ordered phases and concise steps describing what to change without repeating the spec.

## Decisions

- Follow established code patterns and choose the smallest implementation satisfying the PRD.
- Use an industry-standard default only when the PRD and codebase are silent, and record it as an assumption.
- Stop for a human gate on product ambiguity, security-sensitive choices, payments, personal data or a completed-feature contract change.
- A missing external dependency blocks the feature unless it belongs to the same authorized execution and is ordered earlier.

## Validation

Before saving, confirm paths are plausible, dependencies are ready, acceptance criteria are represented and the plan is executable. Read both saved files once. Do not create a separate reviewer in lean mode unless `prepare` marks the task high risk.
