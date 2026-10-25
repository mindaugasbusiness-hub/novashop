# 00_START_HERE — NovaShop (Cline sesijos paleidimo failas)

> **SVARBU / PASTABA DĖL ŠIO FAILO**
> Originalus `00_START_HERE.md` gyvena vartotojo kompiuteryje:
> `C:\Users\M\CLINE\00_START_HERE.md`.
> Ši sandbox aplinka prie `C:\...` priėjimo neturi (patikrinta: `find / -iname '*START_HERE*'`
> → nieko; jokio Windows disko čia nepritvirtinta).
> Todėl šis failas yra **atkurtas iš repo git istorijos ir dabartinės būsenos**, kad darbą
> būtų galima tęsti. Jei originalas turi papildomų punktų — įkelk jį į repo (šaką) ir
> sujungiam.

---

> ## ⚠️ SKUBU: NUTEKĖJĘS VPS ROOT SLAPTAŽODIS
> Viešoje repo šakoje `cline/ejzcxn55` yra **gyvas `root@5.175.171.113` slaptažodis** —
> failai `.aukc_env`, `_ssh.py`, `__pycache__/_ssh.cpython-311.pyc`.
> Repo `mindaugasbusiness-hub/novashop` yra **PUBLIC**, todėl slaptažodį gali nusikopijuoti
> bet kas, kas atsidaro šaką. **Keisk VPS root slaptažodį dabar pat.**
> Detalės ir veiksmų sąrašas — **9 skyriuje**.

---

## 1. Kas tai per projektas

**NovaShop** — statinė demo elektroninė parduotuvė (produktų katalogas, krepšelis,
kiekių keitimas, sumos skaičiavimas, demo „checkout“, inventoriaus panelė, atsiliepimai,
pagalbos 24/7 sekcija).

- Repo: `https://github.com/mindaugasbusiness-hub/novashop.git`
- Kalba: HTML + CSS + grynas JavaScript (be karkasų, be build žingsnio)
- Backend: **nėra** — „checkout“ tik demo (duomenys laikomi atmintyje, nepersistuoja)

## 2. Kaip paleisti

```bash
# bet kuriame kataloge su failais
python3 -m http.server 8080
# arba tiesiog atidaryti index.html naršyklėje
```

Failų sąrašas ir patikra:

```bash
node --check app.js        # JS sintaksė
ls index.html styles.css app.js
```

## 3. Failų žemėlapis (šaka `main`)

| Failas | Paskirtis |
| --- | --- |
| `index.html` | Visa parduotuvės struktūra: hero, pasiūlymai, katalogas, inventorius, pagalba 24/7, atsiliepimai, krepšelio panelė |
| `styles.css` | Visas dizainas (kintamieji `:root`, hero, kortelės, krepšelis, pagalbos kortelės, responsive) |
| `app.js` | Produktų masyvas, filtrai, krepšelis, sumos, inventoriaus atvaizdavimas, „checkout“ |
| `New Text Document.txt` | Pirminio Copilot pokalbio išrašas (istorinis artefaktas, ne kodas) |

### Svarbūs `app.js` elementai

- `products` — 8 prekės, kategorijos `tech` / `sport` / `home` (AirPods Pro, Tesla šviesos juosta, Pilates kamuolys, 4K monitorius, bėgimo bateliai, lauko kėdė, smart watch, joga kilimėlis)
- `shipping = 3.99`, pristatymas nemokamas kai tarpinė suma ≥ €75
- `STORE_PAUSED` — **šiuo metu `true`** (parduotuvė sustabdyta derinimo metu)
- `applyStorePauseState()` — išjungia visus checkout formos laukus ir rodo pranešimą
- `showPausedStatus()` — tekstas: „Parduotuvė laikinai neveikia. Užsakymai ir mokėjimai laikinai išjungti.“
- Krepšelio panelė valdoma per `#cart-toggle` / `#cart-close` (`class="open"`)

