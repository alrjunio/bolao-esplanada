#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/healthcheck.sh staging
code=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8016/api/me)
[[ "$code" == 401 ]]
echo SMOKE_OK
