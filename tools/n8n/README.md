# n8n paleidimas ir budėtojas (`tools/n8n`)

Sukurta: **2026-10-28** · Šaka: `cline/da6qq3k9` · Autorius: Cline (agentas)
Tikslas: n8n **:5678** ir brokerio prievadas **:5679** nebekristų po Windows perkrovimo.

---

## 1. Kas iš tikrųjų vyksta (svarbiausia dalis)

Ankstesnis paaiškinimas „:5679 neveikia, nes antras n8n egzempliorius užima tą patį portą"
yra **netikslus**. Faktai, rasti repo istorijoje (`_out/readNative2.txt`, `_out/runWf.txt`,
`_mcmd/run-wf2.ps1`, n8n `task-broker-server.js`):

| Prievadas | Kas jį laiko | Ką tai reiškia |
|---|---|---|
| **5678** | n8n serverio procesas (`node n8n start`) | UI, webhook'ai, `/healthz` |
| **5679** | **tas pats** n8n procesas | n8n **Task Broker** (`N8N_RUNNERS_TASK_BROKER_PORT`) |

Patikrintas matavimas iš tikros mašinos:

```
5678 -> PID 7976 (node, pradzia 10/24/2026 04:44:48)
5679 -> PID 7976 (node, pradzia 10/24/2026 04:44:48)   <-- TAS PATS PID, ne antras n8n
```

Tikroji klaida atsiranda tik tada, kai **paleidžiama antra n8n komanda** (pvz. `n8n execute`
arba `import:workflow`) **kol serveris dar veikia**:

```
n8n Task Broker's port 5679 is already in use. Do you have another instance of n8n running already?
execute exit: 1
```

Ką tai reiškia praktiškai:

* **n8n nereikia antro egzemplioriaus.** „Brokeris" nėra atskira paslauga -- jis gimsta ir miršta
  kartu su n8n serveriu. Todėl pulto lentelėje „Antras n8n egzempliorius užima portą" klaidina:
  teisinga formuluotė -- **„CLI komanda susiduria su veikiančio serverio brokeriu"**.
* **Sprendimas:** serveriui brokeris lieka `5679`, o CLI komandoms duodamas **laisvas** prievadas
  `5690..5699`. Tai jau buvo patikrinta 2026-10-25 (`run-wf2.ps1`):
  `n8n Task Broker ready on 127.0.0.1, port 5699` → `execute` grąžino 0.
* Jei nori **atskiro** brokerio kaip tikros atskiros paslaugos -- tai jau ne „antras n8n", o
  `N8N_RUNNERS_MODE=external` su atskiru `n8nio/runners` konteineriu. Windows + `internal`
  režime to daryti nereikia ir nerekomenduojama.

---

## 2. Failai ir ką jie daro

| Failas | Paskirtis |
|---|---|
| `n8n-konfig.ps1` | **Vienintelė tiesos vieta**: keliai, prievadai (5678/5679), žurnalai ir sprendimo funkcija `Get-N8nBusena` |
| `start-n8n.ps1` | Paleidžia **vieną** n8n serverį: uždaroma sena kopija, tikrinami prievadai, laukiama `/healthz` |
| `start-n8n.cmd` | Trumputis apvalkalas (ASCII, be diakritikų) -- jį kviečia Task Scheduler |
| `restart-n8n.ps1` | Sustabdo ir paleidžia iš naujo -- **šitą kviečia pulto mygtukas** |
| `n8n-watchdog.ps1` | Budėtojas: kas ciklą tikrina :5678 ir :5679, prikelia, jei krenta |
| `registruok-uzduotis.ps1` | Sukuria Task Scheduler užduotis „N8N START LOGON" ir „N8N WATCHDOG" |
| `n8n-diagnostika.ps1` | Būklės ataskaita: prievadai, PID, rezervuoti diapazonai, versija, užduotys |
| `n8n-cli.ps1` | **Sprendžia :5679 konfliktą**: CLI komandos paleidžiamos su laisvu brokerio prievadu |
| `test-n8n-logika.ps1` | Savitikra (40 patikrų): sprendimai, prievadų paieška, aplinka, apsaugos |
| `savitikra.py` | Patikrina failų koduotę/BOM/CRLF ir ar nėra slaptų reikšmių |

---

## 3. Įdiegimas ant Windows

```powershell
# 1) Nukopijuok šį aplanką į savo įrankius
$tikslas = 'C:\Users\M\CLINE\tools\n8n'
New-Item -ItemType Directory -Force -Path $tikslas | Out-Null
Copy-Item -Path .\tools\n8n\* -Destination $tikslas -Recurse -Force

# 2) Jei jau turi seną start-n8n.cmd -- pirmiausia kopija (1 taisyklė: nieko netrinti)
Copy-Item 'C:\Users\M\CLINE\tools\start-n8n.cmd' `
          ('C:\Users\M\CLINE\tools\start-n8n.cmd.bak-' + (Get-Date -Format 'yyyyMMdd_HHmmss')) -Force

