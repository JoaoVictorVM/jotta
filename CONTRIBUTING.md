# Contributing

Obrigado por contribuir com o Jotta.

## Antes de alterar

- Abra uma issue para mudancas amplas de comportamento.
- Preserve o modo `manual-classic` quando alterar os caminhos lean ou strict.
- Nao inclua PRDs reais, logs, credenciais, caminhos pessoais ou estado de projetos consumidores.
- Nao adicione nomes de modelos que a plataforma instalada nao reconhece.
- Mantenha `AGENTS.md` como indice, nao como deposito de regras extensas.

## Validacao local

Execute:

```bash
python scripts/repository_check.py
python -m pytest
jotta --root src/jotta/templates doctor
jotta --root src/jotta/templates models validate
```

Skills novas ou alteradas precisam de frontmatter valido, descricao objetiva e referencias existentes. Mudancas de decisao precisam de um caso em `src/jotta/templates/.jotta/evals/cases/`.

## Pull requests

Explique:

- O problema resolvido.
- O comportamento anterior e o novo.
- O impacto nos perfis `manual-classic`, `lean` e `strict`.
- As verificacoes executadas.
- O efeito esperado no consumo de contexto.

Nao inclua saidas completas de agentes ou logs longos. Use recibos compactos e exemplos sanitizados.
