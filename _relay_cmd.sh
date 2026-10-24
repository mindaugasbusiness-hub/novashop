#!/bin/bash
# Siuncia PowerShell komanda M kompiuteriui per relay ir laukia rezultato.
# Naudojimas: ./_relay_cmd.sh 'Get-Date'   arba   ./_relay_cmd.sh -f komanda.ps1
TOK=$(cat /tmp/relay.token)
BASE=http://127.0.0.1:8798
if [ "$1" = "-f" ]; then CMD=$(cat "$2"); else CMD="$1"; fi
ID=$(curl -s -m 20 -H "X-Key: $TOK" -X POST --data-binary "$CMD" "$BASE/cmd" \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
for i in $(seq 1 90); do
  OUT=$(curl -s -m 20 -H "X-Key: $TOK" "$BASE/out?id=$ID")
  if [ "$OUT" != "pending" ] && [ -n "$OUT" ]; then
    echo "$OUT" | base64 -d 2>/dev/null || echo "$OUT"
    exit 0
  fi
  sleep 2
done
echo "TIMEOUT (id=$ID)"
