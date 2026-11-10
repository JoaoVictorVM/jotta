# Workflow: retomada e cancelamento

## Retomar

1. Leia `current-run.json` e valide o estado externo.
2. Confirme branches, PRs, SHAs, arquivos e testes antes de confiar no registro.
3. Nao repita uma etapa cuja evidencia ainda seja valida.
4. Se houver divergencia, registre e retome do ultimo checkpoint comprovado.

## Cancelar

1. Pare novas mutacoes.
2. Nao reverta, descarte ou limpe trabalho automaticamente.
3. Registre status `cancelled`, ponto de parada e artefatos existentes.
4. Informe como retomar ou remover os artefatos de forma segura.
