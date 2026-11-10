# Politicas

Esta pasta concentra as regras que limitam a execucao.

| Arquivo | Conteudo |
|---|---|
| `permissions.md` | Acoes permitidas, negadas e liberadas por perfil |
| `human-gates.md` | Situacoes que exigem decisao humana |
| `budget.json` | Limites de orcamento, faixas de decisao e checkpoints |
| `providers.json` | Origem do uso informado por cada provedor |
| `routing.json` | Classe de modelo por tarefa e modelos por provedor |

## Controle de orçamento

O budget guard combina duas medidas independentes:

- uso global informado pelo provedor, quando disponivel;
- consumo local da execucao, calculado por tokens e custo estimado.

O maior percentual conhecido determina a decisao. Medicao ausente nunca deve ser apresentada como zero real. A origem fica registrada em `.jotta/runtime/state/usage.json`.

`providers.json` declara a origem ativa. O harness nao inventa uma API de cota: quando a plataforma oferece uma ferramenta de uso, o agente consulta essa ferramenta e grava o percentual com `record`. Quando nao oferece, registra `unavailable` e usa somente os limites locais da execucao conforme a politica.

### Comandos

```powershell
jotta budget status
jotta budget check --checkpoint before-feature --scope feature
jotta budget record --input-tokens 1200 --output-tokens 300 --estimated-cost-usd 0.08
jotta budget record --provider-usage-percent 82 --source provider-api
jotta budget record --provider-usage-unavailable
jotta budget reserve --id spec-f03 --input-tokens 20000 --output-tokens 5000 --estimated-cost-usd 1.00
jotta budget release --id spec-f03
jotta budget authorize --scope feature --until-percent 90 --reason "concluir feature atual"
jotta budget clear-authorization
```

### Codigos de saida

| Codigo | Significado |
|---|---|
| 0 | Pode continuar, inclusive aviso ou autorizacao valida |
| 2 | Human gate obrigatorio |
| 3 | Hard stop, nao pode ser sobrescrito |
| 4 | Medicao obrigatoria indisponivel |

Uma autorizacao vale somente para o escopo registrado e nunca ultrapassa o hard stop. O orquestrador deve verificar o budget entre etapas. Nenhum sensor consegue interromper uma resposta de modelo que ja esta em andamento.

## Roteamento de modelos

Skills descrevem como trabalhar. O orquestrador escolhe o modelo antes de criar o agente que executara a skill.

`routing.json` usa classes de capacidade para evitar dependencia de nomes comerciais instaveis. Por padrao, `spec-writer` usa `efficient`, enquanto implementacao e revisao usam classes mais fortes.

### Configurar um modelo exato

Use o identificador aceito pela plataforma, nao apenas o nome de marketing. Exemplo ilustrativo:

```json
"anthropic": {
  "efficient": "ID_EXATO_DO_MODELO_SONNET_CONFIGURADO",
  "balanced": null,
  "strong": null,
  "review": null
}
```

Depois valide e resolva a rota:

```powershell
jotta models validate
jotta models resolve --task spec-writer --provider anthropic
```

Um valor `null` significa que o harness deve herdar o modelo da plataforma. Se a plataforma nao permite selecao por agente, a rota e apenas uma preferencia declarada. O orquestrador deve registrar o modelo efetivamente usado e nunca afirmar que aplicou uma rota sem evidencia.

Modelo mais barato nao reduz requisitos da skill, validacoes ou human gates. Se a qualidade observada cair, altere a rota, nao simplifique o contrato da skill.
### OpenCode and Orca

OpenCode can route to multiple providers, so configure exact provider model IDs in `routing.json` and pass the provider key to `jotta prepare`. The Orca agent id is separate and must match the installed Orca guide. See `.jotta/adapters/opencode/README.md`.
