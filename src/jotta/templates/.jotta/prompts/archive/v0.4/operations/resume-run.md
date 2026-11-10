# Retomar uma execucao

## Prompt

```text
Retome a execucao atual do harness.

Leia `AGENTS.md`, `.harness/state/current-run.json`, `.harness/state/tasks.json` e os artefatos locais relacionados. Valide o estado externo antes de confiar nos registros: arquivos, hashes, branches, commits, PRs, checks e testes, conforme aplicavel.

Nao repita etapas cuja evidencia ainda seja valida. Se houver divergencia, registre-a e retome do ultimo checkpoint comprovado. Preserve o perfil, destino, escopo e autorizacoes da execucao original. Uma autorizacao nova nao deve ser presumida.
```
