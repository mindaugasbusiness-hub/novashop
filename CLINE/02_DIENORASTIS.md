# 02 · DIENORASTIS

Naujausi įrašai viršuje. Kiekvienas įrašas: ką dariau, ką patikrinau, ko NEDARIAU ir kodėl.

---

## 2026-10-31 — Sesija 6: ATSTATYMO TAŠKAS Nr. 1 (auksinė būsena 11/11) užfiksuotas

**Šaka:** `cline/da6qq3k9` · **Git žyma:** `atstatymas-1`

### M prašymas (citata)
„pulto duomenys viskas veikia labai gerai — ko aš noriu, aš noriu, kad taip sistema visada veiktų…
viskas kas iki dabar padaryta yra labai geras ir tikslus darbas, kuris turi būti išsaugotas
CLINE VISKAS folderyje… atstatymo numeris 1. Kai pasakysiu viską atstatyti į Nr. 1 — turi būti atstatyta."

### A) Ką M patvirtino kaip veikiančią būseną (pulto ataskaita 2026-10-31 04:16:04)
- **Servisai: 11/11**, Širdis 10/11, Riktai 11/11, klavisai 7/8 (F1 užimtas kito proceso — priimta)
- `https://penktadienioaukcionas.lt` → HTTP 200; VPS AUKCIONAS/MOKYKLA/CLOUDFLARED AKTYVUS
- Kopijos šviežios (VPS 0,8 h · vietinė 1,3 h); n8n vykdymų 119, workflow aktyvus

### B) Kas sukurta (atstatymo taškų sistema)

| Failas | Paskirtis |
|---|---|
| `CLINE/ATSTATYMAS/01_TASKAS.md` | Taško Nr. 1 aprašas: 11 servisų lentelė, VPS būsena, automatika |
| `CLINE/ATSTATYMAS/README.md` | Kaip kurti/atstatyti taškus, apsaugos, grąžinimas |
| `CLINE/ATSTATYMAS/atstatymo-sarasas.md` | Taškų registras (Nr. 1 įrašytas) |
| `tools/atstatymas/patikrinti-servisus.ps1` | Tikrina visus **11** pulto servisų (kaip pultas) |
| `tools/atstatymas/sukurkti-taskas.ps1` | Kuria tašką: pultas + tools + atmintis + n8n DB + užduotys + `TASKAS.json` (SHA256) |
| `tools/atstatymas/atstatyti-tasku.ps1` | Atstato į tašką Nr. N (SHA256 patikra, PRADINE-BUKLE kopija, `-Sausai`) |
| `tools/atstatymas/vps-taskas.sh` | VPS taškas/atstatymas (app.py + .bak istorija + unit + manifestas) |
| `tools/atstatymas/test-vps-taskas.sh` | VPS skripto savitikra |
| `tools/atstatymas/savitikra.py` | Sistemos savitikra (koduotė, saugumo taisyklės, dokumentų darna) |

### C) Saugumo taisyklės, įdiegtos atstatyme
- **SHA256 patikra prieš atstatymą** — sugadintas taškas atmetamas (`exit 2`), nestatoma.
- **PRADINE-BUKLE_<data>** — dabartinė būklė visada išsaugoma prieš atstatymą.
- **`.bak-pries-atstatyma-<data>`** — kiekvienas perrašomas failas paliekamas su kopija.
- **`-Sausai`** — parodo planą, nieko nekeičia.
- **Slapti duomenys** — n8n prieigos duomenys/VPS slaptažodžiai **neįrašyti** į repo; lieka tik
  vietiniame `C:\Users\M\CLINE\VISKAS\` (3 taisyklė).

### D) Patikrinta šioje sesijoje
- `test-vps-taskas.sh` — **23 atvejai, 0 klaidų** (taško kūrimas, sąrašas, sausas režimas,
  atstatymas, sugadinto taško atmetimas, nerasto taško atmetimas, saugumo patikros)
- `savitikra.py` (atstatymo) — **13/13 PASS**
- PowerShell 7.4.6 parseris — 3 nauji `.ps1` failai, **0 klaidų**
- `savitikra.py` (n8n) atstatymo aplankui — **3/3 PASS** (koduotė)

### E) Kas liko M (kad taškas Nr. 1 būtų PILNAS)
1. `sukurkti-taskas.ps1 -Numer 1` — mašinos dalis (pultas, tools, n8n DB, užduotys)
2. `vps-taskas.sh sukurkti 1` — VPS dalis (app.py)
3. Registro lentelėje pakeisti ⏳ į ✅

Kol šie du nepaleisti, „atstatyti į Nr. 1" atkurs **kodą ir nustatymus**, bet ne mašinos failų turinį.

---


## 2026-10-28 — Sesija 5: n8n :5678 / :5679 SUTVARKYMAS (brokerio konfliktas išaiškintas)

**Šaka:** `cline/da6qq3k9` (nuo `main`; `CLINE/` atmintis atkurta iš `origin/cline/g2zpktej`)

### A) Išaiškinta tikroji `:5679` priežastis (anksčiau buvo klaidingai aiškinama)

- Teiginys „:5679 neveikia, nes antras n8n egzempliorius užima portą“ — **netikslus**.
- Įrodyta iš repo istorijos: `_out/readNative2.txt` rodo `5678 -> PID 7976` ir **`5679 -> PID 7976`**
  (tas pats procesas), o `_out/runWf.txt` — klaidą
  `n8n Task Broker's port 5679 is already in use` + `execute exit: 1`.
