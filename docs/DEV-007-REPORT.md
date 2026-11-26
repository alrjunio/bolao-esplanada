# DEV-007 — Consolidação técnica V3.0 Launch

**Emissor:** CHAT 01 — Desenvolvimento e Integração  
**Destino:** CHAT 00 — Gerência  
**Data:** 25/11/2026 (horário de Brasília)  
**Situação:** entrega de código em branch; homologação integral pendente.

## Identificação
- Repositório: `alrjunio/bolao-esplanada`
- Branch: `release/v3.0-launch`
- Base da `main`: `edc3d88beab6e118e99e56c8359435a67c6c0b70`
- Commit de referência antes deste relatório: `5dc41a3291d645fce24f3fe1aa98f089b133c518`
- PR #1: https://github.com/alrjunio/bolao-esplanada/pull/1 (Draft, sem merge)
- Comparação: 34 commits à frente da main, 26 arquivos alterados/adicionados, nenhum atrás.

## Implementado na branch
- Pontuação exibida com piso zero e saldo assinado preservado no motor.
- Remoção de desempates por nomes ou partidos; empate exibido não recebe critério adicional.
- Resposta pública de ranking limitada a apelido e pontos.
- Testes versionados de pontuação, bloqueios, persistência, ranking, radar e alterações estruturais.
- Interface com identidade institucional e estilos adaptáveis, Radar editorial manual e tutorial.
- Termos e privacidade acessíveis via `/legal` antes do cadastro.
- Regulamento e tutorial versionados em `docs/`.
- Arquivos de infraestrutura do CHAT 02 presentes na branch, inspecionados de forma estática; scripts de deploy/rollback produtivo permanecem intencionalmente bloqueados.

## Testes executados e evidências
- Execução local isolada, utilizando cópia auditada de `app/scoring.py`:
  `python -m unittest discover -v` — 15 testes executados, 15 aprovados (`OK`).
  Abrangência: ministros, partidos, situação, extras, quantidade, estruturas e critérios não confirmados.
- Análise sintática do JavaScript incorporado em `app/static/index.html`: `JS_PARSE_OK`.
- CI no GitHub: arquivo de workflow criado, mas consultas ao commit não expuseram runs PR-triggered nem statuses.
  **Não existe evidência disponível de execução completa do workflow.**
- Testes integrais FastAPI/SQLite, browser mobile, integração e staging: **não executados com evidência suficiente**.
- A causa exata da ausência dos runs não foi determinada; o conector de runs é limitado a eventos de Pull Request.

## Pendências bloqueantes para homologação
1. Executar e registrar a suíte completa de `python -m unittest discover -s tests -v` no checkout da branch.
2. Identificar o estado de GitHub Actions no painel do repositório e obter workflow verde ou relatório de execução equivalente.
3. Executar testes de integração com dois navegadores, bloqueios progressivos e persistência no ambiente isolado.
4. Validar staging, backup e restore com CHAT 02, sem tocar nos dados reais.
5. CHAT 03 homologar as regras e fluxos.
6. Publicar identificação do responsável pelos dados, canal de contato e prazo de retenção antes de inscrições públicas.
7. CHAT 00 autorizar explicitamente merge e deploy.

## Parecer
**Candidato técnico a homologação, não homologado.** A branch permanece independente da `main`; nenhum deploy, merge ou acesso ao banco de produção foi realizado.
