#!/usr/bin/env bash
# Smoke testas be tikro Cline/rakto: naudoja stub'ą vietoj `cline` binaro.
# Paleisk: bash test/smoke-test.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
TMP="$(mktemp -d)"
PORT=7099
TOKEN="test-token"
BASE="http://127.0.0.1:$PORT"

cleanup() {
  [[ -n "${SERVER_PID:-}" ]] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT

# --- stub `cline` ---
cat > "$TMP/cline" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_ARGS_FILE"
prompt="${!#}"
echo '{"ts":"2026-10-29T10:00:00.000Z","type":"agent_event","event":{"type":"content_start","contentType":"text"}}'
echo '{"ts":"2026-10-29T10:00:00.100Z","type":"agent_event","event":{"type":"done","reason":"completed","text":"ok","iterations":2}}'
case "$prompt" in
  *FAIL*)
    echo '{"ts":"2026-10-29T10:00:00.200Z","type":"agent_event","event":{"type":"error","message":"429 rate limit"}}' >&2
    exit 1 ;;
  *ABORTED*)
    echo '{"ts":"2026-10-29T10:00:00.300Z","type":"run_result","finishReason":"aborted","iterations":3,"durationMs":1200,"model":"stub/model","usage":{"inputTokens":10,"outputTokens":5},"text":"nepabaigta"}'
    exit 0 ;;
  *SLOW*)
    sleep 10 ;;
esac
echo '{"ts":"2026-10-29T10:00:00.400Z","type":"run_result","finishReason":"completed","iterations":2,"durationMs":1234,"model":"stub/model","usage":{"inputTokens":100,"outputTokens":42},"text":"Sutvarkyta: 3 failai."}'
STUB
chmod +x "$TMP/cline"

export CLINE_BIN="$TMP/cline"
export CLINE_CONFIG="$TMP/cline-config"
export CLINE_DATA_DIR="$TMP/cline-data"
export WORKSPACE_ROOT="$TMP/work"
export PORT WORKER_TOKEN="$TOKEN"
export STUB_ARGS_FILE="$TMP/args.txt"
export CLINE_PROVIDER="openrouter" CLINE_MODEL="stub/model"
export TASK_TIMEOUT_SECONDS=60

node "$ROOT/server.js" > "$TMP/server.log" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 50); do
  curl -sf "$BASE/healthz" > /dev/null 2>&1 && break
  sleep 0.2
done

pass=0; fail=0
check() { # name expected actual
  if [[ "$2" == "$3" ]]; then echo "  ok   $1"; pass=$((pass+1));
  else echo "  FAIL $1 (laukta: $2, gauta: $3)"; fail=$((fail+1)); fi
}

echo "1) healthz"
check "healthz 200" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/healthz")"

echo "2) be tokeno"
check "401" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/run" \
  -H 'content-type: application/json' -d '{"prompt":"x"}')"

echo "3) tuščias prompt"
check "400" 400 "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/run" \
  -H 'content-type: application/json' -H "x-worker-token: $TOKEN" -d '{"prompt":"  "}')"

echo "4) cwd escape"
check "400 (path traversal)" 400 "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/run" \
  -H 'content-type: application/json' -H "x-worker-token: $TOKEN" -d '{"prompt":"x","cwd":"../../etc"}')"

echo "5) sėkminga užduotis"
BODY="$(curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"sutvarkyk testus","cwd":"projektas"}')"
check "ok=true" "true" "$(node -e 'console.log(String(JSON.parse(process.argv[1]).ok))' "$BODY")"
check "text" "Sutvarkyta: 3 failai." "$(node -e 'console.log(JSON.parse(process.argv[1]).text)' "$BODY")"
check "model" "stub/model" "$(node -e 'console.log(JSON.parse(process.argv[1]).model)' "$BODY")"
check "cwd sukurtas" "yes" "$([[ -d "$TMP/work/projektas" ]] && echo yes || echo no)"
check "prompt perduotas" "sutvarkyk testus" "$(tail -1 "$TMP/args.txt")"
check "--json perduotas" "yes" "$(grep -qx -- '--json' "$TMP/args.txt" && echo yes || echo no)"
check "--auto-approve true" "yes" "$(grep -A1 -x -- '--auto-approve' "$TMP/args.txt" | grep -qx 'true' && echo yes || echo no)"

echo "6) agento klaida (429)"
BODY="$(curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"FAIL dabar"}')"
check "ok=false" "false" "$(node -e 'console.log(String(JSON.parse(process.argv[1]).ok))' "$BODY")"
check "klaidos tekstas" "429 rate limit" "$(node -e 'console.log(JSON.parse(process.argv[1]).error)' "$BODY")"

echo "7) nepabaigta užduotis"
BODY="$(curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"ABORTED prašau"}')"
check "ok=false (aborted)" "false" "$(node -e 'console.log(String(JSON.parse(process.argv[1]).ok))' "$BODY")"
check "finishReason" "aborted" "$(node -e 'console.log(JSON.parse(process.argv[1]).finishReason)' "$BODY")"

echo "8) timeout"
BODY="$(curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"SLOW","timeout":1}')"
check "ok=false (timeout)" "false" "$(node -e 'console.log(String(JSON.parse(process.argv[1]).ok))' "$BODY")"

echo "9) dvi užduotys vienu metu -> vykdomos po vieną"
START=$(date +%s)
curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"SLOW vienas","timeout":1}' > /dev/null &
CURL_ONE=$!
curl -s -X POST "$BASE/run" -H 'content-type: application/json' -H "x-worker-token: $TOKEN" \
  -d '{"prompt":"SLOW du","timeout":1}' > /dev/null &
CURL_TWO=$!
wait "$CURL_ONE" "$CURL_TWO"
ELAPSED=$(( $(date +%s) - START ))
check "serializuota (>=$((2*1))s, gauta ${ELAPSED}s)" "yes" "$([[ $ELAPSED -ge 2 ]] && echo yes || echo no)"

echo
echo "Rezultatas: $pass ok, $fail fail"
[[ $fail -eq 0 ]]

