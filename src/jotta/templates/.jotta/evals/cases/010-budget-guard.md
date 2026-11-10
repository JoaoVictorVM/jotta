# Caso 010: budget guard

## Objetivo

Validar aviso, human gate, autorizacao limitada, reservas e hard stop.

## Cenarios

1. Com uso abaixo de 70%, `check` retorna codigo 0 e `continue`.
2. Em 70%, retorna codigo 0 e `warning`.
3. Em 85%, retorna codigo 2 e `human-gate`.
4. Autorize somente `feature` ate 90%. Confirme que feature continua e wave nao herda a autorizacao.
5. Em 95%, confirme codigo 3 mesmo com autorizacao anterior.
6. Reserve agentes paralelos e confirme que a reserva entra no percentual antes do dispatch.
7. Libere a reserva e confirme sua remocao.
8. Marque uso do provedor indisponivel e confirme o fallback para budget local.

## Aprovacao

O fluxo nunca apresenta estimativa local como percentual real do provedor e nunca ultrapassa hard stop.
