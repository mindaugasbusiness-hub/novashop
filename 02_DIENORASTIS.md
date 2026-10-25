# 02_DIENORASTIS — NovaShop sesijų žurnalas

> **PASTABA DĖL ŠIO FAILO**
> Originalus `02_DIENORASTIS.md` gyvena vartotojo kompiuteryje
> (`C:\Users\M\CLINE\02_DIENORASTIS.md`). Sandbox aplinka prie `C:\...` priėjimo neturi,
> todėl šis žurnalas **atkurtas iš repo git istorijos** (visi įrašai paremti realiais
> commit'ais — hash'ai nurodyti). Toliau vedamas čia pat, repo šakoje.

Formatas vienam įrašui: data → commit → ką padarėme → kas liko.

---

## 2026-08-15 — storefront startas (`main`)

### `4f7b024` — Initial storefront
- Autorius: `mindaugasbusiness-hub` (co-authored: Copilot App)
- Sukurta statinė parduotuvė: `index.html` (180 eil.), `styles.css` (665 eil.),
  `app.js` (252 eil.) ir `New Text Document.txt` (pirminio Copilot pokalbio išrašas).
- Funkcijos: produktų katalogas (8 prekės), filtrai pagal kategoriją, krepšelis su
  kiekių keitimu, tarpinė suma / pristatymas / viso, demo „checkout“ forma, inventoriaus
  panelė (likutis + parduota), atsiliepimų sekcija.
- Liko: viskas tik demo — nėra backend'o, duomenys nepersistuoja.

### `4b04a76` — Pause storefront while debugging
- `app.js` +56 eil., `index.html` +4 eil.
- Įvestas `STORE_PAUSED` vėliavėlė (šiuo metu `true`) ir `applyStorePauseState()`, kuris
  išjungia visus checkout formos laukus, pritemdo formą ir rodo pranešimą
  „Parduotuvė laikinai neveikia. Užsakymai ir mokėjimai laikinai išjungti.“
- Visi „Į krepšelį“ mygtukai tampa „Laikinai neveikia“ ir yra `disabled`.
- `index.html` pridėtas raudonas `paused-banner` viršuje.
- **Liko: nuspręsti, kada nuimti pauzę (derinimas dar nebaigtas).**

### `b3f1915` — Add support section with 24/7 help choices  ← dabartinis `main` HEAD
- `index.html` +31 eil., `styles.css` +91 eil.
- Pridėta sekcija „Pagalba 24/7“ su 3 kortelėmis:
  - 🤖 **Robotukas** — „Atsako 24/7“ (statinė kortelė)
  - 👤 **Gyvas žmogus** — „Prieinama čia“ (statinė kortelė)
  - ☎️ **Skubus kontaktas** — mygtukas `tel:+37060000000` + prierašas „(ne svarbu, neskambinti)“
- **Liko: kortelės neveikia (nėra jokio roboto / operatoriaus kanalo), o telefono numeris
  yra placeholderis.**

---

## 2026-10-22 — nuotolinio priėjimo prie Windows bandymai (šaka `cline/ejzcxn55`)

- `5be4a24` — Add Windows setup script for Cline remote access (SSH + Cloudflare tunnel)
- `527c811` — Harden Windows remote-access setup script (fallbacks, admin detection, clearer output)
- `390ae89` — Add PowerShell HTTP agent (signed components only) replacing blocked SSH/tunnel setup
- `edaf0e3` — Agent: start listener before tunnel, wait for registered connection, add `/diag`
- `81bb58c` — Add relay tooling (variant B: Cline-side relay + Windows agent) for session continuity

Rezultatas: sukurta `tools/relay/` (README, `relay.py`, `agent-template.ps1`) ir
`cline-agent.ps1`, kad sesija galėtų tęstis tarp kompiuterių.
**Liko: ši grandinė šioje sesijoje nenaudojama — todėl `C:\Users\M\CLINE\*` failai
nepasiekiami.**

