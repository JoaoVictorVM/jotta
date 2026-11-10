# Commit plan schema

```json
{
  "schema_version": 1,
  "plan_id": "commit-plan-YYYYMMDD-HHMMSS",
  "source_kind": "working-tree",
  "source_fingerprint": "sha256",
  "commits": [
    {
      "id": "C01",
      "message": "feat(scope): descricao",
      "reason": "mudanca logica",
      "files": ["path"],
      "fingerprints": {"path": "sha256"}
    }
  ],
  "excluded": [],
  "unpushed_commits": []
}
```

Allowed source kinds: `working-tree`, `unpublished-history`, `initial-project`.
