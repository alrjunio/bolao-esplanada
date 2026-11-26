#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(pwd -P) != "$(realpath "$HOME/bolao-esplanada")" && $(git branch --show-current) == release/v3.0-launch ]] || exit 1
[[ -z $(git status --porcelain) ]] || exit 1
git pull --ff-only origin release/v3.0-launch
