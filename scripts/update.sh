#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(pwd -P) != "$(realpath "$HOME/bolao-esplanada")" && $(git branch --show-current) == release/v3.0-launch ]] || exit 1
[[ -z $(git status --porcelain) ]] || exit 1
if [[ $# == 0 ]]; then
  git pull --ff-only origin release/v3.0-launch
elif [[ $# == 1 && "$1" =~ ^[0-9a-f]{40}$ ]]; then
  git fetch origin release/v3.0-launch
  [[ $(git rev-parse FETCH_HEAD) == "$1" ]] || { echo "Remote head differs from authorized commit"; exit 1; }
  git merge --ff-only "$1"
  [[ $(git rev-parse HEAD) == "$1" ]]
else
  exit 2
fi
git rev-parse HEAD
