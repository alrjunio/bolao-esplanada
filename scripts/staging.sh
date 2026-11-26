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
status) compose ps ;;
stop) compose stop ;;
*) echo "Uso: staging.sh up|status|stop"; exit 2 ;;
esac
