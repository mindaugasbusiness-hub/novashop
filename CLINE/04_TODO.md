# 04 · TODO — kur sustojome ir ką darome toliau

Atnaujinta: 2026-10-26

## Padaryta šioje sesijoje
- [x] Veikiantis relay kodas perkeltas į šią šaką (`tools/relay/`)
- [x] Savitikra `test-relay.py` → 11/11 OK
- [x] `start.sh` (relay + tunelis + patikra + eilutė) → patikrinta gyvai iki viešo adreso
- [x] `lenta.py` (adresų lenta su saugumo saugikliu)
- [x] Windows pusė: paleidėjas, PRADZIA, nuorodų kūrėjas, įrašymas viena eilute
- [x] Atminties rinkinys `CLINE/00–05` šioje šakoje

## Kitas žingsnis (pirmas, kai tik bus ryšys)
- [ ] Direktorius paleidžia `windows/irasyk.ps1` eilutę savo kompiuteryje → patikrinti, ar darbalaukyje
      atsirado/atsinaujino abi nuorodos ir ar langas prisijungia per 2–3 sek.
- [ ] Jei kas nors lūžta: paimti `C:\Users\M\CLINE\logai\rysys-YYYYMMDD.log` ir sutvarkyti pagal jį.

## Laukia direktoriaus sprendimo
- [ ] **Repo viešumas.** Dabar viešas. Du klausimai: (a) ar daryti privatų (tada lenta veiks be saugiklių),
      (b) šakoje `cline/ejzcxn55` istorijoje yra VPS root slaptažodis — jį reikėtų pakeisti.
- [ ] Ar nori `-Auto` režimo (be jokio kopijavimo) — tada reikia privataus repo arba atskiros
      slaptos vietos adresui.
- [ ] NovaShop būsena: `STORE_PAUSED = true` (parduotuvė laikinai uždaryta). Atidaryti, kai bus sprendimas.
- [ ] Šakos `cline/f6ggtezn` darbai („Bitė papildymas“) vis dar nesujungti į `main` — reikia sprendimo,
      ar sujungti.

## Idėjos ateičiai (neįsipareigojimas)
- [ ] `pc.py cmd` rezultatų archyvavimas `C:\Users\M\CLINE\logai\` — kad liktų įrodymai, ką veikėme.
- [ ] Ryšio trukmės matavimas: kiek sekundžių praeina nuo nuorodos paspaudimo iki „prisijungta“.
      Dabar teigiama 2–3 sek. — verta išmatuoti ir įrašyti faktą.
