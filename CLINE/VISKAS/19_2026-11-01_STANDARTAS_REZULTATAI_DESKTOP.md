# 19 - STANDARTAS: visu uzduociu rezultatai darbalaukyje (DeFi formatas)

Sukurta: 2026-11-01. Autorius: Cline. Galioja VISOMS KUMSTIS AI uzduotims.

## 1. Taisykle

Kiekviena uzduotis, kuri renka duomenis, PRIVALO rezultatus ideti i darbalauki:

```
C:\Users\M\Desktop\<UZDUOTIES-PAVADINIMAS>\
   ataskaita_<data>_<laikas>.html   <- pilna ataskaita viename HTML faile (DeFi stilius)
   ataskaita_<data>_<laikas>.md     <- ta pati ataskaita tekstu
   visi-duomenys_<data>.csv         <- visi surinkti duomenys (skirtukas kabliataskis)
   grupes\                          <- atskiri CSV pagal kategorijas (01-..., 02-...)
```

- Kiekvienas paleidimas kuria **naujus** failus su data ir laiku.
- **NIEKO NETRINK**, senu failu neperrasyti.
- HTML stilius: toks pat kaip `C:\Users\M\Desktop\Kumstis\DeFi ataskaitos\defi-naujausia.html`
  (font Segoe UI, lentele su sticky header, sekcijos, ispejimai).

## 2. Dabar nustatyta (2026-11-01)

| Nustatymas | Reiksme |
|---|---|
| Workflow | `CLINE - uzduotis Cline worker (Ollama nereikia)` |
| Paleidiklis | **kas 1 val.** (anksciau buvo kas 6 val.) |
| Uzduotis | autoplius.lt auto iki 400 EUR su technine apziura |
| Rezultatai | `C:\Users\M\Desktop\AUTO-PAIESKA\` (DeFi formatu) |
| Modelis | `cline-free/nemotron-3.5-super-vl` (nemokamas) |

## 3. Receptas (kodel veikia)

Autoplius blokuoja paprasta parsiuntima (403). Todėl uzduotyje irasytos tikslios komandos:

```
curl "http://127.0.0.1:8099/goto?url=<adresas>" -H "X-BToken: bt-9f3a71c2e5d84b06"
curl "http://127.0.0.1:8099/text" -H "X-BToken: bt-9f3a71c2e5d84b06"
```

`:8099` = narsykles daemonas (Playwright + Chrome). Jis atidaro puslapi kaip zmogus -> 200 OK.

## 4. Ka daryti, kai norima naujos uzduoties

1. Uzduoties tekstas rasomas n8n mazge `Uzduotis` -> laukas `prompt`.
2. Butinai irasoma:
   - `TIPAS: veikti` arba `TIPAS: skaityti`
   - kaip gauti duomenis (jei svetaine blokuoja - per `:8099`)
   - KUR deti rezultatus (darbalaukio aplankas, DeFi formatas)
   - `NIEKO NETRINK`
3. Paskelbti (Publish).