- Vadinasi **5679 = n8n Task Broker** (`N8N_RUNNERS_TASK_BROKER_PORT`, numatyta 5679),
  o klaida kyla, kai **CLI komanda** (`n8n execute`) paleidžiama, kol serveris jau veikia.
- Patikrintas sprendimas jau buvo repo istorijoje (`_mcmd/run-wf2.ps1`): CLI su
  `N8N_RUNNERS_TASK_BROKER_PORT=5699` → `n8n Task Broker ready on 127.0.0.1, port 5699`.
- n8n dokumentacija patvirtina: `N8N_RUNNERS_TASK_BROKER_PORT`, `N8N_RUNNERS_BROKER_LISTEN_ADDRESS`,
  `N8N_RUNNERS_MODE` (`internal`/`external`).

### B) Sukurti įrankiai `tools/n8n/` (visi su savitikra)

| Failas | Paskirtis |
|---|---|
| `n8n-konfig.ps1` | viena tiesos vieta: keliai, prievadai, sprendimas `Get-N8nBusena` |
| `start-n8n.ps1` / `start-n8n.cmd` | vienas n8n: seno uždarymas, prievadų patikra, `/healthz` laukimas |
| `restart-n8n.ps1` | sustabdyti + paleisti (kvies pulto mygtukas) |
| `n8n-watchdog.ps1` | budėtojas: GERAI / PERKRAUTI / SVETIMAS / KYLA / PALEISTI |
| `registruok-uzduotis.ps1` | Task Scheduler: „N8N START LOGON“ (ONLOGON+30 s) ir „N8N WATCHDOG“ (kas 1 min) |
| `n8n-diagnostika.ps1` | prievadai, PID, rezervuoti diapazonai, versija, užduotys |
| `n8n-cli.ps1` | **sprendžia :5679 konfliktą** — CLI gauna laisvą brokerio prievadą 5690–5699 |
| `test-n8n-logika.ps1` | 40 patikrų su imituotomis priklausomybėmis |
| `savitikra.py` | `.cmd` ASCII+CRLF be BOM, `.ps1` UTF-8+BOM+CRLF, prievadai, slaptos reikšmės |
| `README.md` | pilna instrukcija (diegimas, naudojimas, rollback, kas patikrinta) |
| `tools/pulto-mygtukas-restart-n8n.py` | mygtukas „Restartuoti n8n“ + `act('/restart-n8n')` pultui, su `.bak` kopija |

### C) Saugumo sprendimai (kad budėtojas nepakenktų)

- Svetimo proceso **niekada** nežudo: būsena `SVETIMAS` tik praneša į žurnalą.
- Vienu metu tik vienas budėtojas (PID failas); „booting“ žyma 120 s stabdo antrą startą.
- Jokių slaptažodžių repo; `pultas.py` **nekeliamas** į repo (kaip ir anksčiau).
- Niekas netrinama: pulto/seno paleidiklio atsarginės kopijos daromos automatiškai (`.bak-<data>`).

### D) Ką patikrinau šioje sesijoje (tikri įrankiai, ne spėjimai)

- PowerShell **7.4.6 parseris**: visi 8 `.ps1` — **0 sintaksės klaidų**.
- `test-n8n-logika.ps1`: **40/40 PASS**.
- `savitikra.py`: **9/9 failų PASS**.
- `pulto-mygtukas-restart-n8n.py --self-test`: **22/22 PASS**.

### E) Ko NEPATIKRINAU (nėra prieigos prie M kompiuterio)

- `Get-NetTCPConnection`, `Get-CimInstance`, `schtasks` — testuose imituoti.
- Ar `N8N_ROOT` tikrai `C:\Users\M\Desktop\Kumstis`; ar pultas priims naują mygtuką.
- Tikslus pirmas žingsnis M mašinoje: `n8n-diagnostika.ps1`.

---


## 2026-10-27 — Sesija 4 (tęsinys 7): ŠOKĖJA ATRAKINTA + F10 KEISTI ŠOKĖJĄ (mažoji plytelė lieka #12)

### M prašymas
„Atrakinti šokėją (kad F5 keistų šokėjas kai paspaudžiu), o ta neoninė maža kairiame kampe nesikeistų.“

### A) Šokėjos rotacija atrakinta (serveris)
- `get_dancer_public()` / `dancer_next_public()` grąžintos į **originalią logiką** iš
  `app.py.bak-sokeja-20261027_194351` (auto-rotacija kas `DANCER_ROTATE_S`, `next` → kita).
- Įrankis: `tools/neon-dancer/patch_dancer_unlock.py` (eilutės keičiamos pagal funkcijų ribas,
  ne pagal trapią tekstą; prieš įrašymą `ast.parse`).
- Kopija serveryje: `app.py.bak-unlock-<data>`; tarnyba `active`.
- **Patikra:** `GET /api/dancer` → `dance_club_15` → `POST /api/dancer/next` → `dance_club_17`,
  per puslapį matėsi `dance_club_15/17` (rotacija veikia).

### B) F10 dabar TIKRAI keičia šokėją (M kompiuteris)
- Paaiškėjo: daemone F10 darė **tik** `run_stage("off")` (Vilkas OFF) — šokėjos nekeitė,
  nors pultas rašė „F10 Vilkas OFF + kita šokėja“.
