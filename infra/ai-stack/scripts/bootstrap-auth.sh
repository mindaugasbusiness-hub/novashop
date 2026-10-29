#!/usr/bin/env bash
# Docker variantas: vieną kartą prisijungiam prie Cline (ClinePass / Cline account)
# ir įrašom konfigūraciją į 'cline_data' volume, kad headless worker'is galėtų dirbti
# be rakto ir be jokio UI.
#
#   bash scripts/bootstrap-auth.sh            # interaktyvus 'cline auth' konteineryje
#   bash scripts/bootstrap-auth.sh from-host  # nukopijuoti tavo ~/.cline
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
MODE="${1:-login}"

cd "$ROOT"
docker compose build cline-worker

if [[ "$MODE" == "from-host" ]]; then
  [[ -d "$HOME/.cline/data/settings" ]] || {
    echo "[x] Nerasta ~/.cline/data/settings – pirmiausia prisijunk: cline auth"; exit 1; }
  echo "[i] Kopijuoju $HOME/.cline -> /data/cline (volume)"
  docker compose run --rm --no-deps \
    -v "$HOME/.cline:/seed:ro" \
    --entrypoint bash \
    cline-worker -lc '
      mkdir -p /data/cline &&
      cp -a /seed/. /data/cline/ &&
      chmod -R u+rwX /data/cline &&
      echo "[i] Nukopijuota. providers.json:" &&
      ls -la /data/cline/data/settings/'
else
  echo "[i] Interaktyvus prisijungimas (pasirink Cline / ClinePass ir modelį)."
  docker compose run --rm -it --no-deps cline-worker cline auth
fi

docker compose up -d cline-worker
sleep 2
echo
echo "[i] Worker'io būsena:"
docker compose exec -T cline-worker node -e \
  "fetch('http://127.0.0.1:7070/healthz').then(r=>r.json()).then(j=>console.log(JSON.stringify(j,null,2)))"
