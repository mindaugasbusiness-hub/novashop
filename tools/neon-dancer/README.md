# Neoninė šokėja (#12) — nebaigtas darbas, dabar paruoštas įdiegimui

**Data:** 2026-10-27 · **Projektas:** penktadienioaukcionas.lt (`/opt/aukcionas/app.py`)
**Būsena:** paruošta ir ištestuota (35/35 PASS) · **serveryje DAR NEĮDIEGTA** (šioje sesijoje nėra prieigos prie VPS)

---

## 1. Ką tai daro

Į kairįjį dalyvių panelį (`participants-panel`, `left:8px`, plotis 228 px) **po registracijos formos** (`#joinForm`), prieš „pp-done“ bloką, įdedama nedidelė neoninė video plokštė:

- video: `/photos/dance_club_12.mp4` — autoplay, muted, loop (be garso, be paspaudimo)
- aukštis: 160 px (registruotam — 172 px), plotis per visą panelį
- neoninis rėmelis su švelniu pulsuojančiu švytėjimu (`@keyframes neonDancerGlow`)
- apačioje kairėje smulki žymė „neon“
- **mobiliame (≤640 px) ir žemame ekrane (≤660 px) paslėpta**, kad neuždengtų formos
- `prefers-reduced-motion` — animacija išjungiama

Nieko netrina ir nepervardina: tik **įterpia** du blokus (CSS + HTML).

---

## 2. Failai

| Failas | Paskirtis |
|---|---|
| `patch_neon_dancer.py` | įrašo pakeitimą į `app.py` (su `.bak` kopija, su saugikliais) |
| `savitikra.py` | 35 patikrinimų ant **kopijos** — originalo neliečia |

Saugikliai `patch_neon_dancer.py` viduje:

- jei ieskomo teksto faile yra **ne 1 kartą** → STABDO ir nieko nerašo;
- jei jau įdiegta → sako „JAU IDIEGTA“ ir nieko nedaro (galima leisti daug kartų);
- prieš įrašymą daro `app.py.bak-neon-YYYYMMDD-HHMMSS`;
- išlaiko CRLF eilučių galus (failas Windows formato).

---

## 3. Kaip įdiegti (VPS)

```bash
# 1) nusiųsti įrankį į serverį
scp tools/neon-dancer/patch_neon_dancer.py root@<serveris>:/tmp/

# 2) SAUSAI patikrinti (nieko nerašo)
python3 /tmp/patch_neon_dancer.py --dry

# 3) įrašyti (padaro .bak kopiją)
python3 /tmp/patch_neon_dancer.py

# 4) paleisti svetainę iš naujo
systemctl restart aukcionas

# 5) patikrinti
curl -s http://127.0.0.1:8000/ | grep -c 'class="neon-dancer"'     # turi būti 1
ls -l /opt/aukcionas/photos/dance_club_12.mp4                      # turi egzistuoti
```

Jei naudojamas jų įrankis `_vps.py` (slaptažodis tik per `AUKC_PW`, niekada nespausdinamas):

```bash
AUKC_PW='...' python3 _vps.py --put tools/neon-dancer/patch_neon_dancer.py /tmp/patch_neon_dancer.py
AUKC_PW='...' python3 _vps.py "python3 /tmp/patch_neon_dancer.py --dry"
```

---

## 4. Grąžinimas atgal (jei nepatiks)

```bash
ls -lt /opt/aukcionas/app.py.bak-neon-* | head -3
cp /opt/aukcionas/app.py.bak-neon-20261027-220010 /opt/aukcionas/app.py   # savo datą
systemctl restart aukcionas
```

---

## 5. Patikra prieš įdiegiant (čia, be serverio)

```bash
git show origin/cline/ejzcxn55:_app_now.py > /tmp/neonbase/app_now.py   # bazinė kopija
python3 tools/neon-dancer/savitikra.py                                  # 35/35 PASS
```

`savitikra.py` tikrina: ankerių unikalumą, įterpimo vietą (po `#joinForm`, prieš `#ppDone`,
po `.participants-panel`), HTML/CSS vientisumą, skliaustų balansą, CRLF išsaugojimą,
naujų dubliuotų `id` nebuvimą, `.bak` kopijos turinį, idempotenciją, `.py` sintaksę
(`compile()`), `--dry` režimą ir tai, kad sugadintas ankeris **sustabdo** darbą.

---

## 6. Ko NEPATIKRINAU (sąžiningai)

- **Realaus vaizdo naršyklėje** — šioje sesijoje naršyklės nėra; patikrinta tik statinė struktūra.
- **Ar serverio `app.py` toks pat kaip bazinė kopija** (`_app_now.py`, 9599 eilutės, 2026-10-27).
  Jei skiriasi — patch **STABDO ir nieko nerašo** (tai saugu, bet reikės peržiūrėti ankerius).
- **Ar `/opt/aukcionas/photos/dance_club_12.mp4` tikrai yra** (sąraše `DANCER_WHITELIST` jis yra,
  bet failo aš nemačiau).
- **Kaip atrodo su tikru vaizdu** — video kadravimas `object-position:center 34%` gali prašyti
  pakoreguoti (viena eilutė CSS), kai pamatysi gyvai.