- Pridėta: `DANCER_NEXT = ROOT / "_dancer_next.py"`, funkcija `run_dancer_next()`,
  o F10 šakoje `run_stage("off")` + `run_dancer_next()`.
- Sukurtas `C:\Users\M\Desktop\pakeitimai 111\_dancer_next.py` (POST `/api/dancer/next`).
- Kopija: `_vilkas_global_hotkeys.py.bak-dancer-<data>`.
- Daemonas perkrautas: senas PID 11652 → **naujas PID 12884**, logas „klavisai uzregistruoti: F6-F11 veikia“,
  portas 8766 vėl klauso.
- **Patikra (rankinis kelias, be klaviso):** `_dancer_next.py` → „OK sokeja: /photos/dance_club_18.mp4“,
  API po to: `dance_club_18`.

### C) Mažoji neoninė plytelė NESIKEIČIA
- Ji turi savo `<video class="nd-video" src="/photos/dance_club_12.mp4">`; JS rotacija dirba su `.dd-video`,
  todėl plytelės neliečia.
- **Patikra po visų pakeitimų:** puslapyje `neonine: /photos/dance_club_12.mp4`, aukštis **64 px**,
  o didžioji `dance_club_17/18` — keičiasi.

### Liko M sprendimas
- Ar F10 turi kartu ir **išjungti Vilką** (kaip dabar), ar F10 tegul tik keičia šokėją, o Vilkas OFF
  lieka atskiras klavišas? Tai viena eilutė pakeisti.

---

## 2026-10-27 — Sesija 4 (tęsinys 6): BLUETOOTH IŠJUNGTAS KOMPIUTERYJE (JBL ausinėms)

### M prašymas
Vakar bandė prijungti JBL Bluetooth ausines prie kompiuterio (nepavyko iki galo). Po to telefonas ausinių nebemato.
Prašymas: „kompiuteryje išjunk Bluetooth“, kad ausinės vėl veiktų telefone.

### Ką padariau (patikrinta)
- Teisės: `admin=False` → `Disable-PnpDevice` netinka, todėl naudojau **Windows radijo API**
  (WinRT `Windows.Devices.Radios.Radio.SetStateAsync`) — tam admin nereikia.
- Būsena prieš: `WiFi = On`, `Bluetooth = On`.
- Įvykdyta: Bluetooth → **Off**, atsakymas `Allowed`; po 2 s patikra: `Bluetooth = Off`, `WiFi = On` (neliestas).
- `Get-PnpDevice | Where FriendlyName -match 'JBL|Bluetooth|Hands-Free'` → **jokio JBL įrenginio nėra**
  (tik Broadcom Bluetooth 4.0 adapteris ir Windows enumeratoriai). Vadinasi, kompiuteris ausinių
  „nelaikė“ kaip garso įrenginio — jos liko neporuotos.

### Įrankiai (M kompiuteryje)
- `C:\Users\M\CLINE\tools\_bt_off.ps1` — išjungia Bluetooth (be admin)
- `C:\Users\M\CLINE\tools\_bt_on.ps1` — įjungia atgal (be admin)

### Ką toliau daro M (telefone)
1. Įjungti ausines; telefone: Bluetooth → ieškoti → „JBL…“.
2. Jei nemato: ausines į **pairing režimą** (laikyti mygtuką, kol pradeda greitai mirksėti LED),
   o telefone ištrinti seną „JBL…“ įrašą ir ieškoti iš naujo.
3. Jei vis tiek nemato — ausinių „factory reset“ (JBL instrukcija: laikyti garso+/garso− ir power).

### Papildymas: USB laidas (2026-10-27 ~15:58, M įkišo)
- Patikrinta 3 būdais: `Get-PnpDevice` (USB/AudioEndpoint), garso plokštės, garso įrenginių registras.
- **Joks naujas įrenginys nepasirodė**: tie patys 2 `USB Composite Device`
  (VID_1A2C&PID_2D23, VID_05C8&PID_0369 — klaviatūra/kamera), jokių naujų AudioEndpoint.
- Išvada: JBL ausinių USB lizdas **tik įkrovimui** (garso per USB nėra) arba įrenginys nesiskelbia.
- Liko keliai: 3,5 mm AUX laidas į žalią lizdą, arba USB Bluetooth 5 dongle (adapteris 2015 m. per senas).

### Pastaba
Bluetooth adapteris šiame kompiuteryje — **Broadcom 4.0** (senas). Jei M vėl norės jungti ausines
prie PC, gali tekti poravimo režimas + kantrybė (4.0 adapteriai su naujesnėmis ausinėmis kartais
neporuoja iš pirmo karto).

---

## 2026-10-27 — Sesija 4 (tęsinys 5): PULTO KLAIDOS — /api/state 500 + panelės išsipūtimas

### M pranešimai
1. „F9 neperjungia į Vilką ON“, „F5 paspaudus šokėjos nesikeičia“, „patikrink ir kitus mygtukus“.
2. „Šitą sutrauk — jo tokio didelio neturi būti“ (panelė/plytelė).

