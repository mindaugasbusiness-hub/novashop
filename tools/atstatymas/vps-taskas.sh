#!/usr/bin/env bash
# vps-taskas.sh -- VPS atstatymo taškas: penktadienioaukcionas.lt (aukcionas)
#
# Ką fiksuoja: /opt/aukcionas/app.py, jo .bak kopijas, systemd unit'ą ir patikros rezultatą.
# Ką atstato:  app.py iš pasirinkto taško + `systemctl restart aukcionas` + HTTP patikra.
# 1 TAISYKLĖ: prieš atstatant VISADA padaroma dabartinės būklės kopija (.bak-pries-atstatyma).
#
# Naudojimas:
#   ./vps-taskas.sh sukurkti             # sukurti NAUJĄ tašką (numeris automatinis)
#   ./vps-taskas.sh sukurkti 1           # sukurti/perrašyti tašką Nr. 1
#   ./vps-taskas.sh sarasas              # išvardinti taškus
#   ./vps-taskas.sh patikrinti           # ar svetainė atsako 200
#   ./vps-taskas.sh atstatyti 1          # ATSTATYTI į tašką Nr. 1
#   ./vps-taskas.sh atstatyti 1 --sausai # parodyti, ką darytų, bet nekeisti
#
# Testavimas be VPS:  bash test-vps-taskas.sh

set -uo pipefail

AUKCIONAS_ROOT="${AUKCIONAS_ROOT:-/opt/aukcionas}"
BACKUPS_ROOT="${BACKUPS_ROOT:-/root/BACKUPS_VPS/ATSTATYMO_TASKAI}"
PASLAUGA="${PASLAUGA:-aukcionas}"
SVETAINE="${SVETAINE:-https://penktadienioaukcionas.lt}"
UNIT_FAILAS="${UNIT_FAILAS:-/etc/systemd/system/aukcionas.service}"
LOGAS="${LOGAS:-${BACKUPS_ROOT}/vps-taskas.log}"

log() {
    mkdir -p "$(dirname "$LOGAS")" 2>/dev/null || true
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOGAS"
}

turi() { command -v "$1" >/dev/null 2>&1; }

# --- patikra: ar svetainė atsako 200 -------------------------------------
patikrinti_svetaine() {
    if ! turi curl; then
        echo "NERA curl"
        return 2
    fi
    kodas=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$SVETAINE" 2>/dev/null)
    echo "$kodas"
    [ "$kodas" = "200" ] && return 0 || return 1
}

# --- taškų sąrašas --------------------------------------------------------
cmd_sarasas() {
    if [ ! -d "$BACKUPS_ROOT" ]; then
        echo "Taškų dar nėra ($BACKUPS_ROOT)"
        return 0
    fi
    echo "Atstatymo taškai ($BACKUPS_ROOT):"
    for d in "$BACKUPS_ROOT"/TASKAS-*; do
        [ -d "$d" ] || continue
        dydis=$(du -sh "$d" 2>/dev/null | cut -f1)
        data=$(stat -c '%y' "$d" 2>/dev/null | cut -d. -f1)
        printf '  %-28s %-8s %s\n' "$(basename "$d")" "$dydis" "$data"
    done
}

