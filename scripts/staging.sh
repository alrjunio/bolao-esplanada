#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $EUID != 0 ]] || exit 1
cd "$(dirname "$0")/.."
[[ $(git branch --show-current) == release/v3.0-launch ]] || { echo "Branch incorreta"; exit 1; }
base="$HOME/bolao-staging-private"
mkdir -p -m 700 "$base"
[[ ! -L "$base" && $(stat -c %a "$base") == 700 ]] || exit 1
envfile="$base/staging.env"
if [[ ! -e "$envfile" ]]; then
  (set -o noclobber; printf 'ADMIN_USER=stageadmin\nADMIN_PASSWORD=%s\nINVITE_CODE=%s\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" >"$envfile")
fi
[[ ! -L "$envfile" && $(stat -c %a "$envfile") == 600 ]] || exit 1
compose() { sudo env STAGING_ENV="$envfile" docker-compose -p bolao-homologacao -f infrastructure/docker/compose.staging.yaml "$@"; }
case "${1:-}" in
up)
  if sudo ss -H -lnt 'sport = :8016' | grep -q .; then echo "Porta ocupada; abortando"; exit 1; fi
  compose config --quiet
  compose up -d --build
  ;;
recover)
  # Compose V1 cannot recreate some containers on newer Engine APIs.
  # Only remove a stopped, verified staging container; never its volume.
  [[ $# == 2 ]] || { echo "Uso: staging.sh recover CONTAINER_ID"; exit 2; }
  [[ "$2" =~ ^[a-f0-9]{12,64}$ ]] || exit 2
  sudo -v
  if sudo ss -H -lnt 'sport = :8016' | grep -q .; then echo "Porta ocupada; abortando"; exit 1; fi
  compose config --quiet
  id=$(sudo docker inspect --type container --format '{{.Id}}' "$2")
  project=$(sudo docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$id")
  service=$(sudo docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id")
  state=$(sudo docker inspect --format '{{.State.Status}}' "$id")
  mounts=$(sudo docker inspect --format '{{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}}{{println}}{{end}}' "$id")
  [[ "$project" == bolao-homologacao && "$service" == bolao && "$state" == exited && "$mounts" == volume:bolao-homologacao_staging_data:/data ]] || { echo "Container nao elegivel"; exit 1; }
  sudo docker volume inspect bolao-homologacao_staging_data --format '{{.Name}}' | grep -Fx bolao-homologacao_staging_data
  sudo docker image inspect bolao-homologacao_bolao:latest --format '{{.Id}}'
  # Refuse ambiguous project membership.
  members=$(sudo docker ps -aq --no-trunc --filter label=com.docker.compose.project=bolao-homologacao)
  [[ "$members" == "$id" ]] || { echo "Projeto com outros containers; abortando"; exit 1; }
  sudo docker rm "$id"
  compose up -d --no-build --no-recreate bolao
  ;;
status) compose ps ;;
stop) compose stop ;;
*) echo "Uso: staging.sh up|status|stop|recover CONTAINER_ID"; exit 2 ;;
esac
