# ATSTATYMO TAŠKŲ REGISTRAS

Naujausi viršuje. Kiekvienas taškas turi tris dalis: git žymą, mašinos kopiją, VPS kopiją.

| Nr. | Data | Git žyma | Mašinos kopija | VPS kopija | Būsena tą akimirką | Pastaba |
|---|---|---|---|---|---|---|
| **1** | 2026-10-31 | `atstatymas-1` | ⏳ reikia `sukurkti-taskas.ps1 -Numer 1` | ⏳ reikia `vps-taskas.sh sukurkti 1` | **11/11 servisai, svetainė 200** | Auksinė būsena, patvirtinta direktoriaus. Aprašas: `01_TASKAS.md` |

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