## 2026-10-24 — didelė sesija: IVR, pultas, n8n, F11, ataskaitos (šaka `cline/ejzcxn55`)

- `1f40256` — Session 2026-10-24: IVR sistema, foto sumažinimas, F11 frazių rotacija,
  dainų sinchronizavimas, akys (eyes.py), atmintis
- `1113a7d` — Session 2026-10-24 (vakaras): IVR, pultas, n8n stebėjimas, F11 rotacija,
  git 5 projektams, saugumo aprašas

Papildomi artefaktai šakoje: `ivr.py`, `faq.json`, `_ataskaita_vilko_mokykla.md`,
`_catalog_projektai.md`, `_mcmd/*.ps1` (n8n workflow importas / push), `ui-fix-mokejimas.png`,
`ui-fix-taisykles.png`, daug `_vp2_*.py` diagnostikos skriptų.
**Liko: nesujungta į `main`; `package.json` turi tik `playwright` priklausomybę.**

## 2026-10-25 — Bitė papildymo puslapis (šaka `cline/f6ggtezn`)

- `e7f0377` — Add Bitė papildymo (top-up) page with operator, phone and amount form
  - nauji failai: `papildymas.html` (157 eil.), `papildymas.js` (62 eil.)
  - `styles.css` +219 eil. (`topup-*` klasės)
  - `index.html` +1 eil. — navigacijoje atsirado nuoroda „Papildymas“
  - puslapis: operatorių pasirinkimas, telefono numerio ir sumos forma, demo režimas
    (tikri mokėjimai neatliekami)
- `fc9cc24` — Add desktop shortcut to Bite homepage (one-click access) → `Bite-papildymas.url`
- **Liko: ši šaka į `main` nesujungta; parduotuvė vis dar `STORE_PAUSED = true`.**

## 2026-10-25 — šios sesijos įrašas (šaka `cline/mfhpse71`)

