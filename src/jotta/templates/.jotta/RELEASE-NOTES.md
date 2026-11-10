# v0.5.0

## Resultado

Esta versao reduz o contexto padrao sem remover o fluxo manual que ja funcionava.

- Preserva integralmente os contratos antigos de `prd-writer`, `spec-writer` e `implement-feature` em referencias carregadas sob demanda.
- Introduz os perfis `manual-classic`, `lean` e `strict`.
- Consolida a operacao atual em tres workflows: `product`, `change` e `quality`.
- Usa smoke checks por feature no perfil lean e concentra revisao semantica no final.
- Exige worktree gerenciada pelo Orca para GitHub autonomo e abre o agente em terminal visivel.
- Remove worktree e branch local somente depois de merge confirmado e verificacoes de seguranca.
- Gera pacotes de contexto compactos e recibos de qualidade com logs fora do prompt.
- Registra estimativas de consumo por fase e mantem os limites do provedor como human gate quando a plataforma os disponibiliza.
- Mantem prompts antigos e workflows antigos em `archive/v0.4` para consulta, sem inclui-los no contexto normal.

## Compatibilidade

O modo `manual-classic` e a trilha de compatibilidade para o fluxo anterior, incluindo entrevistas, G1 a G4, planos, validacao detalhada e commits conforme o contrato preservado. O modo `strict` reutiliza o contrato completo com automacao. O modo `lean` e o novo padrao economico.

## Restricao conhecida

O adaptador Orca precisa do executavel `orca` ou `orca.exe` disponivel no ambiente em que o harness rodar. O comando `doctor` informa quando ele nao esta acessivel.
