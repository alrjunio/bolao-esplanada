# Bolão da Esplanada — V3.0 Launch

**Base:** V2.5 (`edc3d88beab6e118e99e56c8359435a67c6c0b70`)  
**Branch de preparação:** `release/v3.0-launch`  
**Situação:** em desenvolvimento; não homologada.

## Preservação de dados

- Não substituir nem excluir o volume persistente `bolao_data`.
- Não executar `docker compose down -v`, operações de reset ou exclusão de contas.
- Antes de implantar, obter backup verificado do SQLite e guardá-lo fora do volume de produção.
- Preservar o arquivo `.env`; nunca fazer commit de credenciais.
- Testar restauração e reversão em ambiente isolado antes de atualizar produção.
- O modelo atual mantém os palpites serializados em JSON nas tabelas existentes; as alterações desta branch não exigem migração destrutiva.

## Execução isolada dos testes

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Há um workflow de GitHub Actions em `.github/workflows/v3-launch-tests.yml`.
A existência do workflow não substitui a evidência de uma execução bem-sucedida.

## Regras de lançamento

- Pontuação exibida no ranking nunca inferior a zero, com saldo assinado preservado na ordenação.
- Cada bloqueio de pasta impede a alteração retroativa do registro correspondente.
- O primeiro bloqueio ministerial congela o total previsto e os palpites extras.
- Campos oficiais ainda não confirmados são neutros na apuração.
- Resultados oficiais dependem de fonte registrada no painel administrativo.
- Palpites individuais não devem ser divulgados automaticamente a outros participantes.
- O projeto não é um serviço oficial de governo.

## Portões para homologação

1. Testes automatizados aprovados em ambiente isolado.
2. Conferência de bloqueios e concorrência por duas sessões independentes.
3. Revisão das regras por CHAT 03.
4. Revisão de deploy, backup/rollback e HTTPS por CHAT 02.
5. Autorização expressa de merge pelo CHAT 00.

## Infraestrutura

O Docker Compose atual publica `127.0.0.1:8015` e usa `/data/bolao.sqlite3`.
As atualizações propostas pelo CHAT 02 só devem ser integradas após revisão dos
arquivos correspondentes e de sua compatibilidade com o volume existente.

**Não fazer merge na `main` ou deploy de produção antes da aprovação gerencial.**