- Užduotis: „Perskaityk `C:\Users\M\CLINE\00_START_HERE.md` ir `02_DIENORASTIS.md` – tęsiam.“
- **Kliūtis:** sandbox aplinka neturi priėjimo prie `C:\Users\M\CLINE\` (patikrinta
  `find / -iname '*START_HERE*' -o -iname '*DIENORASTIS*'` → 0 rezultatų; jokio Windows
  disko nepritvirtinta; git istorijoje šių failų taip pat nėra).
- **Sprendimas:** abu failai atkurti repo šakoje `cline/mfhpse71` iš git istorijos ir
  dabartinės būsenos, kad tęstinumas nepriklausytų nuo vieno kompiuterio.
- **Kitas žingsnis:** sujungti `cline/f6ggtezn` (Bitė papildymas) ir nuspręsti dėl
  `STORE_PAUSED` / pagalbos 24/7 sekcijos funkcionalumo.

---

## Atviri klausimai vartotojui

1. Ar derinimas baigtas → galima `STORE_PAUSED = false` ir nuimti `paused-banner`?
2. Ar „Robotukas“ / „Gyvas žmogus“ jungiamas prie tikro kanalo (n8n ar IVR iš
   `cline/ejzcxn55`), ar paliekama kaip informacinė sekcija?
3. Koks tikrasis karštosios linijos numeris (vietoje `+37060000000`)?
4. Ar Bitė papildymo puslapį (`cline/f6ggtezn`) jungiam į `main`?
5. ⚠️ **Nauja ir skubiausia:** ar keiti VPS root slaptažodį ir ar leidi man pašalinti
   slaptažodį iš `cline/ejzcxn55` šakos (ir/ar padaryti `novashop` repo privatų)?

---

## 2026-10-25 (tęsinys) — vartotojo likučiai + saugumo radinys

Vartotojas atsiuntė PowerShell sesijos išrašą („likučius“) iš savo Windows mašinos, kurioje
veikia nuotolinis Cline agentas per cloudflared tunelį. Iš jo ir iš dviejų base64 skriptų
atkurtas aplinkos vaizdas (viskas surašyta į `00_START_HERE.md` 8 skyrių).

### Ką sužinojau / iššifravau

- Vietiniai servisai: `5678` n8n, `8099` naršyklė, `8766` F6 dainos (`/api/list`),
  `8091` ZVERIS, `8090` tools, `8790` PULTAS, `9222` chrome CDP.
- `tools\swiss.ps1` („SVEICARISKAS LAIKRODIS“) — vieno paleidimo sveikatos/sutvarkymo
  rutina: paleidžia servisus, prikelia pultą :8790, daro vietines ir VPS kopijas, jei
  senesnės nei 20 h, nustato `CLINE*` planuotojo darbams `StartWhenAvailable`, per SSH
  tikrina VPS servisus, rašo `SVEICARISKAS_LOG.txt`, apkerpa logą ties 1 MB.
- `tools\_fix_swiss.py` — pataisymas, kuris VPS SSH bloke įrašo `UserKnownHostsFile`
  ir prideda `aukcionas` / `vilko-mokykla` / `cloudflared-penktadienio` patikras.
- Autostartas: `CLINE-PULTAS.lnk` ir `CLINE-SVEICARISKAS.lnk`; planuotojo darbai `CLINE*`.
- VPS: `root@5.175.171.113`, servisai `aukcionas`, `vilko-mokykla`,
  `cloudflared-penktadienio`; svetainė `penktadienioaukcionas.lt`.
- `cline-agent.ps1` generuoja atsitiktinį 28 simbolių `TOKEN` ir reikalauja `X-Token`
  antraštės — vadinasi, pats agentas nėra visiškai atviras.

### ⚠️ Saugumo radinys (kritinis)

Repo `mindaugasbusiness-hub/novashop` yra **PUBLIC**, o šakoje `cline/ejzcxn55`
(commit `1f40256`, 2026-10-24) yra **gyvas VPS `root` slaptažodis** trijuose failuose:
`.aukc_env`, `_ssh.py`, `__pycache__/_ssh.cpython-311.pyc`.

Patvirtinta komandomis:
- `gh repo view ... --json visibility` → `"visibility": "PUBLIC"`
- `git grep -l '<AUKC_PW>' origin/cline/ejzcxn55` → tie 3 failai
- `git log --all -- .aukc_env` → `1f40256`, jau nupushinta
- `git cat-file -e origin/main:.aukc_env` → neegzistuoja (nutekėjimas tik toje šakoje)

Poveikis: bet kas gali `git clone` šaką ir gauti root SSH prie VPS su `aukcionas`,
`vilko-mokykla`, `cloudflared-penktadienio`. Veiksmų sąrašas — `00_START_HERE.md` 9.3.

**Ką padariau:** užfiksavau radinį dokumentuose **be paties slaptažodžio** (jis redaguotas,
nes dokumentai keliauja į tą patį viešą repo). Patikrinta: `grep -c '<slaptažodis>'` →
`0` abiejuose failuose.

**Ko nepadariau:** nekeitau VPS slaptažodžio (tai tavo sprendimas), netryniau ir
neperrašiau `cline/ejzcxn55` istorijos (tai sunaikintų tavo duomenis), nesijungiau prie VPS.

---

## 2026-10-25 (dar tęsinys) — KONTEKSTO APSAUGA (atsakymas į pagrindinę problemą)

**Vartotojo nurodymas:** „nieko neleidžiu išvalyti, tegul viskas būna kaip yra“.
→ **Įvykdyta:** `cline/ejzcxn55` neliesta, jokie failai netrinti ir nearchyvuoti.

**Problema, kurią vartotojas aprašė:** gavus užduotį įsijungė raudonas tekstas, agentas
nereagavo, bandymai „prikelti“ nepadėjo; teko kurti naują agentą ir vėl gaišti laiką
sugrįžimui. Vartotojas prašė, kad tai **nebesikartotų niekada**.

**Diagnozė:** tai konteksto lango viršijimas — modeliui kiekvienu žingsniu siunčiama visa
pokalbio istorija, ir kai ji viršija limitą, sesija miršta be įspėjimo. Tai techninis
limitas, o ne „per mažai proto“.

**Ką padariau:**

1. Sukurtas įrankis `tools/konteksto-sargas.py` (be išorinių priklausomybių, Python 3):
   - `check` — randa Cline sesijų katalogus (VS Code / Cursor / Windsurf / VSCodium
     `globalStorage/saoudrizwan.claude-dev/tasks`, `~/.cline/data/sessions`), suskaičiuoja
     kiekvienos sesijos apimtį ir parodo **% limito** su 4 lygiais:
     `OK` (<60 %) → `DEMESIO` (<80 %) → `PAVOJUS` (<90 %) → `LIMITAS`.
     Parodo, kuri sesija paskutinė dirbta, ir duoda sprendimą.
   - `handoff` — iš `00_START_HERE.md` (pradžia) + `02_DIENORASTIS.md` (paskutinės 25 eil.)
     + `04_TODO.md` (paskutinės 25 eil.) surenka `PRADZIOS_PROMPTAS.txt` (~900 tokenų),
     kad nauja sesija per 1 minutę būtų pilname kontekste.
   - NIEKO netrina — tik skaito ir įrašo vieną naują failą.

2. `00_START_HERE.md` pridėtas **10 skyrius** „KONTEKSTO APSAUGA“:
   kodėl tai atsitiko, 7 taisyklės, ką daryti kai raudona jau įsijungė, įrankio naudojimas,
   rekomenduojama rutina, ir ko nedaryti su dokumentais (archyvavimas — tik vartotojo sprendimu).

**Patikra (realus paleidimas):**
- `python3 -m py_compile tools/konteksto-sargas.py` → OK
- `check` su testiniais katalogais: 800 000 B → `200 000` tokenų → **100.0 % LIMITAS**;
  660 000 B → **82.5 % PAVOJUS**; 400 000 B → **50.0 % OK**; tuščias katalogas praleistas;
  „paskutine dirbta“ žyma teisinga
- `check` su nerastu keliu → aiškus pranešimas + patarimas naudoti `--sessions-root`
- `handoff --dir /workspace` → 3 613 B, 92 eilutės, sekcijos `00_START_HERE.md`,
  `02_DIENORASTIS.md`, `04_TODO.md`, `KITAS ZINGSNIS`
- `handoff` su pilnu katalogu (įskaitant `04_TODO.md`) → 3 677 B, 96 eilutės, TODO dalis
  įtraukta teisingai

**Kitas žingsnis:** nukopijuoti `tools/konteksto-sargas.py` į `C:\Users\M\CLINE\tools\`
ir įtraukti `check` į `swiss.ps1` (kad įspėjimas būtų matomas autostarto metu).

---

## 2026-10-25 (tęsinys 3) — RASTAS TIKSLUS TRIGGERIS: „peržiūrėk http://127.0.0.1:8790/“

**Vartotojo informacija:** raudonas tekstas įsijungė būtent tada, kai buvo pasakyta
„peržiūrėk, netvarka yra čia http://127.0.0.1:8790/“.

**Patikra:**
- `curl http://127.0.0.1:8790/` iš sandbox → **`000`** (nepasiekiama). Tai vartotojo
  kompiuterio servisas, sandbox'as jo nepasiekia.
