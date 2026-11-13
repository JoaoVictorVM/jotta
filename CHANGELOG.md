# Changelog

Todas as mudancas relevantes deste projeto serao registradas aqui.

## Nao lancado

- Distribui o Jotta como pacote Python com o comando `jotta`, que substitui os scripts de `.harness/scripts/`.
- Move o conteudo instalado para os templates do pacote e renomeia a pasta do harness de `.harness/` para `.jotta/`.
- Consolida permissoes, orcamento e roteamento em `.jotta/policy/` e cria o estado de execucao sob demanda em `.jotta/runtime/state/`.
- Substitui `scripts/install.py` e `bootstrap.py` por `jotta install`, com `--dry-run`, `--force-overwrite` e `--no-git-exclude`.
- O `doctor` deixa de exigir exclusoes locais no Git e arquivos de estado.
- Move a arquitetura e as suposicoes do agente para `docs/`, adiciona os guias de conceitos e une as release notes a este changelog.
- Remove os prompts e workflows arquivados da v0.4. Eles continuam disponiveis na tag `v0.5.0`, em `.harness/prompts/archive/v0.4/` e `.harness/workflows/archive/v0.4/`.

## 0.5.0

- Adiciona os perfis `manual-classic`, `lean` e `strict`.
- Preserva integralmente os contratos das skills de PRD, spec e implementacao.
- Consolida a execucao em workflows de produto, mudanca e qualidade.
- Adiciona contexto progressivo, checkpoints e quality receipts compactos.
- Adiciona budget gate e roteamento de modelos por tarefa.
- Adiciona worktrees e sessoes visiveis gerenciadas pelo Orca.
- Adiciona adaptadores para Codex, Claude e OpenCode.
- Adiciona prompts, avaliacoes e verificacoes automatizadas.
- Prepara o projeto para distribuicao open source sob a licenca MIT.
- Usa smoke checks por feature no perfil lean e concentra a revisao semantica no final.
- Remove worktree e branch local somente depois de merge confirmado e verificacoes de seguranca.
- Registra estimativas de consumo por fase e trata os limites do provedor como human gate quando a plataforma os disponibiliza.
- Mantem prompts e workflows antigos em `archive/v0.4` para consulta, fora do contexto normal.

### Compatibilidade

O perfil `manual-classic` e a trilha de compatibilidade para o fluxo anterior, incluindo entrevistas, G1 a G4, planos, validacao detalhada e commits conforme o contrato preservado. O perfil `strict` reutiliza o contrato completo com automacao. O perfil `lean` e o novo padrao economico.

### Restricao conhecida

O adaptador Orca precisa do executavel `orca` ou `orca.exe` no ambiente em que o harness roda. O `doctor` informa quando ele nao esta acessivel.
