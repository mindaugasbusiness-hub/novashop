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