# --- naujas taškas --------------------------------------------------------
cmd_sukurkti() {
    local numeris="${1:-}"
    if [ -z "$numeris" ]; then
        numeris=$(ls -1d "$BACKUPS_ROOT"/TASKAS-* 2>/dev/null | wc -l)
        numeris=$((numeris + 1))
    fi
    local tikslas="${BACKUPS_ROOT}/TASKAS-${numeris}_$(date '+%Y-%m-%d_%H%M')"

    if [ ! -f "${AUKCIONAS_ROOT}/app.py" ]; then
        echo "KLAIDA: nera ${AUKCIONAS_ROOT}/app.py"
        return 1
    fi

    mkdir -p "$tikslas" || return 1
    cp -a "${AUKCIONAS_ROOT}/app.py" "$tikslas/app.py"

    # visos esamos .bak kopijos (istorija, kad būtų kuo grąžinti)
    if ls "${AUKCIONAS_ROOT}"/app.py.bak-* >/dev/null 2>&1; then
        mkdir -p "$tikslas/bak-kopijos"
        cp -a "${AUKCIONAS_ROOT}"/app.py.bak-* "$tikslas/bak-kopijos/" 2>/dev/null || true
    fi

    # kiti .py failai (jei yra)
    if ls "${AUKCIONAS_ROOT}"/*.py >/dev/null 2>&1; then
        mkdir -p "$tikslas/py"
        cp -a "${AUKCIONAS_ROOT}"/*.py "$tikslas/py/" 2>/dev/null || true
    fi

    [ -f "$UNIT_FAILAS" ] && cp -a "$UNIT_FAILAS" "$tikslas/aukcionas.service" 2>/dev/null || true

    # manifestas su SHA256 -- atstatant bus galima patikrinti, kad taškas nesugadintas
    {
        echo "TASKAS=$numeris"
        echo "DATA=$(date '+%Y-%m-%d %H:%M:%S')"
        echo "AUKCIONAS_ROOT=$AUKCIONAS_ROOT"
        echo "PASLAUGA=$PASLAUGA"
        echo "PYTHON=$(python3 -V 2>&1)"
        echo "SVETAINE=$SVETAINE"
        echo "HTTP=$(patikrinti_svetaine 2>/dev/null || echo 'nera')"
        echo "FAILAI:"
        (cd "$tikslas" && find . -type f ! -name MANIFEST.txt -exec sha256sum {} \; | sort -k2)
    } > "$tikslas/MANIFEST.txt"

    log "SUKURTAS taskas Nr. $numeris -> $tikslas"
    echo "Sukurta: $tikslas"
    echo "Patikra: ./vps-taskas.sh sarasas"
}

# --- atstatymas -----------------------------------------------------------
cmd_atstatyti() {
    local numeris="$1"
    local sausai="${2:-}"
    local saltinis
    saltinis=$(ls -1d "$BACKUPS_ROOT"/TASKAS-${numeris}_* 2>/dev/null | head -1)

    if [ -z "$saltinis" ] || [ ! -d "$saltinis" ]; then
        echo "KLAIDA: nera tasko Nr. $numeris ($BACKUPS_ROOT/TASKAS-${numeris}_*)"
        return 1
    fi

    # 1) Taško vientisumo patikra
    if [ -f "$saltinis/MANIFEST.txt" ]; then
        if (cd "$saltinis" && grep -E '^[0-9a-f]{64}  ' MANIFEST.txt > /tmp/.vps-taskas.sha \
             && sha256sum -c /tmp/.vps-taskas.sha --quiet); then
            echo "Tasko SHA256 patikra: OK"
        else
            echo "KLAIDA: tasko Nr. $numeris failai sugadinti (SHA256 nesutampa). Nestatau."
            rm -f /tmp/.vps-taskas.sha
            return 1
        fi
        rm -f /tmp/.vps-taskas.sha
    fi

    if [ "$sausai" = "--sausai" ]; then
        echo "SAUSAI: buciau nukopes $saltinis/app.py -> ${AUKCIONAS_ROOT}/app.py"
        echo "SAUSAI: buciau perkraupes paslauga $PASLAUGA"
        return 0
    fi

    # 2) Dabartines bukles kopija (1 taisykle: nieko netrinti)
    if [ -f "${AUKCIONAS_ROOT}/app.py" ]; then
        local kopija="${AUKCIONAS_ROOT}/app.py.bak-pries-atstatyma-$(date '+%Y%m%d-%H%M%S')"
        cp -a "${AUKCIONAS_ROOT}/app.py" "$kopija" || return 1
        echo "Dabartine bukle issaugota: $kopija"
    fi

    # 3) Atstatymas
    cp -a "$saltinis/app.py" "${AUKCIONAS_ROOT}/app.py" || return 1
    echo "Atstatyta: $saltinis/app.py -> ${AUKCIONAS_ROOT}/app.py"

    # 4) Paslaugos perkrovimas
    if turi systemctl && [ -n "$PASLAUGA" ]; then
        systemctl restart "$PASLAUGA" 2>/dev/null \
            || echo "ISPĖJIMAS: systemctl restart $PASLAUGA nepavyko (ar yra teisės?)"
        sleep 3
        systemctl is-active "$PASLAUGA" 2>/dev/null || true
    else
        echo "systemctl nerastas arba PASLAUGA tuščia -- perkrovimas praleistas"
    fi

    # 5) Patikra
    local kodas
    kodas=$(patikrinti_svetaine)
    if [ "$kodas" = "200" ]; then
        log "ATSTATYTA i taska Nr. $numeris; svetaine 200 OK"
        echo "PATIKRA: svetaine atsako 200 -- atstatymas pavyko"
        return 0
    fi
    log "ATSTATYTA i taska Nr. $numeris, BET svetaine atsako $kodas"
    echo "ISPĖJIMAS: svetaine atsako $kodas (tikėtasi 200). Žiūrėk: journalctl -u $PASLAUGA -n 50"
    return 1
}

case "${1:-}" in
    sukurkti)   shift; cmd_sukurkti "${1:-}" ;;
    sarasas)    cmd_sarasas ;;
    patikrinti) kodas=$(patikrinti_svetaine); echo "svetaine: $kodas"; [ "$kodas" = "200" ] ;;
    atstatyti)
        shift
        [ -n "${1:-}" ] || { echo "Reikia numerio: ./vps-taskas.sh atstatyti 1"; exit 2; }
        cmd_atstatyti "$1" "${2:-}"
        ;;
    *)
        sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
esac

