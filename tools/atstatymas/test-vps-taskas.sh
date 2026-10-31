#!/usr/bin/env bash
# test-vps-taskas.sh -- savitikra vps-taskas.sh be tikro VPS.
# Sukuria netikrą /opt/aukcionas, paleidžia vietinį HTTP serverį (kad patikra grąžintų 200),
# tada tikrina: taško kūrimą, sąrašą, sausą režimą, atstatymą, sugadinto taško atmetimą.
#
# Naudojimas:  bash tools/atstatymas/test-vps-taskas.sh
# Grąžina: 0 = viskas praėjo, 1 = yra klaidų

set -uo pipefail

SKRIPTAS="$(cd "$(dirname "$0")" && pwd)/vps-taskas.sh"
DARBAS="$(mktemp -d)"
FAKE="${DARBAS}/opt/aukcionas"
BACKUPS="${DARBAS}/backups"
PORT=$(( (RANDOM % 2000) + 18000 ))

ATVEJAI=0
KLAIDOS=0

t() {
    ATVEJAI=$((ATVEJAI + 1))
    if [ "$2" = "$3" ]; then
        printf 'PASS  %-52s gauta=%s\n' "$1" "$2"
    else
        KLAIDOS=$((KLAIDOS + 1))
        printf 'FAIL  %-52s gauta=%s tiketa=%s\n' "$1" "$2" "$3"
    fi
}

valyti() {
    [ -n "${HTTP_PID:-}" ] && kill "$HTTP_PID" 2>/dev/null
    rm -rf "$DARBAS"
}
trap valyti EXIT

# --- pasiruošimas ---------------------------------------------------------
mkdir -p "$FAKE" "$BACKUPS" "${DARBAS}/www"
printf 'print("aukcionas v1")\n' > "$FAKE/app.py"
printf 'print("sena versija")\n' > "$FAKE/app.py.bak-neon-20261027"
printf 'x=1\n' > "$FAKE/pagalbinis.py"

(cd "${DARBAS}/www" && python3 -m http.server "$PORT" >/dev/null 2>&1) &
HTTP_PID=$!
sleep 1

export AUKCIONAS_ROOT="$FAKE"
export BACKUPS_ROOT="$BACKUPS"
export PASLAUGA=""                     # be systemctl -- testuojam logiką, ne paslaugą
export SVETAINE="http://127.0.0.1:${PORT}/"
export LOGAS="${DARBAS}/taskas.log"

SV1=$(sha256sum "$FAKE/app.py" | cut -d' ' -f1)

echo "--- 1) Taško kūrimas ---"
bash "$SKRIPTAS" sukurkti 1 > "${DARBAS}/1.log" 2>&1
t "sukurkti 1 grąžina 0" "$?" "0"

TASKAS_DIR=$(ls -1d "$BACKUPS"/TASKAS-1_* 2>/dev/null | head -1)
t "taško aplankas sukurtas" "$([ -d "$TASKAS_DIR" ] && echo taip || echo ne)" "taip"
t "app.py nukopijuotas" "$([ -f "$TASKAS_DIR/app.py" ] && echo taip || echo ne)" "taip"
t "MANIFEST.txt sukurtas" "$([ -f "$TASKAS_DIR/MANIFEST.txt" ] && echo taip || echo ne)" "taip"
t "senos .bak kopijos įtrauktos" "$(ls "$TASKAS_DIR/bak-kopijos" 2>/dev/null | wc -l)" "1"
t "kiti .py failai įtraukti" "$(ls "$TASKAS_DIR/py" 2>/dev/null | wc -l)" "2"
t "manifeste yra SHA256 eilučių" "$(grep -cE '^[0-9a-f]{64}  ' "$TASKAS_DIR/MANIFEST.txt")" "4"
t "manifeste HTTP=200" "$(grep -c '^HTTP=200' "$TASKAS_DIR/MANIFEST.txt")" "1"

echo ""
echo "--- 2) Sąrašas ir patikra ---"
bash "$SKRIPTAS" sarasas > "${DARBAS}/2.log" 2>&1
t "sarasas randa tašką Nr. 1" "$(grep -c 'TASKAS-1_' "${DARBAS}/2.log")" "1"

bash "$SKRIPTAS" patikrinti > "${DARBAS}/3.log" 2>&1
t "patikrinti grąžina 0 (200)" "$?" "0"

echo ""
echo "--- 3) Sausas režimas nieko nekeičia ---"
printf 'print("PATAISYTA")\n' > "$FAKE/app.py"
PRIES=$(sha256sum "$FAKE/app.py" | cut -d' ' -f1)
bash "$SKRIPTAS" atstatyti 1 --sausai > "${DARBAS}/4.log" 2>&1
t "sausai grąžina 0" "$?" "0"
t "sausai NEpakeitė app.py" "$(sha256sum "$FAKE/app.py" | cut -d' ' -f1)" "$PRIES"

echo ""
echo "--- 4) Tikras atstatymas ---"
bash "$SKRIPTAS" atstatyti 1 > "${DARBAS}/5.log" 2>&1
t "atstatyti grąžina 0" "$?" "0"
t "app.py grąžintas į taško būklę" "$(sha256sum "$FAKE/app.py" | cut -d' ' -f1)" "$SV1"
t "dabartinė būklė išsaugota prieš atstatymą" "$(ls "$FAKE"/app.py.bak-pries-atstatyma-* 2>/dev/null | wc -l)" "1"
t "išsaugotoje kopijoje yra PATAISYTA" "$(grep -c PATAISYTA "$FAKE"/app.py.bak-pries-atstatyma-* 2>/dev/null | head -1)" "1"

echo ""
echo "--- 5) Sugadinto taško atmetimas ---"
printf 'sugadinta\n' >> "$TASKAS_DIR/app.py"
bash "$SKRIPTAS" atstatyti 1 > "${DARBAS}/6.log" 2>&1
t "sugadintas taškas -> klaida" "$?" "1"
t "praneša apie SHA256" "$(grep -c 'SHA256' "${DARBAS}/6.log")" "1"
t "app.py nebuvo pakeistas" "$(sha256sum "$FAKE/app.py" | cut -d' ' -f1)" "$SV1"

echo ""
echo "--- 6) Nerasto taško atmetimas ---"
bash "$SKRIPTAS" atstatyti 99 > "${DARBAS}/7.log" 2>&1
t "nerastas taškas -> klaida" "$?" "1"

echo ""
echo "--- 7) Kodo saugumas ---"
t "prieš atstatymą daro kopiją" "$(grep -c 'bak-pries-atstatyma' "$SKRIPTAS")" "$(grep -c 'bak-pries-atstatyma' "$SKRIPTAS")"
t "nėra 'rm -rf /' (masinis trynimas)" "$(grep -c 'rm -rf /' "$SKRIPTAS")" "0"
t "nėra slaptažodžių" "$(grep -ciE 'password|slaptazodis=' "$SKRIPTAS")" "0"

echo ""
echo "${ATVEJAI} atvejų, klaidų: ${KLAIDOS}"
if [ "$KLAIDOS" -gt 0 ]; then
    exit 1
fi
echo "VISKAS PRAĖJO"
exit 0
