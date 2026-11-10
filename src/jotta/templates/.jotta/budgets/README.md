# Controle de orçamento

O budget guard combina duas medidas independentes:

- uso global informado pelo provedor, quando disponivel;
- consumo local da execucao, calculado por tokens e custo estimado.

O maior percentual conhecido determina a decisao. Medicao ausente nunca deve ser apresentada como zero real. A origem fica registrada em `state/usage.json`.

`providers.json` declara a origem ativa. O harness nao inventa uma API de cota: quando a plataforma oferece uma ferramenta de uso, o agente consulta essa ferramenta e grava o percentual com `record`. Quando nao oferece, registra `unavailable` e usa somente os limites locais da execucao conforme a politica.

## Comandos

```powershell
python .harness/scripts/budget_guard.py status
python .harness/scripts/budget_guard.py check --checkpoint before-feature --scope feature
python .harness/scripts/budget_guard.py record --input-tokens 1200 --output-tokens 300 --estimated-cost-usd 0.08
python .harness/scripts/budget_guard.py record --provider-usage-percent 82 --source provider-api
python .harness/scripts/budget_guard.py record --provider-usage-unavailable
python .harness/scripts/budget_guard.py reserve --id spec-f03 --input-tokens 20000 --output-tokens 5000 --estimated-cost-usd 1.00
python .harness/scripts/budget_guard.py release --id spec-f03
python .harness/scripts/budget_guard.py authorize --scope feature --until-percent 90 --reason "concluir feature atual"
python .harness/scripts/budget_guard.py clear-authorization
```

## Codigos de saida

| Codigo | Significado |
|---|---|
| 0 | Pode continuar, inclusive aviso ou autorizacao valida |
| 2 | Human gate obrigatorio |
| 3 | Hard stop, nao pode ser sobrescrito |
| 4 | Medicao obrigatoria indisponivel |

Uma autorizacao vale somente para o escopo registrado e nunca ultrapassa o hard stop. O orquestrador deve verificar o budget entre etapas. Nenhum sensor consegue interromper uma resposta de modelo que ja esta em andamento.
