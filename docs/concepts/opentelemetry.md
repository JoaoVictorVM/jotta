# OpenTelemetry export

Jotta can send the usage it measures from the agents' transcripts (see [Budget and routing](./budget-and-routing.md#measured-usage)) to any backend that receives OpenTelemetry traces over OTLP/HTTP, such as Langfuse, Jaeger or an OpenTelemetry Collector. The export is off by default and the runtime still has no dependencies: it posts OTLP JSON with the standard library.

## The trace of a run

Each run becomes one trace:

```text
jotta.run                        run id, status, profile, total tokens and cost
  jotta.feature                  one per task, such as F01
    jotta.stage                  one per stage: planning, spec, implementation, quality, review
      chat claude-opus-5-5       one generation per model, with its tokens and cost
```

- **Times:** the run, feature and stage spans cover the task periods that `jotta prepare` opens and `jotta checkpoint` and `jotta finish` close. A generation covers its first and last message.
- **Usage:** only the generations carry the `gen_ai.usage.*` attributes, `gen_ai.usage.cost` and Langfuse's `langfuse.observation.usage_details` and `langfuse.observation.cost_details`. A backend that adds the generations up therefore counts every token once. The parent spans keep their totals under `jotta.*`, such as `jotta.output_tokens` and `jotta.cost_usd`.
- **Unpriced models:** a model without a price in `.jotta/policy/pricing.json` has no cost attribute, and `jotta.unpriced_messages` counts its messages.
- **Blocked runs:** the root span of a blocked run has an error status with the blocker.
- **Ids:** trace and span ids derive from the run id, so exporting the same run again updates its trace instead of adding a second one.

## Configuration

In `.jotta/config.yaml`:

```yaml
telemetry:
  otel:
    enabled: false
    endpoint: http://localhost:4318/v1/traces
    service_name: jotta
```

With `enabled: true`, `jotta finish` exports the run and adds the outcome under `trace` in its output. An unreachable endpoint never blocks `finish`: the outcome is `failed`, with the error.

`jotta export-trace` exports the current run at any time, or another one with `--run <run-id>`, whether or not `enabled` is set. `--dry-run` prints the OTLP payload without sending it.

The standard OpenTelemetry variables take precedence over `config.yaml`, so credentials stay out of versioned files:

| Variable | Effect |
|---|---|
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | The full traces URL. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | The base URL. Jotta appends `/v1/traces`. |
| `OTEL_EXPORTER_OTLP_TRACES_HEADERS`, `OTEL_EXPORTER_OTLP_HEADERS` | Headers as `key=value` pairs separated by commas, with values URL-encoded. |

Jotta always sends JSON over HTTP and ignores `OTEL_EXPORTER_OTLP_PROTOCOL`. An endpoint that only speaks gRPC, usually on port 4317, rejects the export. Only `http` and `https` URLs are accepted.

## Langfuse

Langfuse receives OTLP/HTTP traces at `/api/public/otel`. Its cloud regions are:

- `https://cloud.langfuse.com` for the EU;
- `https://us.cloud.langfuse.com` for the US.

A self-hosted instance uses its own URL.

1. Build the credentials from the project's public and secret keys:

   ```bash
   AUTH=$(printf '%s' "pk-lf-...:sk-lf-..." | base64 | tr -d '\n')
   ```

2. Export the variables in the shell that runs the agent, not in a versioned file:

   ```bash
   export OTEL_EXPORTER_OTLP_ENDPOINT="https://cloud.langfuse.com/api/public/otel"
   export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic%20${AUTH},x-langfuse-ingestion-version=4"
   ```

   The header `x-langfuse-ingestion-version=4` makes the trace show up right away instead of minutes later.

3. Set `enabled: true` under `telemetry.otel`, or run `jotta export-trace` after a run.

The trace is named `jotta <run-id>`, and every span carries `langfuse.trace.metadata.run_id` so runs can be filtered. Generations appear with their model, usage and cost. A model with no price in Langfuse still shows the cost that Jotta computed.

## With the native telemetry of Claude Code

Claude Code exports its own OpenTelemetry metrics and events, and traces in beta. The `claude_code.token.usage` and `claude_code.cost.usage` metrics, for example, are labelled with `session.id`. That telemetry describes the agent's sessions. Jotta's trace describes the harness: which feature and stage each token went to. They complement each other and can use the same backend:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
```

Claude Code ignores these exporter variables in a repository's `.claude/settings.json`. Set them in the shell, in `~/.claude/settings.json` or in managed settings. The Claude Code documentation on monitoring lists every metric and the trace beta.

Because both read `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`, Jotta follows Claude Code to the same backend. The endpoint must accept HTTP: with `grpc` on port 4317, point Jotta elsewhere with `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`.