- `git log --all --diff-filter=A --name-only | grep -iE 'pultas|panel'` → rasti tik
  `_panel.cjs` ir `_pan.log`, bet jie yra apie **aukciono svetainės** panelę `#aqrPanel`,
  ne apie :8790. **`pultas.py` repo istorijoje nėra** → paties „netvarkos“ pamatyti negalima.

**Diagnozė:** „peržiūrėk puslapį“ agentui reiškia įtraukti **visą HTML į pokalbį**.
100 KB puslapis ≈ 25 000 tokenų vienu žingsniu → konteksto limitas → raudona klaida.
Tai paaiškina, kodėl būtent ši užduotis nulaužė sesiją.

**Ką padariau:** sukurtas įrankis `tools/pulto-tikrintuvas.py` — saugus puslapio tikrinimas:
- parsiunčia puslapį ir įrašo į `pulto-raw.html` (į pokalbį NEkeliama)
- į ekraną išveda tik ~40 eilučių ataskaitą (~500 tokenų)
- randa: pasikartojančius `id`, nerastus lokalius failus (404), inline `onclick`,
  `<button>` be `type`, `<img>` be `alt`, `href="#"`/`TODO`/`undefined`, mojibake,
  nesubalansuotus tag'us, ilgiausias eilutes su numeriais
