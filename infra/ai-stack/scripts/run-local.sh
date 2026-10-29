#!/usr/bin/env bash
# Be Docker: paleidžia worker'į tiesiai ant tavo mašinos ir naudoja TAVO jau
# esamą Cline prisijungimą (~/.cline) – taip veikia ClinePass / nemokami modeliai
# be jokio API rakto.
#
#   bash scripts/run-local.sh
#
# n8n (jei irgi Docker'yje) tada kviečia: http://host.docker.internal:7070/run
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"

command -v node >/dev/null || { echo "[x] Reikia Node.js 20+"; exit 1; }
if ! command -v cline >/dev/null; then
  echo "[i] cline nerastas – instaliuoju: npm i -g cline"
  npm install -g cline
fi

# 1) prisijungimas (ClinePass / Cline account) – daroma vieną kartą
if [[ ! -f "${HOME}/.cline/data/settings/providers.json" ]]; then
  echo "[i] Nėra prisijungimo. Paleidžiu 'cline auth' (vienkartinis žingsnis)."
  cline auth || { echo "[x] Nepavyko prisijungti. Paleisk 'cline auth' rankiniu būdu."; exit 1; }
fi

# 2) smėlio dėžė
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT/work}"
mkdir -p "$WORKSPACE_ROOT"
if [[ ! -d "$WORKSPACE_ROOT/projektas" && -d "$ROOT/sandbox/projektas" ]]; then
  cp -a "$ROOT/sandbox/projektas" "$WORKSPACE_ROOT/projektas"
  echo "[i] Sudėtas demo projektas: $WORKSPACE_ROOT/projektas"
fi

# 3) Cline konfigūracija: pagal nutylėjimą – tavo paties ~/.cline (tai ir yra prenumerata)
export CLINE_CONFIG="${CLINE_CONFIG:-$HOME/.cline}"
export CLINE_DATA_DIR="${CLINE_DATA_DIR:-$HOME/.cline/data}"
export PORT="${PORT:-7070}"

echo
echo "  Worker:      http://127.0.0.1:${PORT}"
echo "  Smėlio dėžė: ${WORKSPACE_ROOT}"
echo "  Cline conf:  ${CLINE_CONFIG}"
echo "  Token:       (iš .env)"
echo

exec node "$ROOT/server.js"
