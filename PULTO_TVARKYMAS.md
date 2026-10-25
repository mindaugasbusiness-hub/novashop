# PULTO TVARKYMAS — ką tiksliai sutvarkyti `http://127.0.0.1:8790/`

Šaltinis: 5 vartotojo ekrano nuotraukos (2026-10-25 02:54–02:56).
`pultas.py` repo istorijoje **nėra**, o sandbox'as `127.0.0.1:8790` nepasiekia
(`curl` → `000`), todėl čia — tikslus sąrašas, ką keisti.
Paruoštos funkcijos: `tools/pultas-taisymai.py` (`--self-test`, `--css`, `--pataisymai`).

---

## 1. Būsena rodoma 4 skirtingais žodžiais (didžiausia netvarka)

| Kur | Dabar | Turi būti |
| --- | --- | --- |
| A) antraštė | `Servisai rodomas 5/6` | `Servisai veikia: 5/6` |
| A) suvestinė | `RODOMAS: 5  NE: 1  (iš 6 viso)` | `VEIKIA: 5 · NEVEIKIA: 1 · iš viso: 6` |
| A) ženkliukai | žalias `RODOMAS`, raudonas `NE` | `VEIKIA` / `NEVEIKIA` |
| C) VPS | `active`, `is-active` | `AKTYVUS` |
| D) kopijos | `RODOMAS` (reikšmė neaiški) | `ŠVIEŽIAS` / `PASENĘS` |

**Kodėl:** „RODOMAS“ nėra būsena — jis nieko nesako. Tas pats faktas (ar veikia) rodomas
trimis skirtingais žodžiais, ir net lietuviškai bei angliškai tame pačiame ekrane.

## 2. Trūksta lietuviškų diakritikų (10 vietų)

`is` → `iš` · `uzimta` → `užimta` · `failu` → `failų` · `aplanku` → `aplankų` ·
`dainu` → `dainų` · `ivykiu` → `įvykių` · `botu` → `botų` ·
`07_ZINIOS.md` → `07_ŽINIOS.md` · `PRANESIMU_LOG.txt` → `PRANEŠIMŲ_LOG.txt` ·
`BUDEJIMAS_LOG.txt` → `BUDĖJIMO_LOG.txt`

## 3. Python `True` išlindo į ekraną

`E) SESIJOS_ATASKAITA.txt`:

```
07_ZINIOS.md = True      ->  07_ŽINIOS.md: TAIP
09_PAKEITIMAI.md = True  ->  09_PAKEITIMAI.md: TAIP
```

**Kodėl:** tai `print(f"{failas} = {rezultatas}")` su `bool`. Reikia `taip_ne(rezultatas)`.
Tas pats pultas B) sekcijoje jau rašo `mokosi: TAIP` — vadinasi, vietomis tvarkinga, vietomis ne.

## 4. Skaičiai lietuvišku formatu

| Dabar | Turi būti |
| --- | --- |
| `1.76 MB` | `1,76 MB` |
| `0.01 MB` | `10 KB` |
| `18.9 s` | `18,9 s` |
| `7.8G` | `7,8 GB` |
| `43% uzimta` | `užimta 44 %` |

**Pastaba:** 7,8 GB laisva iš 14 GB = užimta **44 %**, o ne 43 % → pultas dar ir
skaičiuoja neteisingai. Be to tarpas prieš `%` rašomas, po — ne.

## 5. Trys skirtingi laikai be jokios nuorodos

- antraštė: `2026-10-25 02:54:15`
- B): `paskutinis: 08:04:38`
- C) VPS žurnalas: `09:40:01`, `09:45:01`, `09:50:01`
- E) `BUDEJIMAS_LOG`: `2026-10-24 23:50:07`

Reikia kiekvieną laiką pažymėti juosta: `(vietinis)` / `(VPS)`. Dabar atrodo, kad kažkas
neteisingai rodo laiką, nors iš tikrųjų tai skirtingos juostos.

## 6. Žalias „RODOMAS“ prie pasenusių kopijų (rimčiausia funkcinė klaida)

`D) KOPIJOS` rodo:

- VPS kopijos: `2026-10-24_1256` → **~13 h senumo**
- Vietinės kopijos: `2026-10-24_0631_SecurityWatch` → **~20 h senumo**

