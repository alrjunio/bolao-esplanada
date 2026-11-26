#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $# == 1 && $EUID != 0 ]] || { echo "Uso: bash scripts/restore.sh DIRETORIO_BACKUP"; exit 1; }
src=$(realpath "$1")
[[ "$src" == "$HOME/bolao-private-backups/"* && -f "$src/COMPLETE" ]] || exit 1
(cd "$src"; sha256sum -c SHA256SUMS)
out=$(mktemp -d "$HOME/bolao-private-backups/restore-test-XXXXXXXX")
python3 - "$src/bolao.sqlite3" "$out/restored.sqlite3" <<'PY'
import sqlite3,sys,pathlib,contextlib
with contextlib.closing(sqlite3.connect(pathlib.Path(sys.argv[1]).as_uri()+"?mode=ro",uri=True)) as src, contextlib.closing(sqlite3.connect(sys.argv[2])) as dst:
    assert src.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
    src.backup(dst)
    assert dst.execute("PRAGMA integrity_check").fetchall()==[("ok",)]
    for t in ("game","users","sessions","audit","attempts"):
        a=src.execute(f"SELECT count(*) FROM {t}").fetchone()
        assert a==dst.execute(f"SELECT count(*) FROM {t}").fetchone()
        print(t,a[0])
    for col in ("bet","draft"):
        a=src.execute(f"SELECT count({col}) FROM users").fetchone()
        assert a==dst.execute(f"SELECT count({col}) FROM users").fetchone()
        print(col,a[0])
PY
echo "RESTORE_TEST_OK $out (privado; nunca montar em staging)"
