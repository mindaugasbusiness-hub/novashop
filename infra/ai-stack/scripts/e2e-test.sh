#!/usr/bin/env bash
# TIKRAS end-to-end testas: worker'is -> Cline (tavo modelis) -> failas diske.
# Reikia paleisto worker'io (run-local.sh arba docker compose up).
#
#   bash scripts/e2e-test.sh
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
BASE="${BASE:-http://127.0.0.1:7070}"
WORK="${WORKSPACE_ROOT:-$ROOT/work}"
TESTFILE="labas.txt"
EXPECTED="Labas is Cline grandines"

echo "1) /healthz"
HEALTH="$(curl -sS "$BASE/healthz")"
echo "$HEALTH" | node -e "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>console.log(JSON.stringify(JSON.parse(s),null,2)))"

echo
echo "2) Užduotis: sukurti $TESTFILE (cwd=projektas)"
rm -f "$WORK/projektas/$TESTFILE"
BODY="$(curl -sS -X POST "$BASE/run" \
  -H 'content-type: application/json' \
  -H "x-worker-token: $WORKER_TOKEN" \
  -d "$(node -e 'console.log(JSON.stringify({
        prompt: "Sukurk failą labas.txt su viena eilute: '"$EXPECTED"'. Nieko daugiau nekeisk.",
        cwd: "projektas",
        timeout: 600
      }))')")"

echo "$BODY" | node -e "
let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
  const r = JSON.parse(s);
  console.log('ok        :', r.ok);
  console.log('modelis   :', r.model);
  console.log('iteracijos:', r.iterations);
  console.log('trukmė    :', r.durationMs, 'ms');
  console.log('tekstas   :', (r.text||'').slice(0,300));
  if (r.error) console.log('klaida    :', r.error);
})"

echo
echo "3) Failas diske"
if [[ -f "$WORK/projektas/$TESTFILE" ]]; then
  echo "   rasta: $WORK/projektas/$TESTFILE"
  cat "$WORK/projektas/$TESTFILE"
  echo
  if grep -qi "Labas" "$WORK/projektas/$TESTFILE"; then
    echo
    echo "✅ END-TO-END VEIKIA: n8n kvietimas -> Cline -> failas diske"
    exit 0
  fi
  echo "⚠️ Failas sukurtas, bet turinys netinka"
  exit 1
fi

echo "❌ Failas nesukurtas. Ką daryti:"
echo "   - patikrink 'cline auth' (ar prisijungta prie Cline/ClinePass)"
echo "   - pažiūrėk worker'io log'ą: docker compose logs cline-worker"
echo "   - jei klaida 401/429: modelis netinkamai pasirinktas arba išsemta kvota"
exit 1