O `swiss.ps1` logika: jei kopijos senesnės nei **20 h** — daryti iš naujo. Pultas vis tiek
rodo žalią `RODOMAS`. Turi būti `PASENĘS (24,5 h)` geltonai/raudonai, kad matytųsi problema.

Be to eilutė yra nesuprantama dėl suklijuotų laukų ir dublikatų:

```
2026-10-24_1256 | failu: 17 | 1.76 MB | 2026-10-24 12:56 | aplanku viso: 6
```

Turi būti atskiri, aiškūs laukai (data · failų · dydis · amžius), be dvigubo laiko.

## 7. Išdėstymas: didelės tuščios skylės

`D)`, `E)`, `F)` sekcijos palieka pustuštes kolonas — dešinėje turinys baigiasi, kairėje
lieka tuščia iki pusės ekrano. Priežastis: CSS grid be `align-items: start` → kortelės
tempiamos iki aukščiausios eilutės kortelės.

Pataisymas paruoštas: `python tools/pultas-taisymai.py --css`

## 8. Kitos smulkmenos

| Kur | Dabar | Turi būti |
| --- | --- | --- |
| B) radijas | `DMX - X GON [icy]` | `DMX - X GON` (`[icy]` — ICY metaduomenų artefaktas) |
| A) F6 | `groja: -` | `groja: nieko` |
| C) VPS | `root@5.175.171.113 (cache 18.9 s)` | `root@5.175.171.113 (podėlis: 18,9 s)` |
| A) ZVERIS | `modelis=huihui_ai/llama3.3-abliterated:70b, uploads=0` | `modelis: llama3.3 70B · įkėlimai: 0` |
| C) diskas | `laisva 7.8G is 14G (43% uzimta)` | `laisva 7,8 GB iš 14 GB (užimta 44 %)` |

**Servisų pavadinimų stilius nesuderintas:** `n8n`, `Naršyklės daemonas`, `F6 panelis`,
`ZVERIS UI`, `Kumstis tools` → siūlau `n8n`, `Naršyklės daemonas`, `F6`, `Žvėris`, `Kumštis`.

**Informacija dubliuojasi:** `Servisai rodomas 5/6` antraštėje ir `RODOMAS: 5 NE: 1`
A) sekcijoje — tas pats du kartus tame pačiame ekrane.

## 9. Kas atrodo kaip realios klaidos, o ne kosmetika

1. `E) PRANESIMU_LOG.txt`:
   `ntfy KLAIDA: The remote name could not be resolved: 'ntfy.sh'`
   → DNS nepavyko; po kelių sekundžių `ntfy OK` → pereinama problema, bet verta retry logikos
   ir lietuviško pranešimo (dabar lietuviškame ekrane angliškas exception tekstas).
2. `A) Naršyklės CDP :9222` → `NE` (chrome be CDP). Ar tai normalu, ar trūksta
   `--remote-debugging-port=9222` paleidžiant Chrome?
3. `(auto-atnaujinimas po N s)` — N **keičiasi** tarp kadrų: `5 s` → `2 s` → `1 s` → `4 s`
   → `5 s`. Ar tai skaičiuotuvas (countdown), ar tikras bug'as? Jei tai atsinaujinimo
   intervalas — jis turi būti pastovus.

## 10. Kad gaučiau kodą ir galėčiau sutvarkyti

`pultas.py` **NEįkelk į viešą repo** — jame gali būti VPS slaptažodis (kaip buvo `_ssh.py`).

Duok tik reikalingas vietas (ne visą failą):

```powershell
# 1) netvarkingi užrašai ir formatai
Select-String -Path 'C:\Users\M\CLINE\pultas\pultas.py' `
  -Pattern 'RODOMAS|rodomas|True|auto-atnaujinimas|cache|uzimta|is 14G|icy|failu|aplanku' `
  -Context 3,3

# 2) CSS / HTML dalis
Select-String -Path 'C:\Users\M\CLINE\pultas\pultas.py' `
  -Pattern '<style|grid-template|display:\s*grid|\.card|class=' -Context 2,2
```

Gautą tekstą įklijuok — tai bus ~200–400 eilučių, ne visas failas.
Jei pultas HTML/CSS laiko atskiruose failuose — įkelk tik juos.

