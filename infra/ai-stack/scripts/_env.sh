#!/usr/bin/env bash
# Bendra .env paruošimo logika kitiems skriptams.
# Naudojama:  source "$(dirname "$0")/_env.sh"
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ROOT/.env.example" ]]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
  else
    : > "$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE"
  echo "[i] Sukurtas $ENV_FILE"
fi

# WORKER_TOKEN: sugeneruojam, jei tuščias arba likęs šablonas
_current_token="$(grep -E '^WORKER_TOKEN=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
if [[ -z "${_current_token}" || "${_current_token}" == "pakeisk_mane" ]]; then
  _new_token="$(openssl rand -hex 32)"
  if grep -qE '^WORKER_TOKEN=' "$ENV_FILE"; then
    # portable in-place replace be sed -i skirtumų
    awk -v t="WORKER_TOKEN=${_new_token}" '/^WORKER_TOKEN=/{print t; next} {print}' \
      "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
  else
    printf 'WORKER_TOKEN=%s\n' "$_new_token" >> "$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE"
  echo "[i] Sugeneruotas naujas WORKER_TOKEN faile $ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${WORKER_TOKEN:?WORKER_TOKEN nepavyko nustatyti}"
