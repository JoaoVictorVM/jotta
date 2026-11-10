<a id="readme-top"></a>

<br />
<div align="center">
  <a href="https://github.com/JoaoVictorVM/jotta">
    <img src="./assets/jotta-icon.png" alt="Jotta logo" width="160">
  </a>

  <h1 align="center">Jotta</h1>

  <p align="center">
    <b>Um fluxo estruturado para desenvolvimento assistido por IA.</b>
    <br />
    Do PRD à entrega verificada, com contexto progressivo, estado local e controle de orçamento.
    <br />
    <a href="./README.md">English</a>
  </p>

  <p align="center">
    <a href="https://github.com/JoaoVictorVM/jotta/actions/workflows/validate.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/JoaoVictorVM/jotta/validate.yml?branch=main&amp;label=ci&amp;style=flat-square"></a>
    <a href="./LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"></a>
    <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square">
    <a href="https://github.com/JoaoVictorVM/jotta/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/JoaoVictorVM/jotta?style=flat-square"></a>
  </p>

  <p align="center">
    <a href="#install">Instalação</a>
    · <a href="#getting-started">Primeiro uso</a>
    · <a href="https://github.com/JoaoVictorVM/jotta/issues">Bugs e ideias</a>
    · <a href="./SECURITY.md">Segurança</a>
    · <a href="#contributing">Contribuição</a>
  </p>
</div>

## O que é o Jotta

O trabalho de programação com IA precisa de requisitos, uma tarefa delimitada, contexto adequado e evidências de que o resultado funciona.

**O Jotta conecta essas etapas dentro do seu projeto.** Ele reúne instruções para agentes, skills e um runtime em Python para passar do PRD às specs de features, implementação, verificações de qualidade e entrega. O estado recuperável registra o trabalho entre sessões.

Documentos de planejamento e estado de execução ficam locais no projeto consumidor. Os agentes continuam usando seus provedores de modelos configurados, e a entrega no GitHub usa GitHub e Orca.

## O que ele faz

**Entrega o contexto necessário para cada tarefa**

- Direciona pedidos de produto, mudanças e validação para workflows específicos.
- Carrega pacotes compactos de tarefa em vez de todo o histórico do projeto.
- Mantém PRDs, specs, planos e memória no projeto consumidor.

**Permite retomar a execução**

- Registra tarefas, checkpoints e status de execução em arquivos JSON locais.
- Preserva worktrees bloqueadas ou não verificadas para inspeção e recuperação.
- Usa worktrees gerenciadas pelo Orca na entrega autônoma no GitHub.

**Controla validação e custo**

- Configura verificações de qualidade nos perfis smoke, feature e full para o seu projeto.
- Aplica limites de orçamento que podem interromper a execução.
- Direciona tarefas para OpenAI, Anthropic ou o modelo herdado da plataforma.

## Perfis de execução

| Perfil | Fluxo |
|---|---|
| `manual-classic` | Entrevistas detalhadas e gates humanos G1 a G4. |
| `lean` | Contexto progressivo, smoke checks por feature e revisão final. Padrão para execução autônoma. |
| `strict` | Validação e revisão mais completas para cada feature. |

Trabalhos de alto risco em `lean` são elevados para `strict` na preparação. Consulte o [guia do runtime](./src/jotta/templates/.jotta/README.md) para o ciclo de execução e os comandos internos.

## Requisitos

| Ferramenta | Quando é necessária |
|---|---|
| Python 3.10+ | O pacote e o comando `jotta`. |
| Agente de programação compatível | Um agente que leia `AGENTS.md` ou `CLAUDE.md`. |
| Git | Fluxos com GitHub. |
| Orca CLI | Worktrees gerenciadas e sessões visíveis de agentes. |

O uso local funciona sem Git ou Orca. A execução autônoma no GitHub bloqueia quando o Orca está indisponível.

<a id="install"></a>