# 3) Patikrink kelius: jei tavo projektas ne C:\Users\M\Desktop\Kumstis -- nustatyk
$env:N8N_ROOT = 'C:\tavo\kelias\iki\Kumstis'
```

`n8n-konfig.ps1` kelius paima iš `$env:N8N_ROOT` (numatytas `C:\Users\M\Desktop\Kumstis`)
ir `$env:N8N_TOOLS_DIR` (numatytas `C:\Users\M\CLINE\tools\n8n`).
**Jokių „C:\Users\M\kelias\iki\projekto" vietos laikiklių nėra** -- savitikra tai tikrina.

---

## 4. Naudojimas (kasdienis)

```powershell
cd C:\Users\M\CLINE\tools\n8n

# Paleisti n8n (vieną egzempliorių, :5678 + brokeris :5679)
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-n8n.ps1

# Perkrauti (šitą kviečia ir pulto mygtukas)
powershell -NoProfile -ExecutionPolicy Bypass -File .\restart-n8n.ps1

# Tik sustabdyti
powershell -NoProfile -ExecutionPolicy Bypass -File .\restart-n8n.ps1 -TikStop

# Būklė vienu ekranu (nieko nekeičia)
powershell -NoProfile -ExecutionPolicy Bypass -File .\n8n-diagnostika.ps1
```

**CLI komandos -- VISADA per `n8n-cli.ps1`**, ne tiesiogiai per `n8n`, kad neužimtum `:5679`:

```powershell
.\n8n-cli.ps1 execute --id=aukcionas0000001 --rawOutput
.\n8n-cli.ps1 import:workflow --input="C:\Users\M\CLINE\n8n\aukciono-stebejimas.json"
.\n8n-cli.ps1 publish:workflow --id=aukcionas0000001
```

Skriptas pats suranda laisvą brokerio prievadą (5690-5699) ir, jei vis tiek susiduria su
klaida „Task Broker's port ... is already in use", pasako tai aiškiai, o ne tyliai krenta.

---

## 5. Automatinis prikėlimas (Task Scheduler)

```powershell
# Registruoti abi užduotis
powershell -NoProfile -ExecutionPolicy Bypass -File .\registruok-uzduotis.ps1

# Patikrinti, ar registruotos
powershell -NoProfile -ExecutionPolicy Bypass -File .\registruok-uzduotis.ps1 -Patikrinti

# Išregistruoti (jei nebereikia)
powershell -NoProfile -ExecutionPolicy Bypass -File .\registruok-uzduotis.ps1 -Isregistruoti
```

Sukuriamos dvi užduotys:

| Užduotis | Ką daro |
|---|---|
| `N8N START LOGON` | Prisijungus paleidžia `start-n8n.cmd` su 30 s delsa (kad tinklas spėtų pakilti) |
| `N8N WATCHDOG` | **Kas 1 minutę** tikrina :5678 ir :5679, prikelia, jei neveikia |

Alternatyva be Task Scheduler -- vienas nuolatinis procesas:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\n8n-watchdog.ps1 -Loop
```

### Ką budėtojas daro ir ko NEDARO

| Situacija | Sprendimas | Ką daro |
|---|---|---|
| Serveris atsako, brokeris klauso | `GERAI` | nieko |
| Serveris atsako, brokeris neklauso | `PERKRAUTI` | perkrauna |
| Serveris neatsako, :5678 **laisvas** | `PALEISTI` | paleidžia |
| Serveris neatsako, :5678 **užimtas kito PID** | `SVETIMAS` | **NIEKO NEŽUDO**, rašo į žurnalą |
| Serveris neatsako, bet ką tik paleistas (<120 s) | `KYLA` | laukia, neleidžia antro starto |

Apsaugos, kad budėtojas pats nesukurtų dviejų n8n:

1. vienu metu leidžiamas tik **vienas** budėtojas (PID failas `n8n-watchdog.pid`);
2. startas praleidžiamas, jei `/healthz` jau atsako;
3. startas praleidžiamas, jei yra „booting" žyma jaunesnė nei 120 s;
4. svetimo proceso **niekada** nežudo -- tik praneša.

---

## 6. Pulto mygtukas „Restartuoti n8n"

Pulto kodas (`pultas.py`) **nėra repo** (jame būdavo VPS slaptažodis), todėl paruoštas
įrankis, kuris įterpia mygtuką ir apdorojimą **su `.bak` kopija**:

