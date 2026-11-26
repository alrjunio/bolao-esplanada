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
[[ $# == 3 && "$3" == CHAT03_WINDOW_CONFIRMED ]] || { echo "Uso: deploy.sh staging COMMIT CHAT03_WINDOW_CONFIRMED"; exit 2; }
commit="$2"
[[ "$commit" =~ ^[0-9a-f]{40}$ && $(git rev-parse HEAD) == "$commit" && -z $(git status --porcelain) ]] || { echo "Commit/tree mismatch"; exit 1; }
[[ ! -e "$base/active" ]] || { echo "Existing operation: review before retry"; exit 1; }
old=$(docker inspect --type container --format '{{.Id}}' "$name")
guard "$old"
[[ $(docker inspect --format '{{.State.Running}}' "$old") == true ]]
[[ $(docker inspect --format '{{.HostConfig.Memory}}:{{.HostConfig.NanoCpus}}:{{.HostConfig.PidsLimit}}' "$old") == 536870912:500000000:128 ]]
op=$(mktemp -d "$base/op-XXXXXXXX")
printf '%s\n' "$old" > "$op/old-id"
printf '%s\n' "$commit" > "$op/commit"
# Build first, using only tracked source from the pinned commit.
mkdir "$op/source"
git archive "$commit" | tar -x -C "$op/source"
docker build --label "org.opencontainers.image.revision=$commit" -t "bolao-staging-release:$commit" "$op/source"
image=$(docker image inspect "bolao-staging-release:$commit" --format '{{.Id}}')
printf '%s\n' "$image" > "$op/image"
# Capture runtime environment privately, never print secrets.
docker inspect --format '{{json .Config.Env}}' "$old" | python3 -c 'import json,sys
for item in json.load(sys.stdin):
    assert "\\n" not in item and "\\r" not in item
    print(item)' > "$op/runtime.env"
# Online consistent backup before any stop.
docker exec -i "$old" python - > "$op/before.sqlite3" <<'PY'
import sqlite3,tempfile,pathlib,sys,contextlib
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d)/"backup"
    with contextlib.closing(sqlite3.connect("file:/data/bolao.sqlite3?mode=ro",uri=True)) as s, contextlib.closing(sqlite3.connect(p)) as b:
        s.execute("BEGIN")
        assert s.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
        s.backup(b)
        assert b.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
        for q in ("SELECT count(*),count(bet),count(draft) FROM users","SELECT count(*) FROM audit","SELECT count(*) FROM game"):
            assert s.execute(q).fetchall()==b.execute(q).fetchall()
    sys.stdout.buffer.write(p.read_bytes())
PY
(cd "$op"; sha256sum before.sqlite3 runtime.env > SHA256SUMS; sha256sum -c SHA256SUMS)
schema "$old" > "$op/schema-before"
# Create candidate without starting it or touching the live database.
new=$(docker create --name "bolao-stage-candidate-${op##*/}" --label bolao.scope=staging-release --network "$network" --restart no --memory 512m --cpus .5 --pids-limit 128 -p "127.0.0.1:$port:8000" --env-file "$op/runtime.env" -v "$volume:/data" "$image")
printf '%s\n' "$new" > "$op/new-id"
printf '%s\n' "$op" > "$base/active"
# No automatic restore or automatic rollback after schema-changing startup.
docker stop "$old"
docker rename "$old" "bolao-stage-previous-${op##*/}"
docker rename "$new" "$name"
docker start "$new"
guard "$new"
ready
schema "$new" > "$op/schema-after"
bash scripts/healthcheck.sh production
echo "STAGING_DEPLOY_OK $op"
