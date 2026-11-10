# Validation categories

- Hard fail: nonzero validation caused by current work. Fix within retry limit.
- Soft fail: check cannot run in the environment. Record exact reason.
- Pre-existing fail: reproduce on base or prove it is unrelated. Record and continue only when the workflow permits.
- Regression: a previously green behavior fails after the change. Blocks success.

Do not declare success with unresolved regression, missing acceptance evidence or failed mandatory gate.

