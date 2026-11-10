# Roteamento de modelos

Skills descrevem como trabalhar. O orquestrador escolhe o modelo antes de criar o agente que executara a skill.

`routing.json` usa classes de capacidade para evitar dependencia de nomes comerciais instaveis. Por padrao, `spec-writer` usa `efficient`, enquanto implementacao e revisao usam classes mais fortes.

## Configurar um modelo exato

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
python .harness/scripts/model_router.py validate
python .harness/scripts/model_router.py resolve --task spec-writer --provider anthropic
```

Um valor `null` significa que o harness deve herdar o modelo da plataforma. Se a plataforma nao permite selecao por agente, a rota e apenas uma preferencia declarada. O orquestrador deve registrar o modelo efetivamente usado e nunca afirmar que aplicou uma rota sem evidencia.

Modelo mais barato nao reduz requisitos da skill, validacoes ou human gates. Se a qualidade observada cair, altere a rota, nao simplifique o contrato da skill.
## OpenCode and Orca

OpenCode can route to multiple providers, so configure exact provider model IDs in `routing.json` and pass the provider key to `harness.py prepare`. The Orca agent id is separate and must match the installed Orca guide. See `.harness/adapters/opencode/README.md`.
