# CLINE ATASKAITA — 2026-10-25 (vakaro darbai)

**Kompiuteris:** DESKTOP-7LPGR90 · **Savininkas:** M
**Šis failas:** sugeneruotas automatiškai; senosios ataskaitos neperrašo.
**Kopijos:** `C:\Users\M\CLINE\VISKAS\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md`
**Pastaba:** tavo kompiuteryje veikia tvarkytojas, kuris laisvus darbalaukio failus sukelia į `Desktop\2026010.24d\`. Jei šio failo darbalaukyje neberasi — jis bus ten (ten jau yra ir šios ataskaitos kopija).

---

## 1. KO PRASEI IR AR PADARYTA

| # | Ko prašei | Padaryta | Įrodymas |
|---|---|---|---|
| 1 | Vienas aplankas su visais prisijungimais, raktai ir darbais | TAIP | `C:\Users\M\CLINE\VISKAS\` + `SEIFAS\` |
| 2 | Vienas failas, kad DI viską žinotų iš karto | TAIP | `00_SKAITYK_NAUJAUSIA.md` (52 KB) + `00_VISKAS_PILNA_ISTORIJA.md` (443 KB) |
| 3 | Visi darbai iki šiol, ne tik šiandien | TAIP | 14 vietinių Cline sesijų surinktos į pilną istoriją |
| 4 | Įjungus kompiuterį viskas susirenka automatiškai | TAIP | startuolio nuoroda `CLINE-SURINKTI.lnk` |
| 5 | n8n automatiškai prižiūri ir taiso | TAIP | workflow `clineAuto0000001`, kas 5 min, vykdymai 206/208/210/212/214 = success |
| 6 | F5 atnaujinimas, kai kas nors ne taip | TAIP | F5 atliekamas tik agento naršyklėje (`:9222`) |
| 7 | F6 grotuvas turi veikti | TAIP | `:8766` = 200, F6–F11 registruoti |
| 8 | Žvėris UI turi atsidaryti | TAIP | `:8091` = 200, `/api/status` = 200 |
| 9 | Niekas netrinama be leidimo | TAIP | jokie M failai netrinti; visos kopijos išsaugotos |
| 10 | Viena eilutė naujam DI | TAIP | `Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.` |

---

## 2. KAS VEIKIA DABAR (patikrinta 2026-10-25 15:00)

Servisai — **9/9**:

| Servisas | Portas | Būsena |
|---|---|---|
| n8n | :5678 | VEIKIA |
| broker | :5679 | VEIKIA |
| Qdrant | :6333 | VEIKIA |
| Kumštis tools | :8090 | VEIKIA |
| Žvėris UI | :8091 | VEIKIA |
| Naršyklės daemonas | :8099 | VEIKIA |
| F6 dainos | :8766 | VEIKIA |
| Pultas | :8790 | VEIKIA |
| Naršykės CDP | :9222 | VEIKIA |
| **CLINE automatikos tiltas** | **:8792** | **VEIKIA (naujas)** |
| AUSYS | :8795 | VEIKIA |

Svetainė `https://penktadienioaukcionas.lt` — **200**.
VPS `5.175.171.113` servisai: aukcionas, Vilko mokykla, cloudflared, vilkas-tts — **active**.

---

## 3. N8N — KĄ JIS DARO TAVO KOMPIUTERYJE

**Aktyvūs n8n darbai:**

1. **CLINE – Žvėris ir VISKAS automatiškai** (naujas, `clineAuto0000001`)
   - kas 5 min: patikrina Žvėris UI; jei neveikia — paleidžia jį iš naujo ir padaro F5 agento naršyklėje;
   - kas 5 min: atnaujina VISKAS istorijos failus.
2. **Aukciono stebėjimas** — kas 5 min tikrina svetainę; jei ne 200 — pranešimas; penktadienį 19:55 priminimas.
3. **Kumštis – vadovų ir specialistų valdyba** — laukia užduoties per `POST /webhook/kumstis`.
4. **Kumštis – DeFi skeneris** — kasdien 08:00 ir per `POST /webhook/defi-scan`, ataskaita į Desktop.

**Sąmoningai neaktyvus:** testinis nukritimo workflow (`aukc-test00000001`) — kad nesiųstų netikrų pranešimų.

**Įrodyta:** n8n vykdymai `206, 208, 210, 212, 214` (workflow `clineAuto0000001`) — visi `success`. Tilto žurnalas: `ensure` 2,8 s, `collect` 0,2 s, abu exit 0.

---

## 4. KAIP PADARYTA, KAD NEBEŪŽBLUOTŲ

- n8n šioje versijoje neturi bendro komandinio mazgo. Todėl sukurtas **saugus vietinis tiltas `:8792`**, kuris leidžia tik tris fiksuotus veiksmus: `/ensure`, `/collect`, `/run`. Savavališkos komandos neįmanomos.
- Slaptas raktas: `C:\Users\M\CLINE\tools\automation-secret.txt` (nėra rodomas, nenaudojamas internete).
- Ryšio agentas pataisytas: komanda vykdoma atskirame procese, tad ryšys nebeužstringa.
- Užrakto apsauga: jei veiksmas užtrunka per ilgai, jis atlaisvinamas automatiškai.

---

## 5. ŠIANDIEN PATAISYTA

| Ką | Priežastis | Rezultatas |
|---|---|---|
| F6 grotuvas | kitas procesas užėmė F1, senas scriptas blokavo ir F6–F11 | `:8766` = 200, F6–F11 veikia |
| Žvėris UI | trūko `index.html` | puslapis atkurtas, `:8091` = 200 |
| n8n workflow | naudojo neįdiegtą mazgą | pakeista į `httpRequest`, vykdymai sėkmingi |
| Automatikos tiltas | užraktas likdavo uždarytas | pataisyta, veikia stabiliai |
| Ryšio agentas | ilga komanda užblokuodavo ryšį | komandos vykdomos atskirai |

Visos originalios versijos išsaugotos `C:\Users\M\CLINE\BACKUPS\` kataloguose.

---

## 6. NUKREIPIMAI

**Naujam DI duok vieną eilutę:**

```
Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.
```

**Rankinis visko atnaujinimas:** darbalaukyje `CLINE ATSTATYTI`.
**Aplanko atidarymas:** darbalaukyje `CLINE VISKAS`.
**Jei reikia ryšio:** darbalaukyje `CLINE RYSYS`.

---

## 7. KAS DAR NEPADARYTA (sąžiningai)

1. **Žvėris AI modelių skaičius = 0.** Puslapis ir API veikia, bet atsakymams reikia atskirai paleisto modelio.
2. **F1 klavišas** lieka procesui, kuris jį užėmė; F6–F11 veikia be jo. Norint perimti F1 — pirmiau reikia identifikuoti savininką (nieko neuždariau).
3. **Sokejos #6–#43 → neoninis stilius** — nepadaryta, liko iš ankstesnės ataskaitos.
4. Ankstesni `05_TODO.md` punktai (admin slaptažodis, keepalive, ntfy) — dalis sutvarkyta, dalis laukia tavo sprendimo.

**Nepaliesta:** jokie tavo failai netrinti, neperkelti, nepervardinti.