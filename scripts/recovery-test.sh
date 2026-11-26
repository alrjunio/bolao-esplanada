#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $EUID != 0 ]] || exit 1
cd "$(dirname "$0")/.."
[[ $(git branch --show-current) == release/v3.0-launch ]] || exit 1
sudo -v
stage=bolao-homologacao_bolao_1
name=bolao-recovery-test
vol=bolao-recovery-test-data
net=bolao-recovery-test-net
expected=f4a07eebb5e94f65aecf7fb2a37ffbab1ce32f67c961df436bc63f19b1e7a3eb
image=sha256:9b13a622b0cc8450889fbead8405d86d6f96df959de7b2f9ab14760c888efea9
case "${1:-}" in
run)
  [[ $(sudo docker inspect "$stage" --format '{{.Image}}') == "$image" ]]
  [[ $(sudo docker inspect "$stage" --format '{{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}}{{println}}{{end}}') == volume:bolao-homologacao_staging_data:/data ]]
  [[ $(sudo docker inspect "$stage" --format '{{.State.Running}}') == true ]]
  [[ -z $(sudo ss -H -lnt 'sport = :8017') ]]
  for kind in container volume network; do
    resource=$name
    case "$kind" in volume) resource=$vol;; network) resource=$net;; esac
    if sudo docker "$kind" inspect "$resource" >/dev/null 2>&1; then
      echo "Recurso existente: $resource; abortando sem remover nada" >&2
      exit 1
    fi
  done
  base=$(mktemp -d "$HOME/bolao-staging-private/recovery-XXXXXXXX")
  sudo docker exec "$stage" cat /data/recovery-tests/inf003-synthetic.sqlite3 > "$base/source.sqlite3"
  printf '%s  %s\n' "$expected" "$base/source.sqlite3" | sha256sum -c -
  printf 'ADMIN_USER=recoveryadmin\nADMIN_PASSWORD=%s\nINVITE_CODE=%s\n' "$(openssl rand -hex 32)" "$(openssl rand -hex 32)" > "$base/recovery.env"
  sudo docker volume create --label bolao.scope=recovery-test "$vol"
  sudo docker network create --label bolao.scope=recovery-test "$net"
  sudo docker run --rm -i --network none --memory 256m --cpus .25 --pids-limit 64 -v "$vol:/data" --entrypoint python "$image" -c 'import sys,sqlite3,os,contextlib,pathlib
os.umask(0o077)
p=pathlib.Path("/data/source.sqlite3")
assert not p.exists()
p.write_bytes(sys.stdin.buffer.read())
with contextlib.closing(sqlite3.connect(p.as_uri()+"?mode=ro",uri=True)) as src, contextlib.closing(sqlite3.connect("/data/bolao.sqlite3")) as dst:
    assert src.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
    assert src.execute("SELECT count(*),count(bet),count(draft) FROM users").fetchone()==(1,1,1)
    src.backup(dst)
    assert dst.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
    assert dst.execute("SELECT count(*),count(bet),count(draft) FROM users").fetchone()==(1,1,1)
    # Do not carry active sessions into an independent test service.
    dst.execute("DELETE FROM sessions")
    dst.execute("DELETE FROM attempts")
    dst.commit()
print("SYNTHETIC_RESTORE_OK")' < "$base/source.sqlite3"
  sudo docker run -d --name "$name" --label bolao.scope=recovery-test --network "$net" --restart no --memory 256m --cpus .25 --pids-limit 64 -p 127.0.0.1:8017:8000 --env-file "$base/recovery.env" -e DB_PATH=/data/bolao.sqlite3 -e COOKIE_SECURE=0 -e FORWARDED_ALLOW_IPS=127.0.0.1 -v "$vol:/data" "$image"
  for i in {1..20}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8017/ -o /dev/null; then break; fi
    sleep 1
  done
  curl -fsS --max-time 5 http://127.0.0.1:8017/ -o /dev/null
  sudo docker exec -i "$name" python - <<'PY'
import json, urllib.request, http.cookiejar, sqlite3
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(path,data=None):
    req=urllib.request.Request("http://127.0.0.1:8000"+path,data=json.dumps(data).encode() if data is not None else None,headers={"Content-Type":"application/json"})
    with client.open(req,timeout=10) as r:
        return json.load(r)
call("/api/login",{"nick":"INF003_TESTE_PERSISTENCIA","password":"TesteSintetico-INF003-2026"})
assert call("/api/me")["role"]=="participant"
own=call("/api/own")
assert own["revision"]==1
expected={"n":"Ministerio Ficticio INF003","a":"Criar","origin":"","person":"Titular Sintetico","party":"Sem filiação partidária","status":"Novo titular"}
for key in ("bet","draft"):
    value=own["state"][key]
    assert value["total"]==1 and value["rows"]==[expected] and value["extras"]=={}
with sqlite3.connect("file:/data/bolao.sqlite3?mode=ro",uri=True) as db:
    assert db.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
print("RECOVERY_LOGIN_OK")
print("RECOVERY_BET_DRAFT_OK")
print("RECOVERY_INTEGRITY_OK")
PY
  sudo docker stats --no-stream "$name" "$stage" bolao-esplanada_bolao_1
  bash scripts/healthcheck.sh staging
  bash scripts/healthcheck.sh production
  sudo docker inspect bolao-esplanada_bolao_1 --format 'ID={{.Id}} StartedAt={{.State.StartedAt}} RestartCount={{.RestartCount}}'
  echo RECOVERY_TEST_OK
  ;;
stop)
  [[ $(sudo docker inspect "$name" --format '{{index .Config.Labels "bolao.scope"}}') == recovery-test ]]
  [[ $(sudo docker inspect "$name" --format '{{range .Mounts}}{{.Name}}:{{.Destination}}{{println}}{{end}}') == "$vol:/data" ]]
  sudo docker stop "$name"
  ;;
*) echo "Uso: bash scripts/recovery-test.sh run|stop"; exit 2;;
esac