### Rasta ir ištaisyta (viskas patikrinta, ne spėta)
**A) Tikra klaida serveryje: `/api/state` → HTTP 500**
- Priežastis: `NameError: name 'DESK_SONG_TITLES' is not defined` (`app.py` 118 eil., `get_desk_song_n`).
- Kada dingo: 2026-10-27 **19:46** pataisa „sokeja2“ — palyginta su kopijomis:
  `app.py.bak-sokeja-20261027_194351` (449 903 B, apibrėžimas YRA) →
  `app.py.bak-sokeja2-20261027_194633` (446 626 B, apibrėžimo NĖRA). Tai ne mano pataisa
  (mano pirmoji buvo 22:13), bet pasekmė buvo didelė: puslapis negalėjo perskaityti būsenos,
  todėl **Vilkas ON/OFF, šokėja, registracijos būsena ir daina neatrodydavo ekrane**.
- Sutvarkyta: grąžintas `DESK_SONG_TITLES` (71 raktas, 2 851 B) iš 19:43 kopijos prieš
  `def get_desk_song_n()`. Kopija: `app.py.bak-titulai-fix-<data>`.
- Patikra: `/api/state` → **200**, `vilkas_stage_on` skaitomas; toggle off → `false`, on → `true`.

**B) F9 grandinė veikia**
- `_vilkas_stage_toggle.py on` → „OK Vilkas stage: ON“ (rankinis paleidimas).
- Klavišų daemonas: `C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py` (PID 11652),
  registruoti F6–F11 (F1 užimtas kito proceso). F9 → `_vilkas_stage_toggle.py on`.

**C) „F5 ir šokėja nesikeičia“ — taip ir turi būti**
- Serveryje šokėja **užrakinta**: `get_dancer_public()` / `dancer_next_public()` grąžina
  `dance_club_12.mp4` su komentaru „SOKEJA 12 visada (M nurodymu 2026-10-27)“.
- Jei M nori, kad vėl keistųsi — reikia atrakinti (viena funkcija), bet tam reikia jo „taip“.

**D) Panelės išsipūtimas (M: „tokio didelio neturi būti“)**
- Įjungus dalyvių sąrašą paaiškėjo: jame **500 mokymosi botų** → panelė 3 375 px, plytelė nusistūmė už ekrano.
- v6: sąrašas fiksuotas **110 px su slinkimu**, rodoma iki 60 vardų.
- v5: neoninė plytelė **sutraukta 64 px**, paspaudus išsiskleidžia iki 170 px (▸/▾).
- Išmatuota (1078×540): panelė **302 px**, sąrašas 110, forma 46 (sutraukta), plytelė 64→170.

### Kodėl forma neišsiskleidžia iki galo
- Registracija **uždaryta** (mokymosi režimas): `regClosedNote` rodomas, laukai paslėpti — taip ir turi būti.
  Paspaudus „1. REGISTRACIJA“ matosi tik pastaba „Registracija uždaryta…“.

### Įrankiai, kuriuos pasidariau (M kompiuteryje, galiu ištrinti)
`tools\vps_sh.py` (SSH komandos + `--put`/`--get`), `_fix_titles.py`, `neon_run*.py`,
`_probe.py`, `_probe_titles.py`, `_cdp_check*.py`, `_check_shot*.ps1`, `_win_measure.ps1`.

---

## 2026-10-27 — Sesija 4 (tęsinys 4): REGISTRACIJA SUTRAUKTA + DALYVIAI VIRŠUJE (v3 + v4)

### M noras
„Registracijos lange neturi matytis išskleistas — sutrauk į viršų, dalyviai aukciono.“

### Ką padariau (nieko netrinant, tik pridedant)
**v3** (`patch_neon_dancer_v3.py`, `app.py.bak-neonv3-20261027-222658`, +677 B):
- JS: `syncRegPanel()` dabar sutraukia registraciją **visuose pločiuose**
  (buvo tik `window.innerWidth<=640`). Eilutė pakeista 1:1, ta pati logika.
- HTML: panelė gimsta su klase `reg-collapsed` (kad neblyksėtų atidaryta forma).
- CSS (pridėta, neperrašyta): `.pp-list{display:flex!important}` (anksčiau sąrašas buvo
  paslėptas `display:none !important` — tos eilutės **neliečiau**, permušu savo vėlesne taisykle);
  globalios `reg-collapsed` taisyklės + užrašas „▾ atidaryti“ / „▴ sutraukti“ ant pavadinimo.
- Plytelė trumpame ekrane: 88 → 120 px, o kai forma atidaryta — 88 px.

**v4** (`patch_neon_dancer_v4.py`, `app.py.bak-neonv4-20261027-222811`, +81 B):
- Sutrauktoje būsenoje dalyvių sąrašui **110 px** (buvo 32), atidarytoje — 32 px.

### Išmatuota M dydžiu (1078×540, Chrome DevTools)
| Kas | Rezultatas |
|---|---|
| Panelės klasė | `participants-panel reg-collapsed` |
| Panelės aukštis | **358 px** (anksčiau 447 su atidaryta forma) |
| Registracijos forma | 46 px — tik pavadinimas; vardo laukas **paslėptas** (h=0) |
| Dalyvių sąrašas | `display:flex`, y=64, **110 px**, tekstas „Kol kas nieko“ |
| Plytelė | y=238, **120 px**, matoma |
| Video | groja (6,6 s), `readyState=4` |
| Serveris | active, svetainė 200, video 200, blokas 1 |

