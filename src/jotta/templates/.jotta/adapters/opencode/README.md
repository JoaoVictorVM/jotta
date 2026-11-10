# OpenCode adapter

The harness stores capability routes, while OpenCode owns provider credentials and exact model availability.

1. List the exact model identifiers exposed by the installed OpenCode version.
2. Put those identifiers in `.harness/models/routing.json` under `providers.openai` or `providers.anthropic`.
3. Resolve a route with `model_router.py resolve --task <task> --provider <provider>`.
4. Start the run with `harness.py prepare ... --agent <installed-orca-agent-id> --provider <provider>`.

For example, if Orca exposes the OpenCode installation as `omp`, use `--agent omp`. Do not assume this id: use the id reported by the installed Orca guide or agent list. `platform` with null mappings inherits the model already selected by the active tool.

Provider selection and agent selection are independent. An OpenCode agent can use an OpenAI or Anthropic model when that provider is configured in OpenCode. A null route never invents a model name and never claims a switch occurred.
