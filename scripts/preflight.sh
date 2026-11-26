#!/usr/bin/env bash
set -euo pipefail
docker --version
docker-compose --version
free -h
df -h /
sudo docker inspect bolao-esplanada_bolao_1 --format '{{.State.Status}} {{range .Mounts}}{{.Name}} {{.Destination}}{{end}}'
sudo ss -lnt | grep -E ':8015 |:8016 ' || true