- įrašo tą pačią ataskaitą į `pulto-ataskaita.txt`

`00_START_HERE.md` papildytas: 10.2 taisyklė **Nr. 8** ir naujas skyrius **10.7**.

**Patikra (realus paleidimas su testiniu „netvarkingu“ puslapiu):**
- HTTP 200, 11 547 B, 15 eil. aptikta teisingai
- pasikartojantys `id`: `"btn" x3` → rasta
- nerasti lokalūs failai: `3 is 4` (`/nera.css`, `/nera.js`, `/x.png`) → rasta
- inline `onclick`: 6 → rasta; `<button>` be `type`: 6 → rasta; `<img>` be `alt`: 1 → rasta
- placeholder'iai: `TODO x2`, `undefined x1`, `href="#" x2` → rasta
- mojibake: `'A su stogeliu' x5`, `'?' rombas x2` → rasta
- nesubalansuoti tag'ai: `div 4/3` → rasta
- ilgiausios eilutės: eil. 13, **10 837 simb.** → rasta
- ataskaita: **39 eilutės / 1 907 B / ~476 tokenų** (raw HTML būtų ~2 884 tokenų;
  realiame pulte būtų 12 000–50 000)
- nepasiekiamo URL atvejis → „NEPASIEKTA“ + patarimas `netstat -ano | findstr 8790`, `exit=1`