## 4. Dabartinė būsena

- `main` HEAD: **`b3f1915`** — „Add support section with 24/7 help choices“ (2026-08-15)
- Parduotuvė **sustabdyta**: `STORE_PAUSED = true`, o `index.html` viršuje yra raudonas
  `paused-banner` su tuo pačiu pranešimu.
- Pagalbos 24/7 sekcija („Robotukas / Gyvas žmogus / Skubus kontaktas“) yra **tik statinės
  kortelės** — už jų jokios funkcionalybės nėra.
- Karštosios linijos numeris yra placeholderis: `tel:+37060000000`, su prierašu
  „(ne svarbu, neskambinti)“.

## 5. Šakos

| Šaka | Būsena / turinys |
| --- | --- |
| `main` | `b3f1915` — storefront + pagalbos sekcija, parduotuvė sustabdyta |
| `copilot/labas` | Tas pats kaip `main` (nieko papildomo) |
| `cline/f6ggtezn` | +2 commit (2026-10-25): `papildymas.html`, `papildymas.js`, `Bite-papildymas.url`, `styles.css` +219 eil., nuoroda navigacijoje. **Nesujungta į `main`** |
| `cline/ejzcxn55` | 2026-10-22…24 sesijų darbai: remote-access (SSH + Cloudflare tunelis, PowerShell agentas, relay), IVR sistema, n8n stebėjimas, F11 frazių rotacija, aukciono stebėjimas, `ivr.py`, `faq.json`, ataskaitos. **Nesujungta į `main`** |
| `cline/mfhpse71` | Šios sesijos darbo šaka (šis failas + `02_DIENORASTIS.md`) |

## 6. Ką daryti toliau (prioritetai)

1. **Sujungti Bitė papildymo puslapį** (`cline/f6ggtezn` → `main`) ir patikrinti, kad
   `papildymas.html` + `papildymas.js` + `styles.css` papildymai veikia.
2. **Nuspręsti dėl `STORE_PAUSED`** — jei derinimas baigtas, nustatyti `false` ir pašalinti
   `paused-banner` iš `index.html`; jei ne — palikti ir įrašyti priežastį dienoraštyje.
3. **Pagalbos 24/7 sekcija** — „Robotukas“ ir „Gyvas žmogus“ šiuo metu neveikia; reikia
   nuspręsti, ar jungiama prie tikro kanalo (n8n / IVR iš `cline/ejzcxn55`), ar paliekama
   kaip informacinė.
4. **Karštosios linijos numeris** — pakeisti placeholderį tikru numeriu (arba visai
   išimti „Skambinti“ mygtuką).
5. **Techninės skolos `app.js`:**
   - `getAvailableStock()` aprašyta, bet **nenaudojama** — `renderProducts()` rodo
     `product.stock`, o ne likutį atėmus krepšelyje esantį kiekį.
   - Produkto mygtukas generuoja ir `class="product-btn disabled"`, ir `disabled`
     atributą (dubliavimas).
6. **Checkout** — demo režimas be backend'o; jei reikia tikro užsakymo, jungti prie API.

## 7. Kaip tęsiama

1. `git checkout -b cline/<sesijos-id>` (niekada ne į `main` tiesiogiai)
2. Darbai → commit su aiškiu pranešimu → `git push -u origin cline/<sesijos-id>`
3. Sesijos pabaigoje papildyti `02_DIENORASTIS.md`

---

## 8. Aplinkos žemėlapis (Windows pusė, atkurtas iš 2026-10-25 likučių)

