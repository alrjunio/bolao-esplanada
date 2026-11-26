#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
production) url=https://bolao.alrjunior.com.br/ ;;
staging) url=http://127.0.0.1:8016/ ;;
*) exit 2 ;;
esac
code=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "$url")
echo "HTTP=$code"
[[ "$code" == 200 ]]
