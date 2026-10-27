#!/usr/bin/env bash
# start.sh — vienas paleidimas Cline pusėje: relay + tunelis + savitikra.
#
# Ką padaro:
#   1. pasirūpina cloudflared (atsisiunčia, jei nėra),
#   2. paleidžia relay.py (portas 8798) ir tunelį,
#   3. sulaukia viešo adreso,
#   4. patikrina, ar adresas tikrai atsako (/health per viešą HTTPS),
#   5. įrašo adresą į /tmp/adresas.txt ir /tmp/relay.base,
#   6. atspausdina eilutę, kurią M nukopijuoja (Ctrl+C).
#
# Naudojimas:
#   bash tools/relay/start.sh              # įprastai
#   bash tools/relay/start.sh --skelbti    # papildomai paskelbti adresų lentoje (žr. lenta.py saugumą)

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8798}"
CF="${CF:-/tmp/cloudflared}"
LOGS=/tmp/relay-logs
SKELBTI=0
for a in "$@"; do [ "$a" = "--skelbti" ] && SKELBTI=1; done

mkdir -p "$LOGS"

echo "1) cloudflared"
if [ ! -x "$CF" ]; then
  echo "   siunčiuosi cloudflared (~40 MB)..."
  curl -sL -o "$CF" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 || true
  chmod +x "$CF" 2>/dev/null || true
fi
if [ ! -x "$CF" ]; then echo "   NEPAVYKO: nėra cloudflared ($CF)"; exit 1; fi
echo "   yra: $CF"

echo "2) relay + tunelis"
pkill -f 'relay\.py' 2>/dev/null || true
pkill -f 'cloudflared tunnel' 2>/dev/null || true
sleep 1
( nohup python3 "$HERE/relay.py" > "$LOGS/relay.log" 2>&1 & ) 
( nohup "$CF" tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate > "$LOGS/cf.log" 2>&1 & )

echo "3) laukiu adreso"
U=""
for i in $(seq 1 40); do
  U=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGS/cf.log" 2>/dev/null | head -1)
  [ -n "$U" ] && break
  sleep 2
done
if [ -z "$U" ]; then
  echo "   NEPAVYKO: adreso nėra. Žr. $LOGS/cf.log"
  tail -5 "$LOGS/cf.log" 2>/dev/null
  exit 1
fi
echo "   adresas: $U"

echo "4) tikrinu adresą per viešą HTTPS (gali užtrukti iki 3 min: DNS propagacija)"
OK=0
for i in $(seq 1 60); do
  C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$U/health" 2>/dev/null || echo 000)
  if [ "$C" = "200" ]; then OK=1; break; fi
  if [ $((i % 10)) -eq 0 ]; then
    if getent hosts "${U#https://}" >/dev/null 2>&1; then
      echo "   ... dar ne (DNS jau veikia, laukiu atsakymo) ${i}/60"
    else
      echo "   ... dar ne (DNS dar nepropagavo) ${i}/60"
    fi
  fi
  sleep 3
done
if [ "$OK" != "1" ]; then
  echo "   NEPAVYKO: $U/health neatsako 200 per 3 min."
  echo "   Ką tikrinti: tail -20 $LOGS/cf.log ; tail -20 $LOGS/relay.log"
  exit 1
fi
echo "   atsako 200"

echo "$U" > /tmp/adresas.txt
echo "$U" > /tmp/relay.base
echo "   įrašyta: /tmp/adresas.txt, /tmp/relay.base"

if [ "$SKELBTI" = "1" ]; then
  echo "5) skelbiu adresų lentoje"
  python3 "$HERE/lenta.py" skelbti || echo "   (lenta nepaskelbta — žr. pranešimą aukščiau)"
else
  echo "5) lentos neskelbiu (jei reikia: start.sh --skelbti)"
fi

echo ""
echo "=================================================================="
echo " PARUOŠTA. Šią eilutę nukopijuok (Ctrl+C), tada darbalaukyje"
echo " dukart spausk \"CLINE RYSYS\":"
echo ""
echo "   iex (irm $U/agent.ps1)"
echo ""
echo " Savitikra: python3 $HERE/test-relay.py"
echo " Būsena:    python3 $HERE/pc.py status"
echo "=================================================================="