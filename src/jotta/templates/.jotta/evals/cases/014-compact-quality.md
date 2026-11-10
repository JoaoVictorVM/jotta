# Compact quality evidence

## Request

Run the configured quality profile when a command emits a long log.

## Expected

- Save the full command output in `.harness/runtime/logs`.
- Return only status, duration, command, log path and a bounded excerpt.
- Stop on the first failure.
- Do not paste a successful full log into model context.
