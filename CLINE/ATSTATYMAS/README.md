# ATSTATYMO TAŠKAI — kaip visada grąžinti veikiančią būseną

Tikslas: kai direktorius pasako **„atstatyk į Nr. N"**, sistema (pultas, įrankiai, n8n)
grąžinama į tą būseną, kuri tuo metu veikė.

> **SVARBU (M sprendimas 2026-10-31):** „aš nenoriu jokio VPS, viskas yra iš mano kompiuterio."
> Todėl VPS dalis (`vps-taskas.sh`) **nenaudojama**. Tašką sudaro tik **git žyma + mašinos kopija**.
> Svetainė `penktadienioaukcionas.lt` turi savo automatinius `BACKUPS_VPS` ir `vilkas-watchdog`.


---

## 1. Trys dalys, kurias apima vienas taškas

| Dalis | Kur saugoma | Kas sukuria |
|---|---|---|
| **Git dalis** | GitHub šaka + žyma `atstatymas-N` | agentas (commit + tag) |
| **Mašinos dalis** | `C:\Users\M\CLINE\VISKAS\ATSTATYMO_TASKAI\TASKAS-N_<data>\` | `sukurkti-taskas.ps1 -Numer N` |
| **VPS dalis** | `/root/BACKUPS_VPS/ATSTATYMO_TASKAI/TASKAS-N_<data>/` | `vps-taskas.sh sukurkti N` |

Taškas laikomas **pilnu** tik kai yra visos trys dalys.

---

## 2. Sukurti naują tašką (kai viskas veikia 11/11)

```powershell
# --- Tavo kompiuteryje ---
cd C:\Users\M\CLINE\tools\atstatymas

# 0) Įsitikinti, kad tikrai viskas veikia (11/11)
powershell -NoProfile -ExecutionPolicy Bypass -File .\patikrinti-servisus.ps1

# 1) Sukurti tašką (numeris pridedamas automatiškai)
powershell -NoProfile -ExecutionPolicy Bypass -File .\sukurkti-taskas.ps1 -Pastaba "11/11 veikia"

# 2) Jei nori konkretaus numerio (pvz. pirmo):
powershell -NoProfile -ExecutionPolicy Bypass -File .\sukurkti-taskas.ps1 -Numer 1 -Pastaba "auksine busena"
```

```bash
# --- VPS ---
/root/BACKUPS_VPS/atstatymas/vps-taskas.sh sukurkti 1
/root/BACKUPS_VPS/atstatymas/vps-taskas.sh sarasas
```

---

## 3. Atstatyti į tašką Nr. N

```powershell
# Ką tai darytų (nieko nekeičia) -- VISADA pirmiausia šitai
powershell -NoProfile -ExecutionPolicy Bypass -File .\atstatyti-tasku.ps1 -Numer 1 -Sausai

# Tikras atstatymas -- atstato VISKĄ (ir n8n duomenų bazę)
powershell -NoProfile -ExecutionPolicy Bypass -File .\atstatyti-tasku.ps1 -Numer 1

# Jei nori atstatyti tik failus, o dabartinę n8n DB PALIKTI:
powershell -NoProfile -ExecutionPolicy Bypass -File .\atstatyti-tasku.ps1 -Numer 1 -BeDuomenuBazes
```

Ką daro atstatymas (eilės tvarka):

1. patikrina visų taško failų **SHA256** (sugadintą tašką atmeta),
2. sustabdo **n8n** (kad DB failas nebūtų užrakintas),
3. išsaugo dabartinę būklę į `PRADINE-BUKLE_<data>` — **įskaitant dabartinę n8n DB**,
4. atstato pultą, tools, atmintį, `pids.json` ir **`database.sqlite`**,
5. atstato Task Scheduler užduotis iš XML,
6. paleidžia n8n ir pultą,
7. paleidžia 11 servisų patikrinimą ir pasako, ar **11/11**.

Trukmė: ~2–4 min (271 MB duomenų bazės kopija).


```bash
# VPS pusė
/root/BACKUPS_VPS/atstatymas/vps-taskas.sh atstatyti 1 --sausai
/root/BACKUPS_VPS/atstatymas/vps-taskas.sh atstatyti 1
```

---

## 4. Apsaugos (kad atstatymas nepakenktų)

| Apsauga | Kaip veikia |
|---|---|
| **SHA256 patikra** | Prieš atstatant tikrinama, ar taško failai nesugadinti. Sugadinto taško **nestato** (kodas 2) |
| **Dabartinės būklės kopija** | Visada sukuriamas `PRADINE-BUKLE_<data>` — atstatymą galima atšaukti |
| **`.bak-pries-atstatyma-<data>`** | Kiekvienas perrašomas failas paliekamas su kopija (1 taisyklė: nieko netrinti) |
| **`-Sausai`** | Parodo planą ir nieko nekeičia |
| **Slapti duomenys** | VISKAS aplankas su slaptažodžiais **niekada** nekeliamas į git (3 taisyklė) |
| **Patikra po atstatymo** | Automatiškai paleidžiamas 11 servisų tikrinimas ir pranešama, ar 11/11 |

---

## 5. Grąžinimas, jei atstatymas buvo neteisingas

```powershell
# Dabartinė (prieš atstatymą buvusi) būklė:
C:\Users\M\CLINE\VISKAS\ATSTATYMO_TASKAI\PRADINE-BUKLE_<data>\

# Pavienis failas:
copy C:\...\pultas\pultas.py.bak-pries-atstatyma-<data> C:\Users\M\CLINE\pultas\pultas.py
```

VPS: `ls /opt/aukcionas/app.py.bak-pries-atstatyma-*` ir `cp` atgal + `systemctl restart aukcionas`.

---

## 6. Failų sąrašas

| Failas | Kur paleidžiamas | Paskirtis |
|---|---|---|
| `patikrinti-servisus.ps1` | Windows | Tikrina visus 11 servisų (kaip pultas) |
| `sukurkti-taskas.ps1` | Windows | Sukuria tašką + `TASKAS.json` su SHA256 |
| `atstatyti-tasku.ps1` | Windows | Atstato į tašką Nr. N (su patikra ir kopijomis) |
| `vps-taskas.sh` | VPS | Taškas/atstatymas `penktadienioaukcionas.lt` |
| `test-vps-taskas.sh` | bet kur (Linux) | VPS skripto savitikra (23 atvejai) |
| `savitikra.py` | bet kur | Patikrina šio aplanko failus ir saugumo taisykles |

---

## 7. Taškų registras

Sąrašas su visais taškais ir jų data: **`atstatymo-sarasas.md`** (šiame aplanke).
Pirmas pilnas taškas: **`01_TASKAS.md`** (2026-10-31, 11/11).
