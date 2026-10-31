# 04 · TODO — kur sustojome ir ką darome toliau

Atnaujinta: 2026-10-27 (Sesija 4) · Branch: `cline/g2zpktej` (nuo `origin/cline/0xjxer93`)

---
## BŪSENA 2026-10-31 (Sesija 6) · Branch: `cline/da6qq3k9` · Žyma: `atstatymas-1`

### ATSTATYMO TAŠKAS Nr. 1 — 11/11 auksinė būsena

- [x] Užfiksuota M patvirtinta būsena: **11/11 servisai**, svetainė HTTP 200, VPS tarnybos AKTYVIOS
- [x] Aprašas: `CLINE/ATSTATYMAS/01_TASKAS.md`; registras: `CLINE/ATSTATYMAS/atstatymo-sarasas.md`
- [x] Sukurta atstatymo sistema (`tools/atstatymas/`) su SHA256 patikra ir privalomomis kopijomis
- [x] Testai: VPS skriptas 23/23, sistemos savitikra 13/13, PS parseris 0 klaidų
- [x] **M žingsnis 1:** mašinos taškas Nr. 1 sukurtas — **504 failai / 508,1 MB** (2026-10-31 05:46)
- [x] **Sprendimas:** VPS dalis **NEDAROMA** — M: „aš nenoriu jokio VPS, viskas yra iš mano kompiuterio"
- [x] Taškas Nr. 1 baigtas: git žyma + mašinos kopija. Daugiau žingsnių nereikia.

### Kaip atstatyti į Nr. 1 (kai M pasakys)

```powershell
# pirma pažiūrėti planą
...\tools\atstatymas\atstatyti-tasku.ps1 -Numer 1 -Sausai
# tikras atstatymas
...\tools\atstatymas\atstatyti-tasku.ps1 -Numer 1
```
VPS: `/root/BACKUPS_VPS/atstatymas/vps-taskas.sh atstatyti 1`

### Laukia M sprendimo

1. Ar jungti šią šaką į `main`, ar su `cline/g2zpktej` (ten naujausia atmintis)?
2. Ar daryti tašką Nr. 2 po kiekvieno didesnio pakeitimo (rekomenduoju: taip, prieš rizikingus darbus)?

---


## BŪSENA 2026-10-28 (Sesija 5) · Branch: `cline/da6qq3k9`

### n8n :5678 / :5679 — sutvarkyta repo pusėje, laukia 3 žingsnių M mašinoje

- [x] Išaiškinta: **:5679 = n8n Task Broker**, ne antras n8n (įrodyta iš `_out/readNative2.txt`:
      `5678 -> PID 7976`, `5679 -> PID 7976`)