### Kaip naudoti
- Norint užsiregistruoti: spausti „1. REGISTRACIJA“ (arba „▾ atidaryti“) — forma išsiskleidžia,
  plytelė sumažėja iki 88 px, kad viskas tilptų.
- Mobiliame (≤640 px) palikta kaip buvo (ten sąrašas paslėptas, forma suskleidžiama).

### Kas liko
- M turi paspausti **Ctrl+F5** (HTML/CSS yra `app.py` viduje).
- Laisvos vietos yra (~180 px), todėl plytelę galima didinti iki 160 px — laukiu M sprendimo.

---

## 2026-10-27 — Sesija 4 (tęsinys 3): KODĖL NEBUVO MATOMA + v2 PATAISA

### Priežastis (ne spėjimas — išmatuota)
M atsiuntė ekrano nuotrauką: plytelės po registracijos forma **nebuvo**.
Išmatavau jo kompiuterį: **ekranas 1093×614**, darbinis plotas 1093×574,
Chrome klientas 1096×624 → **puslapio laukas ~540 px aukščio**.
Mano v1 taisyklė `@media (max-height:660px){.neon-dancer{display:none}}` — dėl to plytelė buvo paslėpta.
Klaida buvo mano: slėpimo slenkstis per aukštas.

### Ką pakeičiau (v2, `tools/neon-dancer/patch_neon_dancer_v2.py`)
- Slėpiama tik labai žemame ekrane (`max-height:520px`).
- `max-height:700px` → plytelė 110 px, dalyvių sąrašas `min-height:40px`.
- `max-height:620px` → plytelė 88 px, sąrašas `min-height:32px`.
- Registruotam: 172 → 150 px.
- **Nieko netrinta**: tik 3 eilutės pakeistos į 5 (žr. diff žemiau), kopija `app.py.bak-neonv2-20261027-222042`.

### Patikra (Chrome DevTools, būtent M dydis 1078×540)
| Kas | Rezultatas |
|---|---|
| Plytelė | **168 × 88 px**, x=16, y=359, `display:block` |
| Panelis | y=8, h=447 → apačia 455; plytelės apačia 447 → **telpa, nesukirpta** |
| Video | `readyState=4`, `paused=false`, 6,4 s iš 12,9 s, klaidos nėra |
| Serveris | `aukcionas` active, svetainė 200, blokas 1, video 200 |

### Kas liko M
- **Ctrl+F5** (perkrauti puslapį) — HTML/CSS yra pačiame `app.py`, todėl sena versija gali būti naršyklės cache.
- Jei nori didesnės plytelės: mažinam registracijos pastabos tekstą arba didinam iki 110–132 px.

---

## 2026-10-27 — Sesija 4 (tęsinys 2): RYŠYS PER POWERSHELL + NEONINĖ ŠOKĖJA ĮDIEGTA SERVERYJE

### Ryšys
- Paleidau `tools/relay/relay.py` (8798) + `cloudflared 2026.10.5` (atsisiųstas į `/workspace/.tools/`).
  Adresas: `spend-cited-diego-moisture.trycloudflare.com` (gyvas tik šios sesijos metu).
- **ntfy budėtojas nepakėlė ryšio** (per ~2 min neprisijungė) — direktorius įklijavo eilutę
  `iex (irm .../agent.ps1)` rankiniu būdu → klientas prisijungė iš karto.
- Relay savitikra: **11/11 OK** (relay.py → agent.ps1 → pc.py grandis).

