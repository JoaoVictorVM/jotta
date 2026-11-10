# Security Policy

## Supported version

A versao mais recente da linha 0.5 recebe correcoes de seguranca durante o desenvolvimento inicial do projeto.

## Reporting a vulnerability

Use o recurso privado `Report a vulnerability` na aba Security do GitHub. Nao publique credenciais, exploits funcionais, dados pessoais ou caminhos internos em uma issue publica.

Se o reporte privado nao estiver habilitado, abra uma issue sem detalhes sensiveis solicitando um canal privado de contato.

## Sensitive files

O repositorio publico nunca deve conter:

- `.jotta/runtime/`
- PRDs, specs ou planos reais de um produto
- `.env`, chaves, tokens ou credenciais
- logs de comandos, respostas de provedores ou dumps de banco
- estado de execucao de um projeto consumidor
- caminhos absolutos da maquina de um contribuidor

Execute `python scripts/repository_check.py` antes de publicar um release.
