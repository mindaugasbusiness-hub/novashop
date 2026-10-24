#!/bin/bash
# Penktadienio aukcionas - IVR audio promptu generavimas (Vilkas)
# Balsas: lt-LT-LeonasNeural, rate=-5%, pitch=-2Hz
set -u
EDGE=/opt/aukcionas/.venv/bin/edge-tts
OUT=/opt/aukcionas/voice
VOICE=lt-LT-LeonasNeural
RATE=-5%
PITCH=-2Hz
mkdir -p "$OUT"

gen () {
  name="$1"; text="$2"
  "$EDGE" --voice "$VOICE" --rate="$RATE" --pitch="$PITCH" --text "$text" --write-media "$OUT/$name" 2>&1 | tail -2
  sz=$(stat -c %s "$OUT/$name" 2>/dev/null || echo 0)
  if [ "$sz" -lt 5000 ]; then echo "FAIL $name ($sz B)"; else echo "OK $name ($sz B)"; fi
}

gen greet.mp3 "Sveiki! Cia penktadienio aukcionas. Vilkas kalba. Kas nutiko? Jei del prekiu priemimo - spauskite vieneta. Kiti klausimai - spauskite du. Jei norite palikti zinute - spauskite tris."
gen prekes.mp3 "Prekiu priemimas. Priimame telefonus, kompiuterius ir buitine technika. Jei norite perduoti preke aukcionui, palikite zinute - spauskite tris. Jei turite klausimu del jau perduotos prekes - spauskite du."
gen klausimai.mp3 "Klausau. Pasakykite savo klausima po pyptelejimo, ir as atsakysiu."
gen zinute.mp3 "Kalbekite po pyptelejimo. Baige galite tiesiog padeti rageli."
gen aciu.mp3 "Aciu. Zinute irasyta. Vilkas perskambins artimiausiu metu."
gen nesupratau.mp3 "Atsiprasau, nesupratau. Spauskite vieneta - del prekiu, du - kiti klausimai, tris - palikti zinute."
gen iki.mp3 "Iki pasimatymo penktadieni dvidesimta valanda. Viso gero!"
gen perkelti.mp3 "Jungiu jus su vedeju. Palaukite."
echo "=== GALUTINIS SARASAS ==="
ls -la "$OUT"/*.mp3
