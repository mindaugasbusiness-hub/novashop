# 03 · TAISYKLĖS

Taisyklės galioja man (agentui) visose sesijose. Jei kyla konfliktas tarp taisyklės ir prašymo „padaryk greičiau“ — laimi taisyklė.

---

## 1 taisyklė (svarbiausia): NIEKO NETRINTI be direktoriaus žodžio

- Netrinu failų, katalogų, branchų, commitų, duomenų bazės įrašų, DIEGIMO (deploy) konfigūracijų — be aiškaus „taip, trink“.
- Kai reikia „pašalinti“, naudoju **TRASH principą**, o ne trynimą:
  - failą → pervadinu su data, pvz. `app.js.bak-2026-10-26`, arba perkeliu į `CLINE/TRASH/`;
  - kodą → pakomentuoju (`// PASLEPTA 2026-10-26: ...`) arba išjungiu vėliavėle (`STORE_PAUSED = true`), NEišmetu;
  - git commit → niekada neamenduoju ir neforsuoju `push`, jei jau nustumta (tik naujas commit).
- Prieš bet kokį didesnį pakeitimą padarau kodo kopiją (branch arba `.bak` failą), kad būtų kuo grąžinti.

## 2 taisyklė: `main` branch yra šventas

- Dirbu tik per atskirus branchus (`cline/<id>`).
- Į `main` nieko nestumiu be direktoriaus prašymo.

## 3 taisyklė: jokių raktų ir slaptažodžių repo viduje

- API raktai, slaptažodžiai, tokenai **niekada** neįrašomi į failus, kurie eina į git.
- Jei raktas reikalingas — tik aplinkos kintamasis arba atskiras, į git neįtrauktas failas (`.env`, įtrauktas į `.gitignore`).

## 4 taisyklė: sakyti tiesą apie galimybes

- Jei ko negaliu padaryti (pvz., sukurti darbalaukio nuorodos ar išlaikyti ryšio adreso iki rytojaus), sakau tai **iškart**, o ne pažadu ir „pamirštu“.
- Viskas, ką rašau į dienoraštį, turi būti **patikrinta**, ne spėjama. Kur netikrinau — rašau „nepatikrinta“.

## 5 taisyklė: prieš tęsiant — pirma atmintis

- Kiekvienos sesijos pradžioje perskaitau `00_START_HERE.md` ir `02_DIENORASTIS.md`, tada `04_TODO.md`.
- Po reikšmingo darbo atnaujinu `02_DIENORASTIS.md` ir `04_TODO.md` **tą pačią sesiją**, ne „rytoj“.

## 6 taisyklė: miesčioniškas saugumas šiam projektui

- Parduotuvės funkcijos, kurios imituoja mokėjimą/uzsakymą, lieka **išjungtos** (`STORE_PAUSED = true`), kol direktorius nepasakys kitaip.
- Telefono numeris `+37060000000` — demonstracinis, su žyma „neskambinti“. Nekeisiu į tikrą be prašymo.