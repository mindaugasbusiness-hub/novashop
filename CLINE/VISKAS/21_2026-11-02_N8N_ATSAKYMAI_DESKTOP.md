# 21 - 2026-11-02 N8N: AI atsakymai automatiškai į Desktop\n8n_atsakymai

Sukurta: 2026-11-02. Autorius: Cline (per relay). M užduotis: "sutvarkyk n8n, kad AI agento atsakymai
automatiškai išsaugotųsi Desktop aplanke".

## 1. Rezultatas (patikrinta gyvai)

- Workflow `FHBgsP2YZSZ5GCqX` ("CLINE - uzduotis Cline worker") papildytas 3 mazgais:
  - `Issaugoti: text` (Set) — laukas `text` = `{{ $json.text }}`
  - `Failas: tekstas` (Convert to File, toText, sourceProperty `text`, binaryPropertyName `data`,
    options.fileName `=ataskaita_{{ $now.format('yyyy-MM-dd_HH-mm-ss') }}.md`, encoding `utf8`)
  - `Rasyti i Desktop` (Read/Write Files, write, fileName
    `=C:\Users\M\Desktop\n8n_atsakymai\ataskaita_{{ $now.format('yyyy-MM-dd_HH-mm-ss') }}.md`,
    dataPropertyName `data`)
- Prijungta prie mazgo "Ar pavyko?" SĖKMĖS šakos (lygiagrečiai su "OK: ataskaita"). Seni 6 mazgai nekeisti.
- Patikrinta: paleidus workflow (execution 428) atsirado
  `C:\Users\M\Desktop\n8n_atsakymai\ataskaita_2026-11-02_13-56-28.md` (3261 B), viduje visas AI atsakymas,
  lietuviškos raidės teisingos (UTF-8).

## 2. Ką reikėjo pataisyti, kad veiktų (svarbu ateičiai)

1. **Failų prieigos riba (n8n 2.x)**: `n8n-core` pagal nutylėjimą leidžia rašyti tik į `~/.n8n-files`
   (SecurityConfig `restrictFileAccessTo`). Be to mazgas "Read/Write Files from Disk" mėtydavo
   "Access to the file is not allowed."
   Sprendimas: `C:\Users\M\Desktop\Kumstis\.env` pridėta eilutė
   `N8N_RESTRICT_FILE_ACCESS_TO=C:\Users\M\Desktop\Kumstis\DeFi ataskaitos;C:\Users\M\Desktop\n8n_atsakymai`
   (kopija: `.env.bak-2026-11-02`). Reikalingas n8n perkrovimas.
2. **Workflow reikia PUBLIKUOTI**: n8n 2.x turi versijavimą. PATCH įrašo tik juodraštį; vykdoma yra
   paskelbta versija (`activeVersionId`). Reikia `POST /rest/workflows/<id>/activate` su
   `{"versionId": "<naujas>"}`.
3. **Išraiška privalo prasidėti `=`**: be `=` n8n laiko tekstą pažodžiui. Todėl pirmas bandymas sukūrė
   failą, pavadintą tiesiog `{{ $binary.data.fileName }}`.
4. **`$binary.data.fileName` tame mazge neveikia** (vardo dalis likdavo neįvertinta). Naudojama tiesioginė
   išraiška su `$now.format(...)` — veikia.

## 3. Prisijungimas prie n8n (veikiantis, 2026-11-02)

- `POST http://127.0.0.1:5678/rest/login` su `{"emailOrLdapLoginId":"m@kumstis.local","password":"<SEIFAS>","browserId":"..."}`
- Atsakymo slapukas `n8n-auth` yra **Secure** → PowerShell `Invoke-WebRequest -WebSession` jo per http
  NESIUNČIA (gaunama 401). Reikia siųsti rankiniu `Cookie:` antrašte.
- `Desktop\Kumstis\n8n-prisijungimas.txt` slaptažodis (Ksgu...) NEBEVEIKIA. Galiojantis slaptažodis —
  VISKAS\16_2026-11-01_KUMSTIS_AI_PATIKRA.md 3 skyriuje.
- n8n CLI (`n8n execute --id`) NETINKA: reikalauja "Execute Workflow Trigger" mazgo, o brokerio portas
  5679 konfliktuoja su veikiančiu n8n.

## 4. Kaip paleisti rankiniu būdu (be laukimo iki grafiko)

```
POST /rest/workflows/FHBgsP2YZSZ5GCqX/run
body: {"triggerToStartFrom": {"name": "Kas 6 val."}}
```

## 5. Liko / pasiūlymai (NEDARYTA be M leidimo)

- Aplanke liko techninis failas `{{ $binary.data.fileName }}` (6596 B) iš pirmų bandymų — NETRINTA.
- Failo vardo laikas imamas Europe/Vilnius (13-56), o M Windows laikrodis rodo 03-56 (skiriasi 10 h).
- Jei norima kaip AUTO-PAIESKA: papildomai generuoti ir `.html` (DeFi stilius) bei `.csv`.