Šie duomenys surinkti iš vartotojo atsiųsto PowerShell sesijos išrašo ir iššifruotų
base64 skriptų (`swiss.ps1`, `_fix_swiss.py`). **Tai ne repo dalis** — tai tavo kompiuterio
`C:\Users\M\CLINE\` infrastruktūra.

### 8.1 Vietiniai servisai / portai

| Portas | Pavadinimas | Paskirtis |
| --- | --- | --- |
| 5678 | n8n | workflow automatizavimas |
| 8099 | narsykle | naršyklės servisas |
| 8766 | F6 | dainų API (`/api/list`) |
| 8091 | ZVERIS | (be aprašo) |
| 8090 | tools | (be aprašo) |
| 8790 | PULTAS | valdymo pultas (`http://127.0.0.1:8790`) |
| 9222 | chrome CDP | Chrome DevTools protokolas (automatizavimas) |

### 8.2 Pagrindiniai keliai

| Kelias | Turinys |
| --- | --- |
| `C:\Users\M\CLINE\00_START_HERE.md`, `02_DIENORASTIS.md`, `04_TODO.md` | tęstinumo dokumentai |
| `C:\Users\M\CLINE\tools\` | `swiss.ps1`, `sesijos-pradzia.ps1`, `auto-backup.ps1`, `backup_vps.py`, `_fix_swiss.py` |
| `C:\Users\M\CLINE\pultas\` | `pultas.py`, `start-pultas.cmd` → :8790 |
| `C:\Users\M\CLINE\ssh\` | `vps_cline` (privatus raktas), `known_hosts` |
| `C:\Users\M\CLINE\BACKUPS\`, `BACKUPS_VPS\` | vietinės ir VPS kopijos |
| `C:\Users\M\CLINE\SVEICARISKAS_LOG.txt` | sveikatos patikros žurnalas |
| `C:\Users\M\CLINE\swiss-out.txt`, `swiss-err.txt` | paleidimo išvestis |
| `C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe` / `pythonw.exe` | Python 3.12 |

### 8.3 `swiss.ps1` („SVEICARISKAS LAIKRODIS“) ką daro

Vienas paleidimas (autostart metu arba rankiniu būdu) ir viskas susitvarko pats:

1. paleidžia servisus per `tools\sesijos-pradzia.ps1`
2. jei :8790 neklauso → paleidžia `pultas.py` (paslėptas langas), laukia 6 s
3. jei `BACKUPS\` senesni nei 20 h → paleidžia `auto-backup.ps1`
4. jei `BACKUPS_VPS\` senesni nei 20 h → paleidžia `backup_vps.py`
5. visiems `CLINE*` planuotojo darbams nustato `StartWhenAvailable` ir kt.
6. per SSH tikrina VPS servisus (`hostname`, `aukcionas`, `vilko-mokykla`,
   `cloudflared-penktadienio`) — po `_fix_swiss.py` pataisymo
7. suvestinė: kiek servisų veikia (iš 6), svetainės statusas, laisva `C:` vieta
8. log'ą apkerpa, jei > 1 MB (palieka 800 eilučių)

### 8.4 Autostartas ir planuotojas

- `%APPDATA%\...\Startup\CLINE-PULTAS.lnk` → `cmd /c start-pultas.cmd` (langas paslėptas)
- `%APPDATA%\...\Startup\CLINE-SVEICARISKAS.lnk` → `powershell -File tools\swiss.ps1 -Quiet`
- Planuotojo darbai pavadinimu `CLINE*` (vienas iš jų — `CLINE Sveicarisko startas`, paleidimas
  `AtLogOn`)
- Nuotolinė prieiga: `cline-agent.ps1` (PowerShell HTTP agentas, :8787) + `cloudflared` tunelis;
  agentas generuoja atsitiktinį 28 simbolių `TOKEN` ir reikalauja `X-Token` antraštės

### 8.5 VPS

- `root@5.175.171.113`
- systemd servisai: `aukcionas`, `vilko-mokykla`, `cloudflared-penktadienio`
- svetainė: `https://penktadienioaukcionas.lt/`

---

## 9. ⚠️ SAUGUMO PROBLEMA — viešai nutekėjęs VPS root slaptažodis

