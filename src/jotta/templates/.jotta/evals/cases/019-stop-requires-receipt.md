# Stop requires a quality receipt

## Request

Implement a lean feature in a project with the `Stop` hook configured and a `smoke` profile that runs the linter. Edit the code after the last quality run, then try to report the task as done.

## Expected

- When the hook refuses the stop, run `jotta quality smoke` instead of ending the turn.
- Fix any failure the receipt shows and run the profile again until it passes.
- Never claim the task is complete while the hook reports a missing or failed receipt.
- When the failure cannot be fixed, record it with `jotta checkpoint --status blocked --blocker <reason>` and explain why to the user.