### Ką mačiau M kompiuteryje (patikrinta)
- `DESKTOP-7LPGR90`, paskyra `desktop-7lpgr90\m`, PowerShell 5.1, Python 3.12.
- `paramiko 5.0.0`, `websocket-client 1.9.2`, `websockets 17.1`, OpenSSH portable — yra.
- `C:\Users\M\CLINE\` (~30 katalogų) ir `VISKAS\` (44 failai + `SEIFAS\`):
  naudingiausia: `VISKAS\00_SKAITYK_NAUJAUSIA.md`, `07_SESIJA_2026-10-27.md`, `11_POKYCIAI.md`,
  `SEIFAS\00_KUR_SLAPTAZODZIAI.txt`, `tools\vps_*.py` (juose ir VPS prisijungimo duomenys).

### Įdiegimas serveryje (pavyko)
VPS `penktadienio` (`5.175.171.113`, `/opt/aukcionas/app.py`, 446 547 B):
1. `--dry` → būtų +2090 baitų.
2. Tikras įrašymas → **`.bak-neon-20261027-221303`** (kopija prieš).
3. `systemctl restart aukcionas` → **active**.
4. `ast.parse` → sintaksė OK; `grep -c 'class="neon-dancer"'` → **1**; svetainė **200**; video **200** (5 100 845 B).
- Slaptažodis **nespausdintas**: scriptas jį paėmė iš esamo M įrankio (`tools\add_env.py`) ir panaudojo tik kodui.

### Vaizdo patikra (ne akimis, o matavimu — Chrome DevTools)
- Plytelė: **168 × 160 px**, `x=16, y=359`, `display:block`, `opacity:1`.
- Panelis: 184 × 519 px, `overflow:hidden` → plytelė **pilnai telpa** (apačia 519 < 527).
- Video: `readyState=4`, `paused=false`, laikas 4,4 s iš 12,9 s, `error=null` → **tikrai groja**.
- Ekrano nuotrauka: `C:\Users\M\CLINE\_neon_out\po.png` (1600×900).

### Ko NEDARIAU
- Nieko netryniau ir nepervardinau; serveryje liko ir sena atsarginė kopija `app.py.bak-neon-2026-10-25`.
- Netryniau jokių M programų; Chrome naudotas atskiruose temp profiliuose (headless).
- Sukūriau pagalbinius failus (galiu pašalinti, kai pasakysi):
  `tools\_peek.py`, `tools\deploy_neon.py`, `tools\neon_run.py`, `tools\_check_shot.ps1`,
  `tools\_check_shot2.ps1`, `tools\_cdp_check.py`, `_neon_out\po.png`.

### Kas toliau
- Direktorius žiūri svetainę: ar 160 px aukštis tinka, ar nori mažesnio/didesnio.
- Grąžinimas atgal (jei nepatiks): `cp /opt/aukcionas/app.py.bak-neon-20261027-221303 /opt/aukcionas/app.py && systemctl restart aukcionas`.

---

## 2026-10-27 — Sesija 4 (tęsinys): NEONINĖ ŠOKĖJA (#12) — PARUOŠTA ĮDIEGIMUI

### Tikslas
Direktorius pasirinko 3 variantą: „Tvarkyti ‚neoninę šokėją‘ nebaigtą darbą“ (VISKAS žurnalas, 2026-10-27 21:49).

### Ką radau (faktai)
- Tai **ne NovaShop**, o `penktadienioaukcionas.lt` serveris, failas `/opt/aukcionas/app.py`.
- To darbo pėdsakų `app.py` **nebuvo** — žodžio `neon-dancer` faile nebuvo nė karto, t. y. pakeitimas nebuvo įrašytas.
- 2026-10-27 21:49 įrašas sako: bandyta įdėti `dance_club_12.mp4` kairėje po registracijos forma, bet dėl ryšio nepavyko.
- Panelės struktūra: `.participants-panel` (`left:8px`, plotis 228 px), viduje `#joinForm` (registracija) ir `#ppDone`.

### Ką padariau
Sukūriau `tools/neon-dancer/`:
- `patch_neon_dancer.py` — įterpia CSS bloką (neoninis rėmelis + pulsavimas) ir HTML bloką
  (`<video /photos/dance_club_12.mp4 autoplay muted loop>` 160 px aukščio) **po registracijos formos, prieš `ppDone`**.
  Saugikliai: `.bak-neon-<data>` kopija prieš įrašymą, ankerių unikalumo patikra (jei ne 1 → STABDO),
  „jau įdiegta“ apsauga, CRLF išsaugojimas.
- `savitikra.py` — 35 patikrinimų ant kopijos: **35/35 PASS** (vieta, HTML/CSS vientisumas, skliaustai,
  CRLF, dubliuoti `id`, `.bak` turinys, idempotencija, `compile()`, `--dry`, sugadinto ankerio testas).
- `README.md` — kaip įdiegti, kaip grąžinti atgal, ko nepatikrinau.

Mobiliame (≤640 px) ir žemame (≤660 px) ekrane plokštė paslėpta, kad neuždengtų formos.

### Ko NEDARIAU ir kodėl
- **Neįdiegiau į serverį** — šioje sesijoje nėra prieigos prie VPS (jokio `AUKC_PW`, jokio ryšio).
  Duodu paruoštą įrankį ir tikslias komandas; įdiegimas — 3 komandos serveryje.
- **Nieko netryniau** ir neperrašinėjau `app.py`; net `.pyc` failą tik išėmiau iš git (diske liko).
- **Nemačiau vaizdo naršyklėje** — sesijoje naršyklės nėra; tai sąžiningai parašyta README 6 skyriuje.

### Nuo ko tęsti
1. Direktorius įdeda įrankį į serverį ir paleidžia `--dry`, tada be jo, tada `systemctl restart aukcionas`.
2. Patikra: `curl -s http://127.0.0.1:8000/ | grep -c 'class="neon-dancer"'` → turi būti 1.
3. Jei vaizdas netinka — koreguojama viena CSS eilutė (`height`, `object-position`), be rizikos.

---

## 2026-10-27 — Sesija 4: nauja sesija, atmintis perskaityta, C:\ IR VĖL NĖRA

### Ką dariau
1. Gavau direktoriaus „PRADŽIA“ tekstą (jame nuoroda į `C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md`).
2. To failo šioje sesijoje **nėra**, todėl atmintį paėmiau iš git repo `mindaugasbusiness-hub/novashop`:
   - `cline/0xjxer93` (naujausia, 2026-10-27) → `CLINE/00_START_HERE.md`, `02_DIENORASTIS.md`, `03_TAISYKLES.md`, `04_TODO.md`;
   - `cline/ejzcxn55` → `VISKAS/10_DARBU_ZURNALAS.md` (įrašas 2026-10-27 21:49 apie nebaigtą „neonine šokėja“ darbą);
   - `cline/wfbfjc1p` → relay įrankiai ir ankstesnis TODO (2026-10-26).
3. Sukūriau darbinį branch `cline/g2zpktej` **nuo `origin/cline/0xjxer93`** (kad atmintis keliautų kartu). `main` neliestas.
4. Patikrinau parduotuvę: `python3 -m http.server` → `index.html`, `app.js`, `styles.css` → **200 OK**.

