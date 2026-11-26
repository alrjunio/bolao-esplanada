#!/usr/bin/env bash
# GER-009-B: production execution deliberately disabled until separate authorization.
set -euo pipefail
umask 077
[[ $EUID != 0 ]] || exit 1
cd "$(dirname "$0")/.."
[[ $(git branch --show-current) == release/v3.0-launch ]] || exit 1
[[ "$(pwd -P)" != "$(realpath "$HOME/bolao-esplanada")" ]] || exit 1
scope="${1:-}"
case "$scope" in
 production) echo "PRODUCTION_BLOCKED: CHAT 00 authorization and reviewed gate required" >&2; exit 77 ;;
 staging) ;;
 *) echo "Specify staging; production is blocked" >&2; exit 2 ;;
esac
name=bolao-homologacao_bolao_1
volume=bolao-homologacao_staging_data
network=bolao-homologacao_default
port=8016
base="$HOME/bolao-staging-private/release-operations"
mkdir -p -m 700 "$base"
[[ ! -L "$base" && $(stat -c %a "$base") == 700 ]] || exit 1
exec 9>"$base/lock"
flock -n 9 || { echo "Another release operation is active"; exit 1; }
sudo -v
docker() { sudo docker "$@"; }
guard() {
  local id="$1"
  [[ $(docker inspect --type container --format '{{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}}{{println}}{{end}}' "$id") == "volume:$volume:/data" ]]
  [[ $(docker inspect --format '{{range $n,$v := .NetworkSettings.Networks}}{{$n}}{{println}}{{end}}' "$id") == "$network" ]]
  [[ $(docker inspect --format '{{(index (index .HostConfig.PortBindings "8000/tcp") 0).HostIp}}:{{(index (index .HostConfig.PortBindings "8000/tcp") 0).HostPort}}' "$id") == "127.0.0.1:$port" ]]
}
ready() {
  local i
  for i in {1..30}; do
    if bash scripts/healthcheck.sh staging >/dev/null 2>&1; then
      bash scripts/smoke-test.sh
      return
    fi
    sleep 1
  done
  echo "Readiness timeout" >&2; return 1
}
schema() {
  docker exec "$1" python -c 'import sqlite3,hashlib,json
with sqlite3.connect("file:/data/bolao.sqlite3?mode=ro",uri=True) as c:
    assert c.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
    print(hashlib.sha256(json.dumps(c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()).encode()).hexdigest())'
}
[[ $# == 3 && "$2" == CHAT03_WINDOW_CONFIRMED && "$3" == SCHEMA_COMPATIBILITY_REVIEWED ]] || { echo "Uso: rollback.sh staging CHAT03_WINDOW_CONFIRMED SCHEMA_COMPATIBILITY_REVIEWED"; exit 2; }
op=$(cat "$base/active")
[[ "$op" == "$base"/op-* && -d "$op" ]] || exit 1
old=$(cat "$op/old-id"); new=$(cat "$op/new-id")
[[ "$old" =~ ^[a-f0-9]{64}$ && "$new" =~ ^[a-f0-9]{64}$ && "$old" != "$new" ]]
guard "$new"
# The stopped predecessor may not have a live network endpoint; verify declared mount/port and retained name.
[[ $(docker inspect --format '{{.Name}}' "$old") == "/bolao-stage-previous-${op##*/}" ]]
[[ $(docker inspect --format '{{.State.Status}}' "$old") == exited ]]
[[ $(docker inspect --format '{{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}}{{println}}{{end}}' "$old") == "volume:$volume:/data" ]]
[[ $(docker inspect --format '{{.Name}}' "$new") == "/$name" ]]
[[ $(schema "$new") == "$(cat "$op/schema-before")" ]] || { echo "Schema changed; manual recovery review required; no old snapshot restored"; exit 1; }
docker stop "$new"
docker rename "$new" "bolao-stage-rolledback-${op##*/}"
docker rename "$old" "$name"
docker start "$old"
guard "$old"
ready
bash scripts/healthcheck.sh production
mv "$base/active" "$op/closed"
echo "STAGING_ROLLBACK_OK $op"
