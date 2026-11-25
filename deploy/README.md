# Preparação para publicação — V1.8 RC

Não publique antes de homologar as regras e o acesso em ambiente de teste. Este pacote mantém o código V1.7, acrescenta configuração de proxy, exclusões Git/Docker e impede alteração da configuração após finalização.

## GitHub (PowerShell, na pasta que contém compose.yaml)
Crie um repositório privado vazio chamado bolao-esplanada no GitHub. Preserve .env e o volume da instalação local. Não envie segredos.

    git init -b main
    git add .
    git diff --cached --name-only
    git commit -m "Bolao da Esplanada V1.8 RC"
    git remote add origin https://github.com/alrjunio/bolao-esplanada.git
    git push -u origin main

Caso já exista repositório ou remote, confira git status e git remote -v em vez de reinicializar. A URL pressupõe que o repositório tenha sido criado nessa conta.

## Servidor Linux (depois de configurar acesso ao repositório privado)
Confira se 8015 está livre com `sudo ss -ltnp | grep ':8015 '` e `docker ps`. Clone em um diretório novo. Configure .env com senha administrativa longa, convite secreto e COOKIE_SECURE=1. Não copie dados de teste para produção. Inicie com docker compose up -d --build. A porta deve permanecer vinculada a 127.0.0.1.

Crie um registro DNS A para bolao apontando ao IP público do servidor. Se usar AAAA, confira conectividade IPv6. Copie deploy/nginx.conf para /etc/nginx/sites-available/bolao-esplanada, habilite com link simbólico em sites-enabled, valide sudo nginx -t e recarregue. Em seguida use sudo certbot --nginx -d bolao.alrjunior.com.br. Teste HTTPS antes do login.

Para preservar limitação de login por IP real, identifique o gateway da rede do container: docker inspect $(docker compose ps -q bolao) --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}'. Configure FORWARDED_ALLOW_IPS no .env apenas com o endereço confiável observado e recrie o container. Nunca use '*' indiscriminadamente. Confirme nos logs que o IP real chega corretamente. Nginx sobrescreve X-Forwarded-For. Não exponha a porta do Uvicorn diretamente.

## Pendências antes de convidar participantes
Homologar navegador/Docker, regras de fusões/divisões e nomes equivalentes, bloqueio individual e impossibilidade de contornar por grafias alternativas, finalização e restauração de backup. V1.7 não tem agendamento de bloqueios. Não tratar este pacote como auditoria de segurança concluída.
