# 60 - 2026-11-08 K2 + GROQ: PILNAS SISTEMOS PERJUNGIMAS NEMOKAMAI

**M nurodymas:** „K2 eis per Groq nemokamai, bet visa sistema islieka ta pati (algoritmine + sena).
K1 eina kaip buvo. K2 per Groq.“

## 1. KODEL BUVO SUSTOJUSIOS ATASKAITOS (visur)
Ne n8n ir ne failu teises, o **Cline saskaitos balansas**:
`"Insufficient balance. Your Cline Credits balance is $-0.11"` (provider `cline-pass`,
modelis `reflection/beam-free`). Net „free“ Beam neveikia su neigiamu balansu.
→ K1 ataskaitos neis, kol balansas neigiamas (arba kol ir K1 nebus perjungtas i Groq).

## 2. KAS PADARYTA K2 (2026-11-08)

### 2.1 Groq raktas
- `.env` faile `C:\Users\viliu\CLINE\ai-stack\.env` → `GROQ_API_KEY=...` (56 simboliai)
- **SVARBU:** PowerShell `Set-Content -Encoding UTF8` prideda **BOM** → agentas rakto nemato.
  Taisymas: rasyti per Python su `encoding="utf-8"` be BOM.
- **Raktas buvo ikeltas i pokalbi → laikyti nutekejusiu; pakeisti (Delete → Create).**

### 2.2 Modeliai (patikrinta su tuo raktu, 1 zodzio testas)
| Modelis | Busena | Kvota (nemokama) |
|---|---|---|
| `openai/gpt-oss-120b` | OK | 30/min, 1 000/d, 8k zetonu/min, 200k zetonu/d |
| `openai/gpt-oss-20b` | OK | tas pats |
| `qwen/qwen3.8-27b` | OK | tas pats |
| `allam-2-7b` | OK | **7 000 uzkl./d**, 6k zetonu/min |
| `openai/gpt-oss-safeguard-20b` | OK | 200k zetonu/d |
| Llama pokalbiu modeliai (`llama-3.3-70b` ir kt.) | **NEBERA saskaitoje** | – |
| whisper-large-v3 / turbo | OK (garsas) | 7,2k garso s/d |

Kvotos **atskiros kiekvienam modeliui** → 3 modeliai ≈ 600 000 zetonu/d.
`web_agent` automatsikai pereina prie kito modelio, kai gauna HTTP 429.

### 2.3 Sukurti / pakeisti failai (visi su .bak)
| Failas | Paskirtis |
|---|---|
| `ai-stack\web_agent.py` | Playwright atidaro puslapi → Groq atsako → iraso i `Desktop\n8n_atsakymai\agent_*.md`. Paprasti klausimai (be URL) – atsakomi **be narsykles**. |
| `ai-stack\tool_agent.py` | **Mini-agentas** `120b` + irankiai: `list_dir`, `read_file`, `read_log`, `check_port`, `write_file`, `run_powershell`. Rasykimas/PowerShell – TIK su `--leisti-keitimus`; trynimas blokuojamas visada. Iki 8 zingsniu. |
| `ai-stack\agent_server.py` | HTTP serveris **:7070**: `GET /` (puslapis), `POST /run`, `POST /agent`, `GET /usage`, `GET /healthz`. Autentifikacija `x-worker-token`. Vykdo agenta TAME paciame procese (be subprocess koduotes problemu). |
| `ai-stack\browser_agent.py` | Suderinamumo wrapper → `web_agent` |
| `ai-stack\start-agent-server.ps1` | Paleidiklis |
| `ai-stack\start-worker.ps1` | Pataisyta: pilnas `node.exe` kelias + `CLINE_ENTRY` |
| `pultas\pultas.py` | **Juodasis sarasas**: istrinta uzduotis nebegrizta is jokio saltinio; „Vykdyti dabar“ visada leidzia; `null` nebeirasoma kaip „None“ |
| `tools\automation_server.py` + 4 pagalbiniai | Atkelti is K1 (buvo :8792 neklausantis → workflow krito kas 2 min) |
| `07_ZINIOS.md` | Atkeltas is K1 (K2 neturejo) |
| `VISKAS\viskas-atnaujinti.ps1` | Atkeltas is K1 |

