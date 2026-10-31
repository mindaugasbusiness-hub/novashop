# ATSTATYMO TAŠKAS Nr. 1 — AUKSINĖ BŪSENA (2026-10-31)

**Sukurta:** 2026-10-31 · **Šaka:** `cline/da6qq3k9` · **Git žyma:** `atstatymas-1`
**Šaltinis:** direktoriaus pulto (`http://127.0.0.1:8790/`) ataskaita 2026-10-31 04:16:04

> Šiame taške užfiksuota būsena, kurią direktorius patvirtino kaip **veikiančią ir teisingą**:
> „pulto duomenys — viskas veikia labai gerai, ko aš noriu, aš noriu, kad taip sistema visada veiktų."

---

## 1. Pagrindinis rodiklis

| Rodiklis | Reikšmė šiame taške |
|---|---|
| **Servisai veikia** | **11/11** |
| Sistemos širdis | Gyva **10/11** |
| Riktai (kas dažniausiai lūžta) | **11/11** |
| Klavisai F1–F11 | **7/8** (F1 užimtas kito proceso — žinoma, priimta būsena) |
| Aukciono svetainė | `https://penktadienioaukcionas.lt` → **HTTP 200** |
| VPS tarnybos | AUKCIONAS **AKTYVUS**, MOKYKLA **AKTYVUS**, CLOUDFLARED **AKTYVUS** |
| Kopijos | VPS 0,8 h, vietinė 1,3 h — abi **ŠVIEŽIOS** |

---

## 2. 11 servisų (tiksli būsena, kurią reikia atstatyti)

| # | Servisas | Adresas | Būsena | Detalės |
|---|---|---|---|---|
| 1 | n8n | `:5678 /healthz` | VEIKIA | `status=ok` |
| 2 | Naršyklės daemonas | `:8099 /health` | VEIKIA | atsako (reikia rakto) |
| 3 | F6 panelis | `:8766 /api/list` | VEIKIA | dainų: 71 · groja: nieko |
| 4 | Žvėris UI | `:8091 /api/status` | VEIKIA | modelis: `huihui_ai/llama3.3-abliterated:70b` · įkėlimai: 0 |
| 5 | Kumštis tools | `:8090 /healthz` | VEIKIA | būsena: ok |
| 6 | Naršyklės CDP | `:9222 /json/version` | VEIKIA | Chrome/156.0.8078.74 |
| 7 | n8n brokeris | `:5679` | VEIKIA | portas klauso (**tas pats PID kaip :5678**) |
| 8 | Qdrant | `:6333` | VEIKIA | portas klauso |
| 9 | Automatikos tiltas | `:8792 /health` | VEIKIA | veiksmai: ensure/collect/write/darbai/run |
| 10 | AUSYS (balsas) | `:8795` | VEIKIA | portas klauso |
| 11 | PULTAS (šis) | `:8790` | VEIKIA | portas klauso |

Patikrinti po atstatymo: `tools\atstatymas\patikrinti-servisus.ps1` (tikrina būtent šiuos 11).

---

## 3. Automatika, kuri tuo metu dirbo (taip ir turi likti)

| Grafikas / kontrolė | Būsena taške Nr. 1 |
|---|---|
| `CLINE VISKAS kas 5 min` | VEIKIA · rezultatas=0 · paskutinis 04:15:19 |
| `CLINE Hotkeys` | VEIKIA · rezultatas=0 · paskutinis 04:16:00 |
| `CLINE VISKAS pries isjungima` | DĖMESIO · `-1073741502` (Windows teardown), bet būsena šviežia — **priimta, duomenų neprarandama** |
| Būsena (06) rašoma | VEIKIA · prieš 0,6 min |
| Sesija (07) rašoma | VEIKIA · prieš 0,6 min |
| Failų pokyčiai (11) | VEIKIA · šiandien pakeitimų: **175** |
| Darbų žurnalas (10) | VEIKIA |
| n8n workflow aktyvus | VEIKIA · `CLINE - uzduotis Cline worker` · `aktyvus=True` · paskelbta versijų: 1 |
| n8n realiai vykdo | VEIKIA · vykdymų: 119 |
| Automatikos tiltas | VEIKIA · health=200 |

---

## 4. VPS būsena (penktadienioaukcionas.lt)

