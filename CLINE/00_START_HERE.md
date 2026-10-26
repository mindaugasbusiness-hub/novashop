# 00 · START HERE — kaip tęsti darbą

**Savininkas:** Mindaugas (direktorius)
**Projektas:** NovaShop (statinė elektroninė parduotuvė) — repo `mindaugasbusiness-hub/novashop`
**Paskutinis atnaujinimas:** 2026-10-26
**Darbinis branch:** `cline/7at5cm57` (pagrindinis `main` NELIESTI)

---

## 1. Viena eilutė rytojui (nukopijuok ir įklijuok)

> Perskaityk `C:\Users\M\CLINE\00_START_HERE.md` ir `02_DIENORASTIS.md` – tęsiam.

Jei `C:\` nepasiekiamas (t. y. sesija paleista debesyse, ne tavo kompiuteryje), ta pati eilutė su papildymu veikia visada:

> Perskaityk `C:\Users\M\CLINE\00_START_HERE.md` ir `02_DIENORASTIS.md` – tęsiam. Jei `C:\` nepasiekiamas, paimk tuos pačius failus iš GitHub repo `mindaugasbusiness-hub/novashop`, branch `cline/7at5cm57`, aplankas `CLINE/`.

Kodėl du variantai: žr. 3 skyrių – šioje sesijoje `C:\` disko **nėra**, todėl vienintelė vieta, kuri garantuotai išlieka, yra git.

---

## 2. Tvarka, kuria skaitomi failai

1. `CLINE/00_START_HERE.md` ← šis failas (kaip dirbti)
2. `CLINE/02_DIENORASTIS.md` ← ką veikėme paskutinį kartą, su patikrintais faktais
3. `CLINE/03_TAISYKLES.md` ← ko NEGALIMA daryti (1-oji taisyklė: nieko netrinti be žodžio)
4. `CLINE/04_TODO.md` ← kur sustojome ir ką darome toliau

---

## 3. Patikrinti faktai (2026-10-26, ne spėjimai)

| Teiginys | Būsena šioje sesijoje |
|---|---|
| Yra `C:\Users\M\CLINE\` su `00_START_HERE.md` ir kt. | **NE** — `C:\` disko nėra, `/mnt/c` tuščias, PowerShell nėra |
| Darbalaukyje yra nuorodos „CLINE RYSYS“ / „CLINE - PRADZIA“ | **Negaliu sukurti** — darbalaukio ir `.lnk` failų šioje sesijoje nėra |
| Veikia `trycloudflare` / `agent.ps1` / n8n / sargas | **Repo viduje pėdsakų nėra.** Tos žinios buvo tik tavo kompiuteryje |
| Adresas iš šios dienos veiks rytoj | **NE** — ši smėliadėžė (sandbox) išjungiama, ir adresas miršta kartu su ja |
| Repo /workspace išliks | **TAIP**, jei įrašyta į git ir nustumta į `origin` |
| Statinė parduotuvė paleidžiama ir atsakymas 200 OK | **TAIP** — patikrinta: `index.html`, `app.js`, `styles.css` → HTTP 200 |

Išvada (sąžininga): greitasis kelias su „CLINE RYSYS“ priklauso nuo to, ar rytojaus sesija turės prieigą prie tavo Windows kompiuterio. Jei neturės — jis neveiks, kad ir ką bebūtų pažadėta. Todėl **atrama perkeliama į git**: ji veikia iš bet kurio įrenginio.

---

## 4. Kaip mane pažadinti rytoj (2 komandos)

```bash
git clone https://github.com/mindaugasbusiness-hub/novashop.git
cd novashop && git checkout cline/7at5cm57
cat CLINE/00_START_HERE.md CLINE/02_DIENORASTIS.md
```

Jei repositorija jau nuklonuota, užtenka:

```bash
git -C <kelias> fetch origin && git -C <kelias> checkout cline/7at5cm57
```

Tada pasakyk vieną sakinį iš 1 skyriaus — toliau tęsiu be papildomų paaiškinimų.

---

## 5. Dėl ilgalaikio ryšio (variantas A vs B)

- **Variantas B (tunelis + n8n + „CLINE RYSYS“)** veikia tik kol gyva sesija ir tik tam kompiuteriui, kuriame jis paleistas. Po kiekvieno perkrovimo adresas naujas. Tai nėra klaida — tai tokio modelio savybė.
- **Variantas A (Cline su VS Code tavo kompiuteryje)** duoda nuolatinį ryšį be jokių adresų, nes dirbu tiesiogiai tavo mašinoje.
- **Trečias, pigiausias variantas:** dirbti taip, kaip dabar — repo + git. Nereikia jokio tunelio, jokio n8n, jokio atnaujinamo adreso. Ryšys atsiranda per `git clone` (arba per Cline GitHub prisijungimą).

Rekomendacija: rinktis **A** (jei nori nuolatinio „gyvo“ ryšio) arba **trečią** (jei nori paprastumo ir nulis priežiūros). B tinka tik vienkartiniam, trumpam darbui.