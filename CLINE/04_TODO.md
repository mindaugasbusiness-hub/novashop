# 04 · TODO — kur sustojome ir ką darome toliau

Atnaujinta: 2026-10-26 · Branch: `cline/7at5cm57`

---

## Kur sustojome

- Parduotuvė **užšaldyta** (`STORE_PAUSED = true`) — mygtukai „Laikinai neveikia“, forma išjungta, baneris rodomas.
- „Pagalba 24/7“ skyrius yra (robotukas / gyvas žmogus / skubus kontaktas).
- Katalogo logika veikia: filtrai, krepšelis, likučiai, pristatymo skaičiavimas (3.99 €, nemokama nuo 75 €).
- Atmintis perkelta į `CLINE/` šiame repo (nes `C:\` sesijoje nepasiekiamas).

## Sprendimai, kurių laukiu iš direktoriaus

- [ ] **A ar B?** — ar pereiname prie Cline + VS Code tavo kompiuteryje (nuolatinis ryšys), ar liekame prie git varianto.
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