## Instalação

Instale o pacote e depois instale o harness no projeto em que deseja usá-lo:

```bash
python -m pip install git+https://github.com/JoaoVictorVM/jotta.git
cd /caminho/do/projeto
jotta install
jotta doctor
```

Os workflows e as skills copiados para o projeto chamam o comando `jotta`, então instale o pacote no ambiente Python que você usa nesse projeto.

O `jotta install` copia `.jotta/`, `.planning/`, `AGENTS.md` e `CLAUDE.md`, cria as pastas locais de planejamento e de runtime e adiciona os arquivos do harness ao `.git/info/exclude` do projeto, para que fiquem fora dos commits. Ele nunca sobrescreve um arquivo sem avisar.

| Opção | Efeito |
|---|---|
| `--target <pasta>` | Instala em outra pasta em vez da atual. |
| `--dry-run` | Mostra os arquivos, as pastas e as exclusões do Git sem escrever nada. |
| `--force-overwrite` | Substitui arquivos existentes do harness após confirmação. Use `--yes` para pular a pergunta. |
| `--no-git-exclude` | Não altera o `.git/info/exclude`, para projetos que versionam o harness. |

<a id="getting-started"></a>

## Primeiro uso

1. Escreva os requisitos do produto em `.planning/PRD.md` usando `prd-writer`.
2. Configure os comandos reais de validação do projeto em `.jotta/sensors/computational/gates.json`.
3. Execute `jotta doctor` no projeto consumidor.
4. Escolha um prompt de `.jotta/prompts/` ou fale com o agente em linguagem natural.

Por exemplo:

```text
Implemente o produto descrito em .planning/PRD.md usando o perfil lean,
de forma autônoma, com entrega no GitHub.
```

Você também pode pedir tarefas menores:

```text
Classifique e implemente este bug localmente.
Implemente F03 usando manual-classic.
Retome a execução registrada.
Mostre o status do harness.
```

## Estrutura do projeto

```text
src/jotta/                   Pacote Python e o comando jotta
src/jotta/templates/         Arquivos instalados no projeto: .jotta/, .planning/, AGENTS.md e CLAUDE.md
tests/                       Testes do pacote
scripts/repository_check.py  Verificações do repositório público e do pacote
scripts/self_test.py         Verificações de regressão dos templates
docs/                        Guia de publicação e recursos visuais
AGENTS.md                    Instruções para agentes que desenvolvem o Jotta
CLAUDE.md                    Ponte para AGENTS.md
```

## Desenvolvimento

Instale o pacote em modo editável com as ferramentas de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
jotta --help
python -m pytest
```

Execute as verificações na cópia do repositório fonte do Jotta:

```bash
python scripts/repository_check.py
python scripts/self_test.py
jotta --root src/jotta/templates doctor
jotta --root src/jotta/templates models validate
```

O CI executa essas verificações em pushes e pull requests. Consulte o [guia de publicação](./docs/PUBLISHING.md) para a preparação do repositório e a configuração do GitHub.

## Segurança e dados locais

Mantenha arquivos de runtime do projeto consumidor, documentos reais de planejamento, credenciais, logs e estado de execução fora do repositório público. O `.gitignore` do repositório fonte cobre os artefatos gerados durante o desenvolvimento.

Leia [SECURITY.md](./SECURITY.md) para relatar uma vulnerabilidade.

<a id="contributing"></a>

## Contribuição

Leia [CONTRIBUTING.md](./CONTRIBUTING.md) para conhecer o fluxo de desenvolvimento. Você pode ajudar com relatos de bugs, documentação e melhorias no harness. Mudanças de comportamento devem incluir ou atualizar um caso em `src/jotta/templates/.jotta/evals/cases/`.

## Licença

Distribuído sob a **licença MIT**. Consulte [LICENSE](./LICENSE).

<p align="right"><a href="#readme-top">Voltar ao topo</a></p>
