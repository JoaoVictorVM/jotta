# Sensores computacionais

Execute pelos comandos em `.harness/scripts/harness.py` e `run_quality.py`.

- `doctor`: integridade do harness.
- `validate-prd`: tabela de features, dependencias e ciclos.
- `validate-state`: JSON e estados conhecidos.
- `gate text`: travessoes em conteudo versionado.
- `gate staged`: caminhos locais, segredos e `.gitkeep` no stage.
- `gate branch`: formato da branch.
- `gate commit`: formato e texto da mensagem.
- `run_quality.py`: comandos configurados por perfil.

