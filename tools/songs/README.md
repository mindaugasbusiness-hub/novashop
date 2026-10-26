# Dainų įkėlimas į F6 grotuvą (penktadienioaukcionas.lt)

## Kaip veikia grandinė

```
Desktop\vid\Muzika          <- vietiniai .webm failai (šaltinis)
        |
        v
_NAUJOS\                    <- čia parsisiunčia naujos dainos
        |  atsiust-naujas.py  (yt-dlp bestaudio -> .webm i _NAUJOS)
        v
 VPS /opt/aukcionas/desk_songs/NN.webm     <- grotuvas groja pagal numerį
        |  ikelk-i-grotuva.py  (scp + titulai + lokalus katalogas + patikra)
        v
 VPS app.py: DESK_SONG_TITLES { NN: "Atlikėjas — Daina" }
 lokalus _desk_songs.py: CATALOG (n, pavadinimas, needle)
```

## Svarbios taisyklės

- Numeris turi būti **ir** faile `desk_songs/NN.webm`, **ir** `DESK_SONG_TITLES` — kitaip
  grotuvas atsakys 404 arba 400.
- Numeris 05 ir 15 tyčia nenaudojami (M sprendimas); 01 ir 33 failai yra, bet be titulo — taip ir palikta.
- Failai turi būti **.webm** (grotuvas atiduoda `audio/webm`; kitas formatas negros naršyklėje).
- Niekada neperrašyti esamo numerio: prieš keliant patikrinama, kurie numeriai VPS jau užimti.
- Prieš keičiant `app.py` ir `_desk_songs.py` — kopija `.bak-naujos-<data>`; po keitimo — `py_compile`.

## Paleidimas

```powershell
python -X utf8 C:\Users\M\CLINE\tools\_atsiust_naujas.py    # fone, ~7 s vienai dainai
python -X utf8 C:\Users\M\CLINE\tools\_ikelk_naujas.py      # po to, kai atsiuntimas baigtas
```

Žurnalai: `Desktop\vid\Muzika\_atsiuntimo_log.txt`, `_ikelimo_log.txt`.
Įkėlimo būsena: `_ikelimo_bukle.json` (kad pakartotinis paleidimas nekeltų to paties).

## Patikra

```powershell
curl http://127.0.0.1:8766/api/list          # dainų sąrašas F6 panelėje
curl https://penktadienioaukcionas.lt/api/desk_songs
```
