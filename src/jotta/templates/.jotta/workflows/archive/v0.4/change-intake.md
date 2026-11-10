# Workflow: entrada de mudancas

## Classificacao

| Classe | Artefato minimo | Encaminhamento |
|---|---|---|
| Bug | Brief com reproducao e teste de regressao | `bugfix.md` |
| Ajuste pequeno | Brief com objetivo e criterios | `small-change.md` |
| Refatoracao | Plano tecnico curto | `small-change.md` |
| Nova feature | Atualizacao do PRD, spec e plan | `feature-extension.md` |
| Evolucao grande | Revisao ampla ou novo PRD | Human gate |

## Regras

- Nao crie um novo PRD para todo pedido.
- Reclassifique um suposto bug quando o comportamento atual estiver de acordo com o PRD.
- Atualize o PRD quando o pedido criar capacidade, mudar criterio de aceite, contrato ou dependencias.
- Nunca renumere IDs existentes.
- Registre IDs locais somente em `.planning` e `.harness/state`.

## Saida

Crie o artefato minimo, atualize `tasks.json` e entregue ao `product-orchestrator` com classe, escopo, perfil e destino.

