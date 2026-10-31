# ATSTATYMO TAŠKŲ REGISTRAS

Naujausi viršuje. Kiekvienas taškas turi tris dalis: git žymą, mašinos kopiją, VPS kopiją.

| Nr. | Data | Git žyma | Mašinos kopija | Būsena tą akimirką | Pastaba |
|---|---|---|---|---|---|
| **1** | 2026-10-31 05:46 | `atstatymas-1` | ✅ **PILNA** — 504 failai, 508,1 MB (`TASKAS-1_2026-10-31_0546`, SHA256 manifestas) | **11/11 servisai** | Auksinė būsena. **VPS dalis NEDAROMA** — M sprendimas 2026-10-31: „viskas yra iš mano kompiuterio". Aprašas: `01_TASKAS.md` |

### Kas įtraukta į mašinos kopiją Nr. 1 (patikrinta 2026-10-31 05:46)

| Dalis | Kiekis |
|---|---|
| pultas | 68 failai |
| tools | 307 failai |
| atmintis (`*.md`, VISKAS) | 114 failai |
| n8n duomenų bazė | `database.sqlite` — 271,3 MB |
| n8n `pids.json` | TAIP |
| Task Scheduler užduotys | 11 XML |
| Būklės ataskaita | `bukle\servisai.txt` (11/11) + `bukle\versijos.txt` |
| **Iš viso** | **504 failai / 508,1 MB** |

Nepilnas bandymas `TASKAS-1_2026-10-31_0539` (be manifesto) paliktas, bet atstatymas jo nenaudoja —
imamas tik taškas su `TASKAS.json`.


---

## Kaip pridėti naują tašką

1. Įsitikinti, kad veikia: `patikrinti-servisus.ps1` → turi būti 11/11.
2. Windows: `sukurkti-taskas.ps1 -Pastaba "<kas pakeista>"`.
3. VPS: `vps-taskas.sh sukurkti` (arba su konkrečiu numeriu).
4. Agentas užfiksuoja git žymą `atstatymas-N` ir papildo lentelę viršuje.

## Numeravimo taisyklė

* Numeris **niekada nepakartojamas** ir nenaudojamas iš naujo.
* Taškas Nr. 1 lieka toks, koks buvo užfiksuotas -- jis neperrašomas, kad „atstatyti į Nr. 1"
  visada reikštų tą pačią būseną.
