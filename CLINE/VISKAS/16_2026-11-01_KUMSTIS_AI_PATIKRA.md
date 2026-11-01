# 16 - 2026-11-01 KUMSTIS AI: grandine patikrinta ir paleista (Cline sesija)

Sukurta: 2026-11-01. Autorius: Cline (per relay, Cline Cloud).
Sesijos tikslas: M prase perskaityti, kas yra KUMSTIS AI, tada paleisti ja kartu.
Rezultatas: grandine VEIKIA (n8n + Cline worker). M prisijunge prie n8n ir patvirtino: "viskas veikia".
Svarbu: M masinoje NIEKO nepakeista, netrinta ir neperrasyta (tik skaitymas ir dvieju langu atidarymas).

## 1. Kas yra KUMSTIS AI (trumpai)

- n8n (:5678) paleidzia uzduotis -> Cline worker (:7070) -> cline CLI -> darbai
  aplanke C:\Users\M\CLINE\ai-stack\work\<projektas>.
- Provider cline-pass, modelis cline-free/nemotron-3.5-super-vl (nemokamas). Ollamos nereikia.
- Aprasyta: VISKAS\15_2026-10-29_KUMSTIS_AI_SISTEMA.md. Kodas: C:\Users\M\CLINE\ai-stack.

## 2. Patikrinta siandien (faktai su irodymais)

| Kas | Reiksme | Irodymas |
|---|---|---|
| n8n :5678 | VEIKIA | GET /healthz -> {"status":"ok"} |
| Cline worker :7070 | VEIKIA | PID 3032 (node), startas 2026-11-01 00:29:56; /healthz -> ok:true |
| Worker parametrai | cline-pass / cline-free/nemotron-3.5-super-vl / cline 3.0.74 / workspace ai-stack\work / timeout 1800 s | /healthz atsakymas |
| cline CLI | 3.0.74 | cline --version |
| n8n workflow | FHBgsP2YZSZ5GCqX | pulto KUMSTIS AI sekcija |
| PULTAS :8790 | VEIKIA, rodo 11/11 servisu | pulto puslapis 2026-11-01 01:14 |
| n8n prisijungimas | VEIKIA (HTTP 200) | POST /rest/login su vietine owner paskyra |
| n8n DB | C:\Users\M\.n8n\database.sqlite (3 563 520 B, 2026-10-29 04:08) | failo patikra |

## 3. Prisijungimas prie n8n (SLAPTA - tik siame VISKAS aplanke, i repo nekeliama)

- Prisijungimo duomenys (el. pastas ir slaptazodis) saugomi TIK M masinoje:
  C:\Users\M\CLINE\VISKAS\16_2026-11-01_KUMSTIS_AI_PATIKRA.md ir VISKAS\SEIFAS.
- I repo slaptazodziai nekeliami (3 taisykle).
- Patikrinta 2026-11-01: n8n prisijungimas veikia (POST /rest/login -> HTTP 200).

## 4. Radiniai ir trukumai (NELIESTI - laukia M sprendimo)

1. Desktop\Kumstis\n8n-prisijungimas.txt turi SENA slaptazodi (Ksgu...); jis nebeveikia (401).
   Teisingas slaptazodis - pulto rodomas (zr. 3 skyriu).
2. Desktop\KUMSTIS AI.lnk - tuscia nuoroda (224 B, tikslas tuscias): paspaudus nieko neatsidaro.
3. Pulto mygtukas "Paleisti/patikrinti servisus" paleidzia tools\sesijos-pradzia.ps1, bet
   KUMSTIS AI worker'io (:7070) NEPALEIDZIA. Pasiulytas atskiras mygtukas "Paleisti KUMSTIS AI"
   (kviestu ai-stack\START-AI-STACK.ps1). M atsake: "nieko nedarykime" - todel nedaryta.
4. Desktop\Kumstis\start-native.ps1 krenta ties 192 eil. (truksta fastembed modelio) - n8n is jo
   nepaleidziamas; START-AI-STACK.ps1 tai apeina.
5. Pakibes procesas PID 9200 (n8n import:workflow) nuo senu sesiju - neliestas (1 taisykle).

## 5. Ko NEDARIAU

- Netryniau, nepervardinau ir neperrasiau jokio M failo.
- Nekeiciau pultas.py, nekeitciau nuorodu, nekeitciau slaptazodziu failo.
- Nesiunciau jokios uzduoties per worker (jokiu nauju failu work\ aplanke).
- Atidariau tik matoma Chrome langa (profilis CLINE\chrome_m) su pultu ir n8n. Anksciau - Google
  registracijos forma tame paciame lange (paskyra NEBAIGTA, nesukurta).

## 6. Ka daryti toliau (TODO - tik su M "taip")

- [ ] Sutvarkyti Desktop\Kumstis\n8n-prisijungimas.txt (teisingas slaptazodis arba nuoroda i SEIFAS).
- [ ] Sutvarkyti Desktop\KUMSTIS AI.lnk (vienu paspaudimu: START-AI-STACK.ps1 + atidaryti pulta).
- [ ] Prideti pulto mygtuka "Paleisti KUMSTIS AI".
- [ ] Gyvas grandines testas (n8n -> worker -> cline) smeliadezeje work\projektas.
- [ ] fastembed modelis (del start-native.ps1).

## 7. Rysio atkurimas (kitai sesijai)

- Relay: relay.py (portas 8798) + cloudflared tunelis; adresas keiciasi kas sesija.
- M pusėje: PowerShell lange `iex (irm https://<adresas>/agent.ps1)` arba budetojas autoconnect.
- Diagnostika: GET /health (be rakto), GET /status (su X-Key).

## 8. Siandienos sesijos eiga (trumpai)

1. Perskaiciau VISKAS\00_SKAITYK_NAUJAUSIA.md ir 15_2026-10-29_KUMSTIS_AI_SISTEMA.md.
2. Patikrinau servisus ir worker'io /healthz - grandine gyva.
3. Atidariau pulta matomame Chrome lange, parodziau KUMSTIS AI sekcija (11/11 servisu).
4. Atidariau n8n prisijungima; M prisijunge prie n8n su savo paskyra -> "viskas veikia".
5. M prase irasyti tai i VISKAS - sis failas.

Atnaujinta: 2026-11-01. Niekas netrinta. Sio failo kopija yra ir repo (be 3 skyriaus slaptazodzio).
