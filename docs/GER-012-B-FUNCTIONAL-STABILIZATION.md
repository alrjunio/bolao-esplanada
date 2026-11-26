# GER-012-B — Estabilização funcional da V3.0 Launch

## Escopo
Somente correções funcionais, interface, Radar, pontuação, documentos e preparação da homologação. Nenhuma alteração no ambiente de produção ou merge na main.

## Ajustes realizados nesta ordem
- Frontend `app/static/index.html`: formulário do Radar diferencia campo de índice vazio de índice 0, evitando registro silencioso de uma cotação não preenchida. Ajustes modestos em navegação responsiva.
- `tests/test_launch_editorial.py`: cenário adicional de índice editorial ausente, que espera HTTP 422.
- O backend já valida índice inteiro de 0 a 100; a intervenção mantém seu contrato e o banco existente.
- Não foi incorporada funcionalidade secundária.

## Revisão estática
- `app/scoring.py`: regras ministeriais, mudanças estruturais, total e extras revisados em relação ao regulamento. Não houve alteração unilateral de pesos.
- `app/main.py`: rotas de Radar, persistência de registros editoriais no JSON `game.state` e apresentação pública do ranking preservadas.
- Termos, política e regulamento têm conteúdo versionado, mas a identificação do responsável, canal real de atendimento e prazo de retenção ainda dependem de definição institucional antes da divulgação pública.

## Execução / evidências
- GitHub: commits registrados na branch `release/v3.0-launch`.
- Não foi possível executar nesta sessão a suíte completa a partir de um clone: o ambiente de execução não resolve `github.com`. A suíte não deve ser declarada aprovada com base apenas na leitura.
- Não houve teste de navegador real mobile/desktop nesta sessão.
- Foram consultados PR #1 e issues; nenhum apontamento do CHAT 03 estava registrado nesses locais no instante da consulta. Relatório de homologação do CHAT 03 continua necessário.

## Encaminhamento obrigatório
A alteração no frontend exige novo SHA candidato. CHAT 03 deve reexecutar cenários do Radar (índice ausente/0/100/fora da faixa, adição e remoção), navegação mobile, integração dos endpoints, pontuação e persistência. CHAT 02 deve preservar sua revisão independente de infraestrutura.

**Situação:** candidato funcional para testes, não homologado. PR permanece Draft, sem merge nem deploy.


## Atualização institucional posterior — GER-016-A (26/11/2026)
A pendência editorial de identificação do responsável, canal de atendimento e prazo de retenção foi resolvida documentalmente na GER-016-A: **Antonio Lazaro Rodrigues Junior**, **antoniolazarorjunior@gmail.com** e **12 meses após o encerramento da temporada 2027**. A execução operacional do descarte após o prazo e a verificação da elegibilidade de maiores de 18 anos devem ser validadas separadamente; a documentação não declara automação desses processos.
