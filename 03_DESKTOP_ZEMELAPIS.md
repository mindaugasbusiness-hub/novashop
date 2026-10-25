# 03_DESKTOP_ZEMELAPIS — ką radau M kompiuteryje (2026-10-25)

> **Jokių slaptažodžių čia nėra ir nebus** — repo yra viešas. Slaptažodžių vietos nurodytos
> tik failų keliais. Visi raktai nuskaityti 2026-10-25 ir laikomi tik Cline sesijos atmintyje.

## 1. Sistema
- Kompiuteris: **DESKTOP-7LPGR90**, paskyra `desktop-7lpgr90\m`, Windows 10 Pro
- `C:` ~47 GB laisva · `D:` CD/DVD įrenginys (ne diskas)
- Node.js `C:\Program Files\nodejs\node.exe` · Python `C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe`
- git: PortableGit 2.56.0 → `C:\Users\M\CLINE\git\bin\git.exe`
- Docker įdiegtas, daemon neįjungtas

## 2. Vietiniai servisai (portai)
| Portas | Servisas |
|---|---|
| 5678 | n8n (Kumstis) |
| 5679 | task broker |
| 6333 | Qdrant |
| 8090 | Kumštis tools (finansai + embeddings) |
| 8091 | Žvėris UI (`/api/status`, llama3.3-abliterated:70b) |
| 8099 | Naršyklės daemonas (`browsed.js`, Playwright) |
| 8766 | F6 dainų panelis (`/api/list`) |
| 8790 | **VALDYMO PULTAS** (`pultas\pultas.py`) |
| 9222 | Chrome CDP (šiuo metu NE) |

