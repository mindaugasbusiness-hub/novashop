# 17 - KUMSTIS AI ARCHITEKTURA: kas uz ka atsakingas

Sukurta: 2026-11-01. Autorius: Cline (per relay).
Tikslas: kiekviena grandis daro tai, ka moka geriausiai. Stiprybes - ten, kur jos naudingiausios.

## 1. Trys grandys

| Grandis | Kas ji | Stiprybe | Atsakomybe |
|---|---|---|---|
| **n8n** (:5678) | VIRSININKAS | grafikai, salygos, integracijos, istorija (Executions), aliarmai | "KADA ir KA daryti" - paleidzia laiku, tikrina rezultata, pranesa apie klaida |
| **Nemotron 3.5 Super VL** (worker :7070) | NEMOKAMOS SMEGENYS | 1 mln. tokenu kontekstas, paveiksleliai, tekstu analize (legal 55%, finance 41%) | "PERSKAITYK IR APRASYK" - santraukos, vertimai, lenteles, vaizdo aprasymai, dideliu failu analize |
| **Cline (as)** | RANKOS IR MEISTRAS | veiksmai: narsykle, terminalas, failai, daug zingsniu, apejimai, taisymas | "EIK IR PADARYK" - sudetingi darbai, svetainiu skaitymas, gedimu taisymas, sistemos prieziura |

## 2. Darbo pasidalijimo taisykle

1. Uzduotis "perskaityti / aprasyti / santrauka / isversti" -> **Nemotron** (nemokama)
2. Uzduotis "veikti": naršyti svetaine, rinkti skelbimus, spausti, siusti, taisyti -> **Cline**
3. Kas paleidzia automatiškai ir kada -> **n8n**
4. Kas priziuri, kad visa tai veiktu -> **Cline**

## 3. Kaip tai atrodo praktiskai

```
n8n (kas 6 val. arba rankiniu paleidimu)
   |
   +--> worker :7070 -> Nemotron  (perskaityk ir aprasyk)
   |
   +--> jei reikia VEIKSMO -> uzduotyje nurodoma:
        "naudok narsykles daemona http://127.0.0.1:8099 su header X-BToken"
        (arba uzduotis duodama Cline'ui, kuris turi visas rankas)
```

## 4. Ko dabar truksta (kad butu "stipriausia sistema")

- [ ] **Marsrutizavimas**: dabar nera taisykles, kuri automatiskai nusprestu "si uzduotis - Nemotronui, ana - Cline'ui".
      Sprendimas: uzduoties sablonas su zyme `TIPAS: skaityti` arba `TIPAS: veikti`.
- [ ] **Narsykles receptas** Nemotronui: be jo jis negali apeiti svetainiu apsaugu (autoplius 403).
- [x] **Mokami modeliai NENAUDOJAMI** (M sprendimas 2026-11-01). Veiksmai atliekami taip:
      jei Nemotron nemoka - uzduotis duodama Cline'ui, arba Nemotronui duodamas tikslus receptas (komandos).
- [ ] **Pultas**: mygtukas "Paleisti KUMSTIS AI" ir uzduoties tipas.

## 5. Praktinis sablonas uzduociai

```
TIPAS: skaityti
KA: perskaityk faila X ir parasik santrauka (5-8 sakiniai)
KUR: C:\Users\M\Desktop\ATASKAITOS\santrauka.md
```

```
TIPAS: veikti
KA: eik i autoplius.lt, surask auto iki 400 EUR su TA
KAIP: naudok narsykles daemona http://127.0.0.1:8099 (header X-BToken: bt-9f3a71c2e5d84b06),
      /goto?url=... tada /text; rezultata rink i lentele
KUR: C:\Users\M\Desktop\AUTO-PAIESKA\ataskaita.md
```

## 6. Taisykles (galioja visada)

1. Niekas netrinama be M leidimo.
2. Pries pakeitima - busenos kopija (`media\busena.py imti`).
3. Nemokamas modelis - tik skaitymui; veiksmams - Cline arba mokamas modelis.
