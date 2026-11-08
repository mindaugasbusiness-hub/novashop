# tools/rizikos — „KA PRARANDU?“ patikra ir saugus taisymas

Pultas rodo ataskaitą **KA PRARANDU?** (3 rizikos: `workflow`, `kopija`, `rag-testas`),
bet nepasako, *kodėl* rizika yra ir *ką konkrečiai prarandi*. Šis įrankis tą padaro
vienu paleidimu ir, jei prašai, paleidžia tavo paties taisymo įrankius.

**Pagrindinė taisyklė Nr.1: įrankis NIEKO NETRINA.** Numatytuoju režimu jis tik
skaito (tinklą, failus, `schtasks /query`). Vienintelis įrašymas — ataskaitos failas,
ir tik jei nurodai `--isvestis`.

---

## 1. Ką tikrina

| Kategorija | Ką daro | Kada rizika |
|---|---|---|
| `workflow` | `:5678` prievadas → `/healthz` → `GET /api/v1/workflows` su `X-N8N-API-KEY` | n8n nepaleistas, procesas kabo, nėra rakto `.env`, raktas atmestas (401), API išjungtas (404) |
| `kopija` | naujausio aplanko `BACKUPS_VPS` ir `BACKUPS` amžius | seniau nei **20 h** (tavo `swiss.ps1` taisyklė) → `PASENUSI_KOPIJA` |
| `rag-testas` | randa `tools\rag*test*.py`, paleidžia jį, iš `%` išveda kokybę; papildomai tikrina Qdrant `:6333` ir embeddings `:8090` | kokybė < **70 %** → `ZEMA_KOKYBE` |
| `grafikai` | `schtasks /query /fo csv /v` — tik `CLINE*` darbai (be `(!)` = ne „Ready“) | grafikas išjungtas → kopija nebus daroma automatiškai |

Kiekvienai būsenai ataskaita parašo ir **„Ka prarandi“** eilutę paprastais žodžiais
(pvz. pasenusi kopija → „jei VPS užlinksta, neturi ko atstatyti“).

---

## 2. Paleidimas

```powershell
# paprasta patikra (nieko nekeičia, nieko netrina)
python C:\Users\M\CLINE\tools\rizikos\ka-prarandu.py

# ta pati patikra + pilna ataskaita į failą (failo į pokalbį NEkelti)
python C:\Users\M\CLINE\tools\rizikos\ka-prarandu.py --isvestis C:\Users\M\CLINE\RIZIKOS_ATASKAITA.txt

# taisymas: paleidžia swiss.ps1 ir/arba backup_vps.py — TIK po „taip“
python C:\Users\M\CLINE\tools\rizikos\ka-prarandu.py --taisyti

# be klausimo (jei nori į grafiką)
python C:\Users\M\CLINE\tools\rizikos\ka-prarandu.py --taisyti --tyliai --isvestis C:\Users\M\CLINE\RIZIKOS_ATASKAITA.txt
```

Išvesties kodai: `0` — rizikų nėra, `1` — rasta rizikų, `2` — netikėta klaida.

### Parametrai

| Parametras | Numatytas | Paskirtis |
|---|---|---|
| `--clines-dir` | `C:\Users\M\CLINE` | kur ieškoti `BACKUPS*`, `tools\`, `07_ZINIOS.md` |
| `--n8n-url` | `http://127.0.0.1:5678` | n8n adresas |
| `--raktas` / `--raktas-failas` | — | API raktas tiesiogiai arba iš `.env` |
| `--riba-h` | `20` | kopijos amžiaus riba valandomis |
| `--rag-riba` | `70` | RAG kokybės riba procentais |
| `--be-rag` / `--be-grafiku` | — | praleisti atitinkamą patikrą |
| `--isvestis` | — | kur įrašyti pilną ataskaitą + JSON detales |
| `--taisyti` / `--tyliai` | — | vykdyti taisymą (be/with patvirtinimo) |

---

## 3. Ką tiksliai daro `--taisyti`