## 3. VPS
- `root@5.175.171.113` (HostBrr, serveris „penktadienio", Ubuntu 24.04)
- **Prieiga veikia per raktą** `C:\Users\M\CLINE\ssh\vps_cline` (patikrinta 2026-10-25)
- systemd: `aukcionas`, `vilko-mokykla`, `cloudflared-penktadienio`, `vilkas-tts`
- `/opt/aukcionas/`: `app.py` (aukciono svetainė), `ivr.py` (Twilio IVR), `voice/` (edge-tts mp3),
  `voicebox/` (balso žinutės), `desk_songs/` (31 failas), `smegenys.json` (253 frazės, 9 intonacijos),
  `vilko_mokykla/`, `.env`
- `/opt/vps-watchdog.sh` + cron kas 5 min → `/var/log/vilkas-watchdog.log`
- Svetainė: https://penktadienioaukcionas.lt

## 4. Desktop projektai (dydis | failai)
| Projektas | Dydis | Failai |
|---|---|---|
| pakeitimai 111 | 59,6 GB | 20 996 |
| vid | 31,2 GB | 99 296 |
| New folder (Camera 5,5 GB + Screenshots 1 246) | 5,8 GB | 1 520 |
| Kumstis (n8n + agentai) | 4,3 GB | 298 131 |
| atstatyk izanga | 367,8 MB | 71 |
| pataisymai_arciausiai_originalo_2026-10-06 | 107,3 MB | 185 |
| IZANGA_FONAS (Muzika_Desktop 149,5 MB) | 150,4 MB | 35 |
| fable kodas vilko auksionui | 25,5 MB | 293 |
| aukciono prekes | 5 MB | 112 |
| SecurityWatch · senos_versijos · bordako sutvarkymas · oly bet · 2026010.24d | ~0 | 3–9 |

`pakeitimai 111` numeruoti subprojektai (pagrindiniai): `02_Aukcionas_Karstas_Lotas` (494 f,
desk_songs 29, vps_pack 240, photos 122), `04_Vinted_ir_Facebook_Watcher` (3 598 f, ByModel 369),
`03_Prekiu_idejimas_auto`, `06_Vast_AI_Linux`, `08_Vinted`, `10_AusesIrBalsas_Whisper_LT`,
`15_Nuoma_Platforma`, `17_Decentralizuotas_Smart_Kontraktas`, `18_Balsu_Agentas_Call`,
`19_Vilkas_Local_TTS`, `PERKELIMAS_KITAM_KOMPIUTERIUI_BE_SLAPTAZODZIU_20261012` (226 f).

## 5. CLINE atmintis (`C:\Users\M\CLINE\`)
| Failas | Turinys |
|---|---|
| `00_START_HERE.md` | pradžia, taisyklė Nr.1, kaip prisijungti (A/B variantai) |
| `01_PROJEKTAI.md` | sistema, projektai, autostart, servisai |
| `02_DIENORASTIS.md` | dienoraštis (naujausia viršuje) |
| `03_TAISYKLES.md` | taisyklės (Nr.1 – nieko netrinti; Nr.10 – neliesti M programų; Nr.11 – Gmail/kritiniai tik pagrindinis Cline) |
| `04_TODO.md` | ką daryti toliau |
| `05_TAISYKLE-NR1.md` | sutrumpinta Nr.1 |
| `06_INVENTORIUS.md` | inventorius |
| `07_ZINIOS.md` | žinių bazė |
| `09_PAKEITIMAI.md` | pakeitimų žurnalas (60+ įrašų su backup keliais) |
| `10_SAUGUMAS.md` | saugumas |
| `INVENTORIUS\01–08` | aplankų medis (889), failų indeksas (8 582), svarbiausi (1 263), raktai (1 337), naujausi, projektų ir raktų katalogai, Vilko mokyklos analizė |
| `tools\` | `backup.ps1`, `connect.ps1`, `backup_vps.py`, `twilio_ivr_set.py`, `sesijos-pradzia.ps1`, `auto-backup.ps1`, `swiss.ps1`, `setup-new-pc.ps1` |
| `pultas\` | `pultas.py` (+ `.bak-2026-10-25-cline`), `start-pultas.cmd`, `KAIP_PALEISTI.txt` |
| `browser\` | `browsed.js` (Playwright daemonas, :8099) |
| `n8n\` | `aukciono-stebejimas.json` |
| `kripto\` | `pinigine.py`, `pf_verify.py`, `contract_check.py`, `README.md`, `seklos.json` |
| `ssh\` | `vps_cline` (privatus raktas), `known_hosts` |
| `BACKUPS\`, `BACKUPS_VPS\`, `TRASH\` | kopijos, šiukšlinė (nieko netrinti) |
| `PERKELIMAS\` | `cline-PILNAS-2026-10-24.7z`, `1-ATKURTI-VISKA.cmd` |

## 6. Grafikai (Task Scheduler, `CLINE*`)
AutoBackup 03:00 · VPS kopijos 03:30 · HealthCheck 08:00 · Būdėjimas kas 5 min ·
PreFlight penktadieniais 17:30 · Perkėlimas sekmadieniais 04:00

## 7. Kur yra prisijungimai (tik vietos, ne reikšmės)
- `Desktop\pakeitimai 111\00_KUR_SLAPTAZODZIAI.txt` — **pagrindinis sąrašas**
- `Desktop\pakeitimai 111\00_MASTER_KAS_KUR_IR_SEIFAS.txt` — kur kas ir seifas
- `Desktop\pakeitimai 111\PERKELIMAS_...\SEIFAS_PRIVATUS_NEPLATINTI\` — **seifas (55 failai)**:
  HostBrr/VPS, vast.ai ×4, Binance, Bybit, Spectrocoin, ElevenLabs, OpenRouter, Meistrų portalai,
  Google/SEO, Twilio `.env`, SIP/Linphone, Vinted, Nuoma, `SSH\`
- `Desktop\pakeitimai 111\00_SESIJA_YYYY-MM-DD_SUVESTINE_IR_SEIFAS.txt` — sesijų suvestinės
- VPS `.env` failai (`/opt/aukcionas/.env`, `18_Balsu_Agentas_Call\.env` ir kt.)

## 8. Saugumo pastaba
Viešame `novashop` repo (šaka `cline/ejzcxn55`) yra VPS root slaptažodis. Prieiga prie VPS
**veikia per raktą**, tad slaptažodžio keitimas nieko nesugadintų, o nutekėjimą uždarytų.
M nurodė repo nevalyti — sprendimas jo.
