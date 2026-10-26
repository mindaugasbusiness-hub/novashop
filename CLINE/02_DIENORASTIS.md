# 02 · DIENORASTIS

Naujausi įrašai viršuje. Kiekvienas įrašas: ką dariau, ką patikrinau, ko NEDARIAU ir kodėl.

---

## 2026-10-26 — Sesija: atrama perkelta į git

### Ką dariau
1. Patikrinau, ar sesijoje yra `C:\Users\M\CLINE\` ir atminties failai → **nėra** (`/mnt` tuščias, jokio Windows disko, jokio PowerShell).
2. Patikrinau repo: `mindaugasbusiness-hub/novashop`, `main` = `b3f1915` („Add support section with 24/7 help choices“), darbinis kelias /workspace.
3. Sukūriau darbinį branch `cline/7at5cm57` (nuo `main`, švarus statusas).
4. Patikrinau, ar repo viduje yra pėdsakų apie n8n / trycloudflare / `agent.ps1` / sargą → **nerasta jokių** (grep per visus failus, išskyrus `.git`).
5. Paleidau statinę parduotuvę ir patikrinau, kad ji tikrai dirba:
   - `python3 -m http.server` → `index.html` **200 OK** (8375 baitai), `app.js` **200 OK**, `styles.css` **200 OK**.
6. Sukūriau šiuos atminties failus repo viduje: `CLINE/00_START_HERE.md`, `02_DIENORASTIS.md`, `03_TAISYKLES.md`, `04_TODO.md`.

### Patikrinta būsena (kodas)
- `app.js`: `const STORE_PAUSED = true;` → parduotuvė **laikinai uždaryta**. Užsakymo forma išjungiama (laukai `disabled`, permatomumas 0.45, `pointer-events: none`), rodomas pranešimas „Parduotuvė laikinai neveikia. Užsakymai ir mokėjimai laikinai išjungti.“
- `index.html`: viršuje yra `paused-banner`, skyrius „Pagalba 24/7“ su 3 kortelėmis (🤖 Robotukas / 👤 Gyvas žmogus / ☎️ Skubus kontaktas), mygtukas `tel:+37060000000` su žyma „(ne svarbu, neskambinti)“.
- Katalogas: 8 produktai, filtrai (visi / tech / sport / home), krepšelis `Map()` pagrindu, pristatymas 3.99 €, nemokamas nuo 75 €.

### Ko NEDARIAU ir kodėl
- **Nekūriau darbalaukio nuorodų** „CLINE RYSYS“ / „CLINE - PRADZIA“ — šioje sesijoje nėra darbalaukio nei `.lnk` galimybės. Jei anksčiau tokios nuorodos buvo sukurtos, jos yra tavo kompiuteryje, ne čia.
- **Neskelbiau jokio tunelio adreso** — jis numirtų kartu su šia sesija, o aš nežadu to, ko negaliu išpildyti rytoj.
- **Neliečiau `main`** ir nieko netryniau (žr. `03_TAISYKLES.md`).
- **Neįrašiau jokių „slaptažodžių“ ar raktų** — n8n buvo minėtas kaip paleistas „be raktų“; repo viduje raktų nėra ir neturi būti.

### Įspėjimas ateičiai (kad nebekartočiau klaidų)
Ankstesni bandymai jungtis nepavyko: SSH → 404, pinggy → slaptažodis, bore → antivirusas. Priežastis bendra: **agentas debesyse neturi prieigos prie tavo kompiuterio**, tad jokie „įėjimo taškai“ į tavo mašiną iš čia neveiks patikimai. Vietoj to naudojam git — jis praeina visur.