Visuose atkeliamuose failuose **53 keliai** pakeisti `C:\Users\M` → `C:\Users\viliu`.

### 2.4 Autostart (be admin, per Startup aplanka)
`%APPDATA%\...\Startup\`: `CLINE-K2-DI-AGENTAS.cmd` (7070), `CLINE-K2-AUTOMATIKA.cmd` (8792),
`CLINE-K2-PULTAS.cmd` (8790). `schtasks` davė „Access is denied“ – todel Startup.

### 2.5 Narsykles
- **Chrome idiegtas** (per admin skripta).
- **Brave:** registro irasas pasalintas, vartotojo duomenys istrinti (245 MB).
  `C:\Program Files\BraveSoftware` (1,09 GB) liko – reikia admin (skriptas darbalaukyje).

## 3. KAS VEIKIA (patikrinta gyvai)
| Testas | Rezultatas |
|---|---|
| `POST :7070/run` „labas“ | `ok=true`, „Labas!“ (~0,4 s) |
| `POST :7070/agent` „kiek md VISKAS“ | `ok=true`, veiksmai: check_port ×2, list_dir → „8 .md failai“ |
| Pultas → n8n → Groq („labas is pulto“) | uzduotis `20261108-164506-14` → **busena „baigta“**, failas `agent_2026-11-08_16-45-17.md` |
| K2 atmintis (VISKAS raso) | execution'ai `success`, VISKAS failai 5 → 8 |
| Juodasis sarasas | istrinta → pakartotinai nekuriama; rankinis – leidziamas |
| Puslapio JS | `node --check` = 0 (sintakse svari) |
| Kvota `/usage` | 4 modeliu duomenys realiu laiku |

## 4. N8N GRANDINE (nepakeista – tik „protas“ kitas)
- **SENAS** `FHBgsP2YZSZ5GCqX` → `:7070/run` + `:8790/api/uzduotys/irasyti`
- **ALGORITMINIS** `BzABxhNszv0Y7ai2` → `:7070/run` + pulto API (atmintis, vektorine, kpi, autonomija, notify)
- Abu eina i **:7070**, kur dabar Groq agentas (anksciau – cline).

## 5. KUR M RAŠO UZDUOTIS
1. **`http://127.0.0.1:7070/`** (darbalaukyje „DI UZDUOTYS“) – modelio pasirinkimas, kvota %, du mygtukai (paprastas / su irankiais).
2. **Pulto skydas** `127.0.0.1:8790/direktorius` → laukas + „Vykdyti dabar (algoritminis)“.
3. PowerShell: `web_agent.py "<uzduotis>"` arba `tool_agent.py "<uzduotis>" [--leisti-keitimus]`.

## 6. SVARBOS PAMOKOS (kad nepasikartotu)
1. `Set-Content -Encoding UTF8` (PS 5.1) prideda **BOM** → `.env` rasyti per Python.
2. K2 `node` **ne PATH** → skriptuose naudoti pilna `runtime\node-v22.23.4-win-x64\node.exe`.
3. `browser-use 0.13.14` API siame rinkinyje neeksportuoja `Agent` → naudojam **Playwright + Groq**.
4. Groq blokuoja `Python-urllib` UA (HTTP 403) → butina `User-Agent`.
5. Dideliu failu perdavimas per relay base64 **gadina** turini → naudoti **GitHub raw**.
6. JS irasytas i HTML per Python escape dažnai lūžta → po kiekvieno pakeitimo tikrinti `node --check`.
7. `schtasks /Create` be admin → „Access is denied“ → naudoti Startup aplanka.
8. Relay (cloudflared quick tunnel) adresas keiciasi po sandboksо perkrovimo → reikia naujos nuorodos.

## 7. KAS LIKO
- [ ] **Pakeisti Groq rakta** (nuteketas pokalbyje).
- [ ] `C:\Program Files\BraveSoftware` (1,09 GB) – paleisti `K2_ADMIN_Chrome_ir_Brave.ps1` kaip admin.
- [ ] Nuspresti del K1: palikti kaip yra (be ataskaitu, kol balansas -0,11) arba perjungti ir K1 i Groq.
- [ ] (Neprivaloma) pridėti daugiau modeliu i `GROQ_MODELS` kaita.
