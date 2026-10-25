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