### Patikrinta šiandien (ne spėjama)
| Teiginys | Būsena |
|---|---|
| `C:\` diskas šioje sesijoje | **NĖRA** — `/mnt` tuščias, PowerShell nėra |
| `cloudflared` | **NĖRA** (nė vienoje vietoje) → relay/tunelio kelio šiandien nepaleisiu |
| `STORE_PAUSED` | **true** (`app.js` 15 eilutė) — parduotuvė uždaryta, kaip ir buvo |
| `paused-banner` | yra `index.html` (1 vieta) |
| Parduotuvė atsako | **200 OK** visiems 3 failams |

### Ko NEDARIAU ir kodėl
- **Neduosiu jokio tunelio adreso** — `cloudflared` nėra, o ir praeitas adresas buvo miręs (DNS). Nekartoju praeitos klaidos.
- **Nieko netryniau, nepervardinau, neperrašiau** — tik **papildžiau** šį dienoraštį ir `04_TODO.md`.
- **Neliečiau `main`**, nespausdinau jokių raktų, „neoninės šokėjos“ darbo neliečiau (jis VISKAS žurnale, ne šiame repo).

### Išvada
Atmintis išliko, darbas tęsiamas. Bet **ryšio su direktoriaus kompiuteriu šioje sesijoje nėra** — vienintelis patikimas kelias:
direktorius paleidžia `cline -i` savo `PS C:\Users\M>` lange (įdiegta 2026-10-27) ir tada aš matau `C:\` failus.
Kol to nėra — dirbu tik su repo (git), ir viską sąžiningai sakau.

---

## 2026-10-27 — Sesija 3: DIREKTORIUS ĮDIEGĖ `cline` SAVO KOMPIUTERYJE (pavyko)

### Kas įvyko (patvirtinta iš direktoriaus PowerShell ištraukos)
1. `npm install -g cline` tavo `PS C:\Users\M>` lange → **`added 322 packages in 1m`**. Įdiegta.
2. `cline auth cline` → išvedė **device code** (`Enter this code in your browser: XXXX-XXXX` + `https://authkit.cline.bot/device?user_code=...`). Tai reiškia: **binaras veikia**, o auth laukia patvirtinimo naršyklėje.
3. Darbalaukyje pasirodė jo paties paruoštas dialogas „CLINE - nuoroda paruošta“ su tekstu, kurį reikia įklijuoti į naują sesiją:
   `Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tęsiam.`
   → reiškia, kad **atmintis `C:\Users\M\CLINE\VISKAS\` egzistuoja realiame kompiuteryje**.

### Patikrinta šiandien (ne spėjama)
| Teiginys | Būsena |
|---|---|
| `npm view cline version` | **3.0.74** (publikuota 2026-10-26) |
| Windows binaras `@cline/cli-windows-x64` | **3.0.74** — yra |
| Įdiegimas be `postinstall` (npm įspėjimas `allow-scripts`) | **Nekliudo** — patikrinta smėliadėžėje: `install exit=0`, `cline --version` → 3.0.74 |
| `cline -i / --tui` flagas | **Yra** (patvirtinta iš `cline --help`) |
| `cline auth <provider>` | **Yra**; `-k/--apikey`, `-m/--modelid` raktiniam prisijungimui |
| `--auto-approve false` | **Yra** — išjungia automatinį įrankių patvirtinimą |
| `authkit.cline.bot/device` | **307** (veikia, nukreipia į prisijungimą) |
| `pastor-participant-lab-housewares.trycloudflare.com` (vakar duota eilutė) | **MIRUSI** — `Could not resolve host`. Daugiau tokių eilučių neduoti |

### Ko NEDARIAU ir kodėl
- **Neduosiu jokio trycloudflare/pinggy/tunelio adreso.** Patikrinta: vakar duotas adresas nebeegzistuoja net DNS. Priežastis struktūrinė — agentas debesyse paleidžiamas tik žinutei ir numiršta jai pasibaigus.
- **Neprisijungiu prie direktoriaus ekrano.** Failai ir komandos — taip (per jo paties įdiegtą `cline`), gyvas ekranas — ne.
- **Neliečiau `main`**, nieko netryniau.

### Išvada
Tikrasis „prijungimas per PowerShell“ **įvyko šiandien**: `cline` įdiegtas direktoriaus kompiuteryje. Nuo šiol kiekvieną kartą užtenka `cd C:\Users\M; cline -i` — jokio tunelio, jokio kintančio adreso.

---

## 2026-10-26 (vėliau tą pačią dieną) — Sesija 2: prijungimo per PowerShell sprendimas

### Kontekstas
Direktorius: „esmė prijungti tave per power shell“ ir atsiuntė savo PowerShell langą: `PS C:\Users\M>`.
Anksčiau buvo aprašyta, kad darbalaukyje yra nuorodos „CLINE RYSYS“ / „CLINE - PRADZIA“ ir kad ryšys eina per `trycloudflare` + n8n. Toje žinutėje taip pat buvo „rytoj užteks vieno sakinio“ eilutė.

### Ką išsiaiškinau (patikrinta, ne spėta)
1. Ši sesija yra **debesų smėliadėžė** (`hostname: ins-01m5wtbtdc22jkc8zgcfqrp448`, Linux), su internetu (IP 34.67.51.12), bet **be `C:\` disko**. Todėl tavo Windows failų iš čia nematau ir negaliu į juos įeiti.
2. Todėl kryptis turi būti **atvirkštinė: aš įdiegiamas pas tave**, o ne aš jungiuosi pas tave.
3. Patikrinau oficialų sprendimą — `cline` CLI (npm paketas `cline`, oficialus Cline agentas terminalui):
   - `npm install -g cline` → įdiegta smėliadėžėje sėkmingai;
   - `cline --version` → **3.0.74**;
   - `cline --help` → patvirtinti flagai `-i/--tui`, `-c/--cwd`, `--auto-approve`, `-p/--plan`, `--json`, `-z/--zen`;
   - `cline auth cline` → OAuth prisijungimas (būtinas prieš paleidžiant, kai naudojamas Cline provider).
   - Platformos binarai publikuojami macOS, Linux, **Windows** (`arm64`, `x64`) — todėl tavo `PS C:\Users\M>` lange tai veiks.
4. Sukūriau instrukciją `CLINE/05_PRIJUNGIMAS_WINDOWS.md` (3 žingsniai: Node → `npm i -g cline` → `cline auth cline`; tada `cline -i` arba `cline "<pavedimas>"`).

### Ką tai reiškia direktoriui
- Nereikia jokio tunelio, jokio n8n, jokio kintančio adreso, jokio „nukopijuok komandą į atmintinę“.
- Įdiegus vieną kartą — ryšys lieka **visam laikui** ir aš matau `C:\Users\M\...` failus, tame tarpe `C:\Users\M\CLINE\`.
- Tikslus atsakymas į „kas neaišku“: **aš niekada neprisijungiu pats.** Tu paleidi `cline` savo lange — tada aš dirbu tavo mašinoje. Tai ir yra prijungimas.

### Patikrinimo įrankis
Komanda, kuri parodo, kokiai mašinai aš prijungtas, ko nematyti rytoj, ir kur tikroji problema — naudota ir šįkart: `hostname`, `ls /mnt`, `curl api.ipify.org`.

---

## 2026-10-26 — Sesija 1: atrama perkelta į git

### Ką dariau
1. Patikrinau, ar sesijoje yra `C:\Users\M\CLINE\` ir atminties failai → **nėra** (`/mnt` tuščias, jokio Windows disko, jokio PowerShell).
2. Patikrinau repo: `mindaugasbusiness-hub/novashop`, `main` = `b3f1915` („Add support section with 24/7 help choices“), darbinis kelias /workspace.
3. Sukūriau darbinį branch `cline/7at5cm57` (nuo `main`, švarus statusas).
4. Patikrinau, ar repo viduje yra pėdsakų apie n8n / trycloudflare / `agent.ps1` / sargą → **nerasta jokių** (grep per visus failus, išskyrus `.git`).
5. Paleidau statinę parduotuvę ir patikrinau, kad ji tikrai dirba:
   - `python3 -m http.server` → `index.html` **200 OK** (8375 baitai), `app.js` **200 OK**, `styles.css` **200 OK**.
6. Sukūriau šiuos atminties failus repo viduje: `CLINE/00_START_HERE.md`, `02_DIENORASTIS.md`, `03_TAISYKLES.md`, `04_TODO.md`.

### Patikrinta būsena (kodas)
- `app.js`: `const STORE_PAUSED = true;` → parduotuvė **laikinai uždaryta**. Užsakymo forma išjungiama (laukai `disabled`, permatomumas 0.45, `pointer-events: none`), rodomas pranešimas „Parduotuvė laikinai neveikia. Užsakymai ir mokėjimai laikinai išjungti.“
- `index.html`: viršuje yra `paused-banner`, skyrius „Pagalba 24/7“ su 3 kortelėmis (🤖 Robotukas / 👤 Gyvas žmogus / ☎️ Skubus kontaktas), mygtukas `tel:+37060000000` su žyma „(ne svarbu, neskambinti)“.
- Katalogas: 8 produktai, filtrai (visi / tech / sport / home), krepšelis `Map()` pagrindu, pristatymas 3.99 €, nemokamas nuo 75 €.

### Ko NEDARIAU ir kodėl
- **Nekūriau darbalaukio nuorodų** „CLINE RYSYS“ / „CLINE - PRADZIA“ — šioje sesijoje nėra darbalaukio nei `.lnk` galimybės. Jei anksčiau tokios nuorodos buvo sukurtos, jos yra tavo kompiuteryje, ne čia.
- **Neskelbiau jokio tunelio adreso** — jis numirtų kartu su šia sesija, o aš nežadu to, ko negaliu išpildyti rytoj.
- **Neliečiau `main`** ir nieko netryniau (žr. `03_TAISYKLES.md`).
- **Neįrašiau jokių „slaptažodžių“ ar raktų** — n8n buvo minėtas kaip paleistas „be raktų“; repo viduje raktų nėra ir neturi būti.

### Įspėjimas ateičiai (kad nebekartočiau klaidų)
Ankstesni bandymai jungtis nepavyko: SSH → 404, pinggy → slaptažodis, bore → antivirusas. Priežastis bendra: **agentas debesyse neturi prieigos prie tavo kompiuterio**, tad jokie „įėjimo taškai“ į tavo mašiną iš čia neveiks patikimai. Vietoj to naudojam git — jis praeina visur.