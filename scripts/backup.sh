#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $EUID != 0 ]] || { echo "Execute como junior"; exit 1; }
root="$HOME/bolao-esplanada"
base="$HOME/bolao-private-backups"
mkdir -p -m 700 "$base"
[[ ! -L "$base" && $(stat -c %a "$base") == 700 ]] || exit 1
dir=$(mktemp -d "$base/snapshot-XXXXXXXX")
trap 'echo "Backup incompleto: $dir" >&2' ERR
sudo -v
sudo docker inspect bolao-esplanada_bolao_1 --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' | grep -Fx bolao-esplanada_bolao_data
sudo docker exec -i bolao-esplanada_bolao_1 python - >"$dir/bolao.sqlite3" <<'PY'
import sqlite3, tempfile, pathlib, sys, contextlib
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d)/"copy.sqlite3"
    with contextlib.closing(sqlite3.connect("file:/data/bolao.sqlite3?mode=ro",uri=True,timeout=10)) as src, contextlib.closing(sqlite3.connect(p)) as dst:
        src.execute("BEGIN")
        assert src.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
        src.backup(dst,pages=128,sleep=.1)
        assert dst.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
        for t in ("game","users","sessions","audit","attempts"):
            a=src.execute(f"SELECT count(*) FROM {t}").fetchone()
            b=dst.execute(f"SELECT count(*) FROM {t}").fetchone()
            assert a==b,(t,a,b)
            print(t,a[0],file=sys.stderr)
        for col in ("bet","draft"):
            a=src.execute(f"SELECT count({col}) FROM users").fetchone()
            assert a==dst.execute(f"SELECT count({col}) FROM users").fetchone()
            print(col,a[0],file=sys.stderr)
    with p.open("rb") as f:
        import shutil
        shutil.copyfileobj(f,sys.stdout.buffer)
PY
cp "$root/.env" "$dir/production.env"
cp "$root/compose.yaml" "$root/Dockerfile" "$root/requirements.txt" "$dir/"
sudo cat /etc/nginx/sites-available/bolao-esplanada >"$dir/nginx.conf"
sudo docker inspect bolao-esplanada_bolao_1 --format '{{.Image}}' >"$dir/image-id"
git -C "$root" rev-parse HEAD >"$dir/git-head"
(cd "$dir"; sha256sum bolao.sqlite3 production.env compose.yaml Dockerfile requirements.txt nginx.conf image-id git-head > SHA256SUMS; sha256sum -c SHA256SUMS)
touch "$dir/COMPLETE"
echo "BACKUP_OK $dir"
