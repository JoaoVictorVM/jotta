# Sensor: provider budget

## Comando

```powershell
python .harness/scripts/budget_guard.py check --checkpoint <checkpoint> --scope <feature|wave|run>
```

## Evidencia

Registre status, percentual efetivo, origem, percentual local, percentual do provedor, reservas e autorizacao aplicavel.

## Decisao

- Codigo 0: continuar e registrar aviso quando houver.
- Codigo 2: ativar `provider-budget-threshold` e aguardar decisao humana.
- Codigo 3: interromper no hard stop.
- Codigo 4: aplicar a politica de medicao indisponivel.

O sensor roda entre etapas e nao interrompe uma chamada de modelo em andamento.