```powershell
cd C:\Users\M\CLINE\tools
python pulto-mygtukas-restart-n8n.py --tikrinti C:\Users\M\CLINE\pultas\pultas.py
python pulto-mygtukas-restart-n8n.py --diegti  C:\Users\M\CLINE\pultas\pultas.py --sausai
python pulto-mygtukas-restart-n8n.py --diegti  C:\Users\M\CLINE\pultas\pultas.py
```

* `--html` parodo mygtuko HTML (`act('/restart-n8n')`);
* `--python` parodo `restart_n8n()` funkciją ir maršrutizavimo eilutę;
* jei pulto maršrutizavimas kitoks -- įklijuok `--python` išvestį rankiniu būdu;
* savitikra: `python pulto-mygtukas-restart-n8n.py --self-test` (22/22).

---

## 7. Windows rezervuoti prievadai (Hyper-V po perkrovimo)

Jei n8n pakimba **be jokios klaidos**, priežastis dažnai yra Windows rezervuotas diapazonas:

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

* Jei `5678`/`5679` patenka į diapazoną: arba `net stop winnat` + `net start winnat`
  (reikia administratoriaus), arba pakeisk prievadą **vienoje vietoje** -- `n8n-konfig.ps1`,
  `ServerioPrievadas` (pvz. `13625`), ir pulto konfigūracijoje.
* `n8n-diagnostika.ps1` šitą tikrina automatiškai ir pasako, jei prievadas rezervuotas.
* Dėl n8n versijos: laikykis **naujausios 1.x** (šaka su sutvarkytu startu -- 1.105.0+).
  Versiją parodo `n8n-diagnostika.ps1`.

---

## 8. Patikros sąrašas (ką daryti iš eilės)

```powershell
# 1) Sustabdyti n8n (tik savo; 1 taisyklė -- nieko netrinti)
powershell -NoProfile -ExecutionPolicy Bypass -File .\restart-n8n.ps1 -TikStop

# 2) Paleisti vieną n8n
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-n8n.ps1

# 3) Patikrinti abu prievadus
curl http://127.0.0.1:5678/healthz     # turi atsakyti 200
powershell -NoProfile -ExecutionPolicy Bypass -File .\n8n-diagnostika.ps1

# 4) Registruoti budėtoją
powershell -NoProfile -ExecutionPolicy Bypass -File .\registruok-uzduotis.ps1

# 5) Perkrauti Windows ir po prisijungimo patikrinti:
#    - pultas rodo „Servisai veikia: 11/11"
#    - :5678 atsako, :5679 laiko TAS PATS PID kaip :5678
```

---

## 9. Grąžinimas (rollback)

* Pultas: atkurti iš `pultas.py.bak-<data>` (įrankis ją padaro automatiškai).
* Senas paleidiklis: `C:\Users\M\CLINE\tools\start-n8n.cmd.bak-<data>`.
* Užduotys: `registruok-uzduotis.ps1 -Isregistruoti`.
* Prievado pakeitimai: visi vienoje vietoje -- `n8n-konfig.ps1`.

---

## 10. Ką patikrinau, o ko ne (4 taisyklė: tiesa apie galimybes)

**Patikrinta šioje sesijoje (be prieigos prie tavo Windows mašinos):**

* visų 7 `.ps1` failų **sintaksė** -- tikru PowerShell 7.4.6 parseriu: **0 klaidų**;
* **logikos testai** `test-n8n-logika.ps1` -- **40/40 PASS** (sprendimai GERAI/PERKRAUTI/
  SVETIMAS/KYLA/PALEISTI, laisvo brokerio paieška, aplinka, žurnalas, apsaugos);
* **failų koduotė** `savitikra.py` -- **8/8 PASS** (`.cmd` ASCII+CRLF be BOM, `.ps1` UTF-8+BOM+CRLF);
* pulto įrankio savitikra -- **22/22 PASS**.

**Nepatikrinta (nes nėra prieigos prie tavo kompiuterio):**

* ar tikrai veikia `Get-NetTCPConnection`, `Get-CimInstance`, `schtasks` tavo mašinoje --
  šie kvietimai testuose buvo imituoti;
* ar `N8N_ROOT` tavo mašinoje tikrai `C:\Users\M\Desktop\Kumstis` (jei ne -- nustatyk kintamąjį);
* ar pultas atsakys į naują mygtuką -- reikia paleisti `--diegti` ir perkrauti pultą;
* tiksli n8n versija tavo mašinoje.

Pirmas žingsnis tavo mašinoje turi būti `n8n-diagnostika.ps1` -- ji parodys, ar keliai teisingi
ir ką tiksliai keisti.