| Kontrolė | Būsena taške Nr. 1 |
|---|---|
| Svetainė | HTTP 200 |
| Eterio daina `/api/desk_song` | VEIKIA · daina: negroja |
| Radijas `/api/radio/now` | VEIKIA · ICONA POP — I LOVE IT |
| Mokymas `/api/practice/status` | VEIKIA · botų: 500 · statymų: 1383 · ratas: 3 · mokosi: TAIP |
| Disko vieta | laisva 7,2 G iš 14 G (užimta 47 %) |
| `vilkas-watchdog.log` | 11:05, 11:10, 11:15 — visi **OK** (svetainė 200, disko 7373–7375 MB) |
| IVR `/twilio/log` | VEIKIA · įvykių: 20 |

Fiksuojama: `tools/atstatymas/vps-taskas.sh sukurkti 1` (VPS pusėje) — app.py + jo `.bak` istorija + systemd unit + SHA256 manifestas.

---

## 5. Ką šis taškas apima ir ko ne

**Apima (git dalis, jau užfiksuota žyma `atstatymas-1`):**
- `tools/n8n/` — n8n paleidimas, budėtojas, diagnostika, CLI apvalkalas
- `tools/atstatymas/` — taško kūrimas/atstatymas (Windows + VPS)
- `CLINE/` — atmintis (00–05) ir šis atstatymo aprašas

**Apima (mašinos dalis — sukuriama `sukurkti-taskas.ps1 -Numer 1`):**
- `pultas\*` (pulto kodas), `tools\*` (visi įrankiai), atmintis (`*.md`)
- n8n: `workflows.json`, `database.sqlite`, `pids.json`
- Task Scheduler užduotys (XML: N8N / CLINE / KUMSTIS / PULTAS / HOTKEY)
- 11 servisų ataskaita ir versijos (`bukle\servisai.txt`, `bukle\versijos.txt`)

**NEapima (sąmoningai, 3 taisyklė):**
- jokių slaptažodžių, raktų ir tokenų **šiame repo dokumente** — jie lieka tik vietiniame
  `C:\Users\M\CLINE\VISKAS\` aplanke, kuris **niekada nekeliamas į git**
- n8n prieigos duomenys, VPS slaptažodis, ntfy raktai — tik VISKAS aplanke

---

## 6. Kaip atstatyti į Nr. 1

Direktoriui pasakius **„atstatyk į Nr. 1"**:

```powershell
# 1) Pirmiausia pažiūrėti, ką tai darytų (nieko nekeičia)
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\M\CLINE\tools\atstatymas\atstatyti-tasku.ps1 -Numer 1 -Sausai

# 2) Tikras atstatymas
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\M\CLINE\tools\atstatymas\atstatyti-tasku.ps1 -Numer 1

# 3) VPS pusė
/root/BACKUPS_VPS/atstatymas/vps-taskas.sh atstatyti 1
```

Atstatymas **niekada netrina**: pirmiausia daro `PRADINE-BUKLE_<data>` kopiją, o kiekvieną
perrašomą failą palieka su `.bak-pries-atstatyma-<data>`.

---

## 7. Būsena: ar taškas Nr. 1 jau pilnas?

| Dalis | Būsena |
|---|---|
| Git dalis (`tools/`, `CLINE/`) | ✅ **PILNA** — žyma `atstatymas-1` |
| Mašinos dalis (pultas, tools, n8n DB, užduotys) | ✅ **PILNA** — 2026-10-31 05:46, 504 failai / 508,1 MB, `TASKAS.json` yra |
| VPS dalis | ⛔ **NEDAROMA** — M sprendimas 2026-10-31: „aš nenoriu jokio VPS, viskas yra iš mano kompiuterio" |
| Patikrinta, ar 11/11 | ✅ Taip — pulto atstatyta 2026-10-31 05:46 (11/11, 5 s) |

**Taškas Nr. 1 = tik tavo kompiuteris.** Atstatymas: `atstatyti-tasku.ps1 -Numer 1`.

Dėl svetainės `penktadienioaukcionas.lt`: jai **nieko papildomai nereikia** — VPS pats daro
automatines kopijas (`BACKUPS_VPS`, pulto D sekcija rodo `ŠVIEŽIAS`) ir turi `vilkas-watchdog`,
kuris kas 5 min tikrina, ar svetainė atsako.



Kol mašinos ir VPS dalys nepaleistos, atstatymas iš taško Nr. 1 atkurs **kodą ir nustatymus**,
bet ne tavo mašinos failų turinį. Todėl pirmas žingsnis tavo kompiuteryje — `sukurkti-taskas.ps1 -Numer 1`.