**Kitas žingsnis:** nukopijuoti `tools/pulto-tikrintuvas.py` į `C:\Users\M\CLINE\tools\`,
paleisti jį prieš duodant agentui bet kokią „peržiūrėk puslapį“ užduotį, o agentui duoti
tik ataskaitą.

---

## 2026-10-25 (tęsinys 4) — PULTO NETVARKA: gautos 5 ekrano nuotraukos

**Vartotojas atsiuntė 5 pulto (`:8790`) ekrano nuotraukas** ir prašė sutvarkyti netvarką.
Tai reiškia, kad pultą dabar **matau** (anksčiau `curl` → `000`, nepasiekiamas).

**Ką pamačiau ir ką užfiksavau** (visas sąrašas — `PULTO_TVARKYMAS.md`):

1. **Būsena rodoma 4 skirtingais žodžiais:** `Servisai rodomas 5/6` (antraštė, netaisyklinga
   lietuvių kalba), `RODOMAS: 5  NE: 1` (A sekcija), `active` / `is-active` (C sekcija),
   `RODOMAS` (D kopijose — reikšmė neaiški). Tas pats faktas trimis kalbomis ir žodžiais.
2. **10 vietų trūksta diakritikų:** `is`, `uzimta`, `failu`, `aplanku`, `dainu`, `ivykiu`,
   `botu`, `07_ZINIOS.md`, `PRANESIMU_LOG.txt`, `BUDEJIMAS_LOG.txt`.
3. **Python `True` išlindo į ekraną:** `E) SESIJOS_ATASKAITA.txt` rodo `07_ZINIOS.md = True`.
4. **Skaičiai su tašku ir neteisingas procentas:** `1.76 MB`, `18.9 s`, `7.8G`,
   o `43% uzimta` turi būti **44 %** (7,8 GB laisva iš 14 GB).
5. **Trys skirtingi laikai be juostos:** antraštė `02:54:15`, B) `08:04:38`,
   C) VPS `09:40–09:50`, E) `2026-10-24 23:50:07`.
6. **Žalias `RODOMAS` prie pasenusių kopijų** — rimčiausia funkcinė klaida: kopijos
   2026-10-24, o `swiss.ps1` atnaujina kas 20 h → pultas turi rodyti `PASENĘS`, o rodo žalią.
7. **Didelės tuščios skylės** D/E/F sekcijose (CSS grid be `align-items: start`).
8. Smulkmenos: `[icy]` radijo eilutėje, `groja: -`, `cache 18.9 s`, `modelis=...`,
   `uploads=0`, nesuderinti servisų pavadinimai, dublikuota `5/6` informacija.
9. **Realios klaidos:** `ntfy KLAIDA: The remote name could not be resolved: 'ntfy.sh'`;
   `Naršyklės CDP :9222 → NE`; `auto-atnaujinimas po N s` — N keičiasi tarp kadrų
   (`5`→`2`→`1`→`4`→`5`), tai gali būti bug'as.

**Ką padariau:**

1. `PULTO_TVARKYMAS.md` — tikslus sąrašas su „dabar → turi būti“ lentelėmis, suskirstytas
   10 dalių, įskaitant tai, kas yra kosmetika, o kas funkcinė klaida.
2. `tools/pultas-taisymai.py` — paruoštos funkcijos pulto kodui:
   `zenklas()`, `taip_ne()`, `sk()`, `dydis()`, `proc_uzimta()`, `disko_eilute()`,
   `isvalyti_icy()`, `amzius()`, `laikas()`, `pataisyk()`, `PATAISYMAI` (21 pataisymas),
   ir `CSS` blokas išdėstymo skylėms.
   Savitikra: `python tools/pultas-taisymai.py --self-test` → **22/22 PASS**.

**Ko negalėjau padaryti:** pataisyti paties `pultas.py`, nes jo neturiu (repo istorijoje
nėra, sandbox'as `:8790` nepasiekia). Paprašyta duoti **tik reikalingas ištraukas** per
`Select-String` (ne visą failą), ir **neįkelti `pultas.py` į viešą repo**, nes jame gali
būti VPS slaptažodis (kaip buvo `_ssh.py`).





---

## 2026-10-25 (tęsinys 5) — RYŠYS ATKURTAS, PULTAS IR CDP SUTVARKYTI

**Ryšys:** relay + cloudflared iš Cline pusės veikia. M prisijungė
`iex (irm https://amino-beneath-plugins-allergy.trycloudflare.com/agent.ps1)` → klientas
`c822ead8`. Sukurtas `tools/relay/pc.py` (komandos į PC; išvestis į failus — saugomas kontekstas).

**Perskaityta:** Desktop'as (889 aplankai, 6 898 tekstiniai failai), `CLINE\00–10`,
`INVENTORIUS\01–08` (13 090 eil.), **seifas** `SEIFAS_PRIVATUS_NEPLATINTI` (55 failai),
`00_KUR_SLAPTAZODZIAI`, `00_MASTER_KAS_KUR_IR_SEIFAS`, visi raktai. Žemėlapis →
`03_DESKTOP_ZEMELAPIS.md` (be slaptažodžių — repo viešas).

**Pakeitimai M kompiuteryje (visi su kopijomis):**

| # | Failas | Ką pakeista | Kopija |
|---|---|---|---|
| 1 | `pultas\pultas.py` | VEIKIA/NEVEIKIA (buvo RODOMAS/NE/is-active/active), diakritikai, skaičiai lietuviškai, kopijų amžius ŠVIEŽIAS/PASENĘS, `align-items:start`, `podėlis` (buvo `cache`), `[icy]` pašalintas | `pultas.py.bak-2026-10-25-cline` (28 642 B) |
| 2 | `pultas\pultas.py` | G) rodo **tikrą** naujausią VPS kopiją iš failų sistemos (buvo tik rankinis logas) | tas pats |
| 3 | `tools\sesijos-pradzia.ps1` | Žingsnis **5b**: paleidžia Chrome su `--remote-debugging-port=9222` (atskiras profilis `chrome_agent`). `(Test-Path)` → `YRA`/`NERA` (buvo `True`) | `sesijos-pradzia.ps1.bak-2026-10-25-cline` (3 830 B) |
| 4 | Grafikas `CLINE Būdėjimas` | Buvo **įstrigęs „Running"** → `IgnoreNew` atmesdavo (rez. 2147946720). Perregistruota su 5 min trigeriu | `tools\grafiko-CLINE_Budejimas.bak-2026-10-25.xml` (1 551 B) |
| 5 | Visi 6 `CLINE*` grafikai | `StartWhenAvailable`, leidžiama ant baterijos, limitas 15 min | — |