| Rizika | Veiksmas | Kodėl saugu |
|---|---|---|
| `workflow` = `NEPALEISTAS` / `SERVERIS_NEGYVAS` | `powershell -File tools\swiss.ps1 -Quiet` (jei nėra — `tools\n8n\restart-n8n.ps1`) | tai tavo paties atkūrimo įrankis: paleidžia servisus, pultą, padaro kopijas jei pasenę |
| `kopija` = `PASENUSI_KOPIJA` / `NERA_KOPIJU` | `python tools\backup_vps.py` (jei nėra — `tools\auto-backup.ps1`) | tik kuria naują kopiją |
| `workflow` = `NERA_RAKTO` / `RAKTAS_NEGALIOJAS` | **nieko** — tik nurodo, kur įrašyti `N8N_API_KEY` | rakto įrankis negeneruoja ir nespausdina |
| `rag-testas` = `ZEMA_KOKYBE` | **nieko** — atmintis yra turinys, ne servisas | žinių bazę papildai tu (ar agentas) sąmoningai, ne automatu |

Po taisymo įrankis **pakartotinai patikrina** ir parodo, ar rizika dingo.

---

## 4. Ką daryti su trimis šios dienos rizikomis

1. **`workflow` — „nepavyko prisijungti prie n8n“**
   `python ...\ka-prarandu.py` parodys tikslią priežastį:
   `NEPALEISTAS` → `swiss.ps1`; `NERA_RAKTO` → įrašyti `N8N_API_KEY` į
   `C:\Users\M\Desktop\Kumstis\.env` (n8n UI: *Settings → n8n API → Create an API key*);
   `RAKTAS_NEGALIOJAS` → tas pats, tik raktą pakeisti.

2. **`kopija` — „VPS kopija sena 47,4 h“**
   `python ...\ka-prarandu.py --taisyti` → `backup_vps.py`. Jei pasikartos rytoj —
   žiūrėk `grafikai` sekciją: darbas `VPS kopijos` (03:30) greičiausiai „Disabled“.

3. **`rag-testas` — „RAG kokybė 50 %“**
   Įrankis parodo, ar testas išvis yra ir kur, bei ar gyvi `:6333` (Qdrant) ir `:8090`
   (embeddings). Jei servisai neklauso — kokybė krenta be jokio turinio pakeitimo.
   Jei servisai gyvi — reikia papildyti `07_ZINIOS.md` tais klausimais, kurie teste
   atsakyti neteisingai (testo išvedimas įrašomas į `--isvestis` failą).

---

## 5. Įjungimas į grafiką (neprivaloma, nedaro nieko destruktyvaus)

```powershell
schtasks /Create /TN "CLINE Rizikos patikra" /SC DAILY /ST 07:45 /F ^
  /TR "python C:\Users\M\CLINE\tools\rizikos\ka-prarandu.py --isvestis C:\Users\M\CLINE\RIZIKOS_ATASKAITA.txt"
```

---

## 6. Sandara

| Funkcija | Paskirtis |
|---|---|
| `tikrinti_n8n` | prievadas → `/healthz` → `/api/v1/workflows`, būsenų taksonomija |
| `tikrinti_kopijas` | `BACKUPS_VPS` / `BACKUPS` naujausio įrašo amžius |
| `tikrinti_rag` | testo paieška ir paleidimas, `%` nuskaitymas, Qdrant/embeddings patikra |
| `tikrinti_grafikus` | `CLINE*` planuotojo darbai |
| `sudaryti_ataskaita` | trumpa ataskaita (≤ ~45 eil.) + „Ka prarandi“ |
| `vykdyti_taisymus` | veiksmų planas → patvirtinimas → paleidimas |

## 7. Testavimas

Įrankis neturi išorinių priklausomybių (tik Python stdlib), todėl testuojamas be n8n:

```bash
python3 tools/rizikos/ka-prarandu.py --clines-dir /tmp/tcline --be-grafiku --be-rag
python3 tools/rizikos/ka-prarandu.py --clines-dir /tmp/tcline --n8n-url http://127.0.0.1:5999 --be-grafiku
```

Patikrintos būsenos: `NEPALEISTAS`, `NERA_RAKTO`, `RAKTAS_NEGALIOJAS` (401), `GERAI`,
`PASENUSI_KOPIJA`, `ZEMA_KOKYBE`, `GERAI` (92 %), taip pat `--taisyti` su atšaukimu
ir su `--tyliai`.