- [x] Sukurti įrankiai `tools/n8n/` (10 failų) + pulto mygtuko įrankis
- [x] Patikra be Windows: PowerShell 7.4.6 parseris 0 klaidų; testai 40/40; savitikra 9/9; pulto įrankis 22/22
- [ ] **M žingsnis 1:** nukopijuoti `tools\n8n\*` į `C:\Users\M\CLINE\tools\n8n\`
- [ ] **M žingsnis 2:** paleisti `n8n-diagnostika.ps1` — patikrinti, ar `N8N_ROOT` teisingas
- [ ] **M žingsnis 3:** `registruok-uzduotis.ps1` (budėtojas kas 1 min + startas prisijungus)
- [ ] Pulto mygtukas: `python pulto-mygtukas-restart-n8n.py --diegti ...\pultas.py`
- [ ] Po 2–3 Windows perkrovimų patikrinti, ar pultas rodo „Servisai veikia: 11/11“

### Laukia M sprendimo

1. Ar perkelti šią šaką į `main`, ar sujungti su `cline/g2zpktej` (ten yra naujausia atmintis)?
2. Ar n8n brokerį palikti `internal` režime (kaip dabar), ar pereiti prie `external` + atskiro
   `n8nio/runners` (saugiau, bet reikia Docker/WSL)?

---



## BŪSENA 2026-10-27 (Sesija 4)

- [x] `cline` CLI įdiegtas direktoriaus kompiuteryje (`npm install -g cline` → 3.0.74) — **padaryta**
- [x] Ryšys per PowerShell (relay + cloudflared) — **veikia**, klientas `96f8c40d`, savitikra 11/11
- [ ] **ntfy budėtojas nepakėlė ryšio automatiškai** — reikia sutvarkyti `autoconnect.ps1`
      (šįkart padėjo rankinis `iex (irm .../agent.ps1)`)
- [ ] Kur laikomas VPS slaptažodis: M įrankiuose `C:\Users\M\CLINE\tools\add_env.py` ir kt. `vps_*.py`
      (patikrinta, kad veikia). **Vertės niekada nerašyti į repo ar į pokalbį.**
- [x] Šioje sesijoje `C:\` pasiekiamas **per relay** (ne tiesiogiai); `cloudflared` 2026.10.5 → `/workspace/.tools/`
- [ ] Parduotuvė vis dar uždaryta (`STORE_PAUSED = true`), svetainė atsako 200 OK

### Laukia direktoriaus sprendimo (1 atsakymas iš 3)
1. **Atidaryti parduotuvę?** (`STORE_PAUSED = false`) — ar dar laikom uždarytą?
2. **Deploy į GitHub Pages?** — nuolatinis nemokamas adresas, jokio tunelio.
3. ~~Nebaigtas „neonine šokėja“ darbas~~ → **ĮDIEGTA SERVERYJE 2026-10-27 22:13** ✅
   - `/opt/aukcionas/app.py` +2090 B, kopija `app.py.bak-neon-20261027-221303`, `aukcionas` → active,
     svetainė 200, `class="neon-dancer"` = 1, video 200.
   - Matuota Chrome DevTools: 1600×900 → 168×160 px; **M dydis (1078×540) → 168×88 px**, y=359, panelis 447,
     video groja (6,4 s / 12,9 s). v2 pataisa: `app.py.bak-neonv2-20261027-222042`.
   - Jei nepatiks dydis — keičiama viena eilutė (`height`) ir vėl `systemctl restart aukcionas`.
   - Grąžinimas: `cp /opt/aukcionas/app.py.bak-neon-20261027-221303 /opt/aukcionas/app.py && systemctl restart aukcionas`

---

## (2026-10-26 įrašas, paliktas nepakeistas)

## ⭐ DABAR SVARBIAUSIA (1 žingsnis direktoriui)

Prijungimas per PowerShell — 3 komandos tavo lange `PS C:\Users\M>`:

```powershell
node -v                                     # jei nera -> winget install OpenJS.NodeJS.LTS
npm install -g cline
cline auth cline
```

Tada mane paleidi:

```powershell
cline -i
# arba
cline -c C:\Users\M\CLINE "Perskaityk 00_START_HERE.md ir 02_DIENORASTIS.md – tęsk"
```

Visa smulkmena: `CLINE/05_PRIJUNGIMAS_WINDOWS.md`. Patikrinta: `cline --version` → 3.0.74.

---

## Kur sustojome

- Parduotuvė **užšaldyta** (`STORE_PAUSED = true`) — mygtukai „Laikinai neveikia“, forma išjungta, baneris rodomas.
- „Pagalba 24/7“ skyrius yra (robotukas / gyvas žmogus / skubus kontaktas).
- Katalogo logika veikia: filtrai, krepšelis, likučiai, pristatymo skaičiavimas (3.99 €, nemokama nuo 75 €).
- Atmintis šiame repo aplanke `CLINE/` — 5 failai (00–05).
- Ištirta ir paruošta: vietinis `cline` CLI kaip nuolatinis prijungimo būdas (be tunelio).

## Sprendimai, kurių laukiu iš direktoriaus

- [ ] **Ar diegiame `cline` CLI** ir ar jis pavyko tavo PowerShell lange? (tai pagrindinis kelias dabar)
- [ ] **Atidaryti parduotuvę ar laikyti uždarytą?** (kol kas uždaryta, ir tai saugu)
- [ ] **Diegimas (deploy):** ar kelti svetainę į GitHub Pages, kad turėtum nuolatinį, nemokamą adresą?

## Darbai iš eilės (kai bus „taip“)

1. **Vienas jungiklis uždarymui** — kad `STORE_PAUSED` būtų viena vieta, o ne išbarstyta logika; uždarytą/atidarytą būseną rodytų aiškiai.
2. **Baneris be inline stiliaus** — perkelti `paused-banner` stilių į `styles.css` (švariau, lengviau keisti).
3. **Atidarymo variantas** — kai direktorius pasakys, paruošti „atidarymo“ režimą (forma veikia tik kaip demonstracija, be tikro mokėjimo).
4. **Paleidimo instrukcija** — viena eilutė kompiuteryje: `python3 -m http.server 8080` arba `npx serve`.
5. **Deploy į GitHub Pages** (jei direktorius pritars) — nuolatinis adresas, jokio tunelio, jokio n8n.

## Ką reikia turėti galvoje

- Ryšys per tunelį (trycloudflare) nepatvarus: adresas keičiasi kas sesiją, seni bandymai (SSH 404, pinggy slaptažodis, bore antivirusas) nepavyko. Git — patikimiausias kelias.
- NIEKO NETRINTI: žr. `03_TAISYKLES.md`.