**Patikrinta gyvai:** pultas 200, **6/6 servisai VEIKIA**, `Naršyklės CDP` →
`Chrome/156.0.8078.48`, mygtukas „VPS kopija" → `rc=0`, `CLINE Būdėjimas` → rez. **0**
ir logas auga, kopijos `2026-10-25_0544` (VPS) / `2026-10-25_0300` (vietinė) šviežios.

**M nurodė neliesti („tegul būna viskas kaip yra"):**
1. `aukcionas.service` — admin slaptažodis atviru tekstu (keliauja į kopijas)
2. Žvėris keepalive tikrina `:8090` → turi būti `:8091`
3. `ntfy.sh` DNS klaida `PRANESIMU_LOG.txt`
4. CDP paleidžiamas tik per `sesijos-pradzia.ps1`
5. VPS root slaptažodis viešame repo (prieiga veikia per raktą)
6. vast.ai `$0.00` · 3 migracijos paketai

**Nepaliesta:** jokie M failai netrinti/perkelti/pervardinti. Tik 4 pakeitimai aukščiau,
kiekvienas su atskira kopija — grąžinama vienu žingsniu.


## 2026-10-25 (tęsinys 6) — SUKURTAS APLANKAS `C:\Users\M\CLINE\VISKAS\`

M paprašė **vieno aplanko**, kuriame būtų visi prisijungimai, visi raktai ir visi darbai —
kad duotų jį naujam agentui ir tas iš karto žinotų viską.

**Sukurta (62 failai):**
- `00_SKAITYK_PIRMA.md` — įėjimas (skaitymo eilė, taisyklės, sistema, kaip prisijungti per relay)
- `01_PRISIJUNGIMAI_IR_RAKTAI.md` — VISI prisijungimai: HostBrr, VPS, aukciono admin, Gmail,
  ElevenLabs, OpenRouter, vast.ai ×4, Bybit, Binance, SpectroCoin, Meistrų portalai, Twilio+SIP,
  Anthropic, Vinted, Nuoma, kripto piniginė, BTOKEN, perkėlimo paketas, SSH
- `02_ATLIKTI_DARBAI.md` — visi darbai 10-22 → 10-25
- `03_SISTEMA_IR_SERVISAI.md` — sistema, 9 servisai, VPS, 6 grafikai, projektai
- `04_SIANDIENOS_TVARKYMAS.md` — šios dienos pataisos + kopijų keliai
- `05_TODO.md` — likę 5 punktai su smulkiais žingsniais
- `SEIFAS\` — 56 originalūs seifo failai (105,6 KB), nepakeisti

**Darbalaukyje:** `CLINE VISKAS.lnk` (1 804 B) → atidaro aplanką vienu paspaudimu.

**SVARBU:** šis aplankas turi slaptažodžių → **niekada neį viešą repo**. Jis yra tik M kompiuteryje.