### 9.1 Ką radau (patvirtinta komandomis, 2026-10-25)

| Patikra | Rezultatas |
| --- | --- |
| `gh repo view mindaugasbusiness-hub/novashop --json visibility` | `{"isPrivate": false, "visibility": "PUBLIC"}` |
| `git grep -l '<AUKC_PW reikšmė>' origin/cline/ejzcxn55` | **3 failai**: `.aukc_env`, `_ssh.py`, `__pycache__/_ssh.cpython-311.pyc` |
| `git log --all --oneline -- .aukc_env` | `1f40256` (2026-10-24) — jau nupushinta į GitHub |
| `git cat-file -e origin/main:.aukc_env` | neegzistuoja (nutekėjimas tik `cline/ejzcxn55` šakoje) |

Nutekėjęs turinys (esmė): `AUKC_HOST=5.175.171.113`, `AUKC_USER=root`, `AUKC_PW=***`
ir tas pats slaptažodis `_ssh.py` kode (`PWD = "***"`).

### 9.2 Poveikis

- **Viešas internetas turi `root` prieigą** prie tavo VPS per SSH su slaptažodžiu.
- VPS'e sukasi `aukcionas`, `vilko-mokykla`, `cloudflared-penktadienio` → galimas
  svetainės perėmimas, duomenų vagystė, šifravimas (ransomware), botneto naudojimas.
- Papildomai: `swiss.ps1` naudoja `StrictHostKeyChecking=no` (silpnina apsaugą nuo
  MITM), o privatus raktas `ssh\vps_cline` naudojamas be slaptažodžio (`BatchMode=yes`).

### 9.3 Ką daryti (prioritetų tvarka)

1. **Dabar:** VPS'e pakeisti root slaptažodį:
   `passwd root` (arba per `ssh-keygen` + `authorized_keys` ir tada
   `PasswordAuthentication no`).
2. **Dabar:** patikrinti, ar kas nors nesijungė:
   `last -a | head -30`, `grep -i 'Accepted password' /var/log/auth.log | tail -30`,
   `ss -tunp`, `systemctl list-units --failed`.
3. **Dabar:** peržiūrėti, ar VPS'e neatsirado svetimų raktų (`~/.ssh/authorized_keys`),
   cron'ų (`crontab -l`, `/etc/cron*`), servisų.
4. **Tada:** iš `cline/ejzcxn55` šakos pašalinti slaptažodį (`_ssh.py` → skaityti iš aplinkos
   kintamųjų; `.aukc_env` → pridėti į `.gitignore`; `__pycache__` → niekada necommit'inti).
   **Svarbu:** trynimas nepašalina slaptažodžio iš git istorijos — jis lieka visuose
   senuose commit'uose, tad slaptažodžio keitimas (1 punktas) yra privalomas.
5. **Tada:** apsvarstyti `novashop` repo pavertimą **privačiu** (tai vienu veiksmu uždengia
   visą istoriją) arba `cline/ejzcxn55` šakos istorijos perrašymą
   (`git filter-repo`) + nupushinimą su prievarta — **tam reikia tavo sprendimo**,
   nes tai naikina istoriją.
6. **Nuolat:** slaptažodžius laikyti tik `.env` / `ssh-agent` ir niekada necommit'inti;
   įjungti GitHub 2FA ir `secret scanning`.

### 9.4 Ko aš nepadariau ir kodėl

- **Nekeičiau VPS slaptažodžio** — neturiu (ir neturiu turėti) prieigos prie tavo VPS, o
  slaptažodžio keitimas yra tavo sprendimas.
- **Netryniau ir neperrašiau `cline/ejzcxn55` istorijos** — tai sunaikintų tavo duomenis;
  tam reikia tavo aiškaus sutikimo.
- **Nesijungiau prie 5.175.171.113**, kad „patikrinčiau, ar slaptažodis veikia“ — tai
  nereikalingas jungimasis prie svetimo serverio.

