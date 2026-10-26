# 03 · TAISYKLĖS (ko NEGALIMA)

Atnaujinta: 2026-10-26

1. **NIEKO NETRINTI ir nearchyvuoti be direktoriaus žodžio.** Jei failas atrodo nereikalingas — pasakyti, ne trinti.
2. **`main` šaka neliečiama.** Visas darbas — atskiroje šakoje (`cline/<sesijos-id>`).
3. **Nesakyti „peržiūrėk puslapį / panelę“.** Puslapio HTML pokalbyje kainuoja ~25 000 tokenų — tai jau yra nulaužę kontekstą. Vietoj to: ataskaita arba `pc.py cmd --lines N`.
4. **Nekelti viso failo į pokalbį.** Didelis išvedimas → failas, ekrane tik pradžia.
5. **Nesakyti, kad kažkas veikia, nepatikrinus.** Kiekvienas „veikia“ turi turėti patikrinimo būdą (`test-relay.py`, `curl`, `node --check`).
6. **Adresų lentos neskelbti viešai.** `lenta.py skelbti` be `--force` atsisako, kol repo viešas. Tai sąmoningas saugiklis, ne gedimas.
7. **Raktų ir slaptažodžių nerašyti į viešą repo.** (Istorijoje yra nutekėjęs VPS root slaptažodis šakoje `cline/ejzcxn55` — priminti direktoriui, nesiimti patiems.)
8. **Ilgų `-Recurse` per visą diską per relay — venk.** Blokuoja komandų eilę iki 5 min.
