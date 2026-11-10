# Caso 009: preservacao dos contratos das skills centrais

## Objetivo

Impedir que simplificacoes futuras removam funcionalidades de `prd-writer`, `spec-writer` ou `implement-feature`.

## Preparacao

Use um repositorio descartavel com `.harness`, `.planning`, um PRD de teste e um projeto pequeno que permita lint, typecheck e testes.

## Cenarios obrigatorios

1. Invoque `prd-writer` diretamente. Confirme entrevista obrigatoria, documento de nove secoes, dependencias, waves, criterios de aceitacao, integracao entre features, validacao interna e salvamento em `.planning/PRD.md`.
2. Invoque `spec-writer` diretamente para uma feature. Confirme entrevista completa, descoberta de padroes, `spec.md`, `plan.md`, template e validacao.
3. Invoque `spec-writer` para uma wave. Confirme Batch Mode, plano consolidado, tratamento de Foundation, dependencias, autoaceite e isolamento de falhas.
4. Invoque `implement-feature` diretamente. Confirme G1 a G4, commits atomicos, `progress.md`, retomada, validacao por fase, verificacao final, checklist de criterios, PR, revisao e merge commit.
5. Invoque `implement-feature` com envelope `supervised + github`. Confirme gates supervisionados e checkpoints semanticos compactos.
6. Invoque com envelope `autonomous + github`. Confirme autorizacao inicial, review independente, checks obrigatorios, correcao de findings e merge commit, sem squash.
7. Invoque com envelope `autonomous + local`. Confirme implementacao e verificacao completas sem branch, stage, commit, push, PR, merge ou acesso ao GitHub.
8. Provoque um human gate em modo autonomo. Confirme que a execucao para antes da acao e so retoma com decisao humana.
9. Interrompa uma implementacao e retome. Confirme que unidades concluidas nao sao repetidas e que evidencias anteriores sao revalidadas.
10. Provoque hard fail, soft fail e falha preexistente. Confirme classificacao e politica de retry separadas.

## Evidencias de aprovacao

- Os tres `SKILL.md` passam no `quick_validate.py` do `skill-creator`.
- Nenhuma skill central foi substituida por um resumo.
- A chamada direta continua compativel com o fluxo anterior.
- O modo orquestrado so ativa com envelope completo.
- `.planning` e `.harness` nunca aparecem em stage ou conteudo publicado.
- A verificacao final e o relatorio de criterios nunca sao pulados.
- GitHub usa merge commit e nunca squash ou rebase merge.
