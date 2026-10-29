# n8n + Cline worker (be Ollamos)

Grandinė: **n8n duoda užduotį → Cline CLI atlieka darbą kompiuteryje → modelis (bet kuris, ne Ollama) mąsto.**

```
n8n (trigger, logika, alertai)
   │  POST http://cline-worker:7070/run   {prompt, cwd}
   ▼
cline-worker (Docker: node + Cline CLI headless)
   │  cline --json --auto-approve true -c /work/projektas "..."
   ▼
/ work katalogas: failai, git, testai, skriptai  ← čia vyksta tikras darbas
   │
   ▼
modelis: Gemini / OpenRouter / Anthropic / ... (raktas .env faile)
```

## 1. Svarbiausia: Cline ≠ modelis

- **Ollama** – modelių serveris. Jis „mąsto“, bet nieko neliečia.
- **Open Interpreter** – agentas, kuris vykdo kodą kompiuteryje. Jam reikia modelio.
- **Cline** – irgi agentas (skaito failus, rašo, leidžia komandas, naudoja MCP). Jam **taip pat** reikia modelio.

Todėl „įdėti Cline vietoj Ollamos“ į Open Interpreterio modelio lizdą **techniškai negalima**: tame lizde turi būti OpenAI suderinamas *modelių* galinis taškas, o Cline yra agentas su savo CLI.

Praktiškai tai reiškia: **Cline išstumia Open Interpreterį**, o modelį pasirenki atskirai (nebūtinai Ollamą).

| Ką nori turėti | Kaip atrodo |
| - | - |
| Viskas nemokama, bet silpna | n8n → Ollama (modelis) + savo skriptas darbui |
| Protinga, bet mokama | n8n → **Cline** + Claude/GPT raktas |
| Protinga ir (beveik) nemokama | n8n → **Cline** + Gemini free tier / OpenRouter `:free` modelis ← šis stack'as |

> Cline taip pat turi OpenAI suderinamą **Cline API** (`https://api.cline.bot/api/v1/chat/completions`), bet jis mokamas, o nemokami modelių promo variantai per API neveikia – tik IDE/CLI.

## 2. Kodėl atskiras „worker“ konteineris, o ne `Execute Command` n8n viduje

- n8n atvaizdis ir agento aplinka nesimaišo (git, ripgrep, python reikalingi agentui, ne n8n).
- Agentas gali valgyti 1–4 GB RAM ir ilgai dirbti – geriau, kai tai atskiras procesas su savo limitu.
- `cline` atnaujinimai ir „nutekėję“ agento procesai neapverčia n8n.
- Worker'is neturi `ports:` → iš išorės nepasiekiamas, tik iš n8n tinklo, ir dar reikalauja `x-worker-token`.

## 3. Paleidimas

```bash
cd infra/ai-stack
cp .env.example .env
# .env: įrašyk WORKER_TOKEN (openssl rand -hex 32) ir CLINE_API_KEY

docker compose up -d --build
curl -s localhost:5678            # n8n UI
docker compose logs -f cline-worker
```

Patikrinimas iš n8n konteinerio:

```bash
docker compose exec n8n node -e "
fetch('http://cline-worker:7070/run',{method:'POST',
  headers:{'content-type':'application/json','x-worker-token':process.env.WORKER_TOKEN},
  body:JSON.stringify({prompt:'Parašyk į /work/projektas/labas.txt žodį labas',cwd:'projektas'})})
 .then(r=>r.text()).then(console.log)"
```

Workflow: n8n → **Import from File** → `n8n-workflow-example.json`.

## 4. Ką daro `server.js`

`POST /run` su `{prompt, cwd, timeout}` paleidžia:

```bash
cline --json --auto-approve true \
      --config /data/cline --data-dir /data/cline/data \
      -c /work/<cwd> -t <timeout> --retries 3 \
      [-P <provider>] [-m <model>] [-k <api-key>] \
      "<prompt>"
```

ir grąžina:

```json
{ "ok": true, "text": "...", "finishReason": "completed", "iterations": 7,
  "usage": {...}, "model": "...", "durationMs": 41230 }
```

- `cwd` negali išeiti už `/work` (path traversal atmetamas).
- Užduotys vykdomos **po vieną** (agentas valgo daug RAM) – eilė, ne parallel.
- `timeout` nužudo visą procesų grupę (ir agento paleistus vaikus).
- Klaidos iš `stderr` (`{"type":"error",...}`) sugaunamos ir grąžinamos kaip `ok:false`.
- `ok=false`, kai `finishReason` nėra `completed` (nutraukta, klaida, timeout, kvota).


## 5. Modelio pasirinkimas (kur „nemokama“ kanda)

`CLINE_PROVIDER` / `CLINE_MODEL` / `CLINE_API_KEY` – `.env` faile. Tikslius ID pažiūrėk savo versijoje: `cline auth` arba interaktyviai `cline` → `/model`. Pavadinimai kinta, todėl čia jų nefiksuoju.

| Variantas | Kaina | Realybė agentui |
| - | - | - |
| Cline free modelių promo (per Cline account, IDE/CLI) | 0 € | Rotuojasi, limituota kvota, per Cline API neveikia |
| Google AI Studio (Gemini Flash) free tier | 0 € | Geriausias „nemokamas“ kompromisas; dienos limitas pakankamas kelioms užduotims |
| OpenRouter `:free` modeliai | 0 € | ~50 užklausų/dieną (daugiau, jei kada nusipirkei kreditų); agentas per vieną užduotį padaro 10–40 užklausų → 2–3 užduotys/dieną |
| Groq / Cerebras free tier | 0 € | Labai greita, bet irgi dienos/tempų limitai |
| ClinePass | ~10 €/mėn | Plokščia kaina, 2–5× didesni limitai – realiausias „beveik nemokamos grandinės“ variantas |
| Ollama lokaliai | 0 € | Niekada nebus 429, bet silpnas tool-calling → agentas klysta („žioplas“) |

**Sąžiningai:** „visiškai nemokama + patikima“ su agentu nesuderinama, nes agentas = daug modelio užklausų vienai užduočiai. Nemokamas tier tinka *kelioms užduotims per dieną*, ne nuolatiniam darbui. Jei nori stabilumo – ClinePass arba pigiausias mokamas modelis, o ne didesnio nemokamo limito medžioklė.

## 6. Saugumas (būtina, nes `--auto-approve true`)

- Worker'yje **jokių** gamybinių slaptažodžių, SSH raktų, `.env` su DB – tik tai, ką agentas turi matyti.
- `./work` – atskiras katalogas, geriausia git repo su švaria būsena: po nesėkmės `git -C work/projektas diff` parodo, ką agentas pridarė.
- CLI neturi komandų allow/deny sąrašo. Jei reikia blokuoti – `PreToolUse` hook, kuris atmeta `run_commands` (žr. Cline docs → Hooks / `.clineignore` hook pavyzdį).
- `mem_limit: 4g` ir jokio `ports:` – jau sudėta į `docker-compose.yml`.

## 7. Jei vis dėlto nori palikti Open Interpreter

Tada Cline į grandinę nededamas – tiesiog pakeisk modelį (Open Interpreter naudoja LiteLLM, todėl `provider/model` prefiksai veikia):

```bash
export OPENROUTER_API_KEY=...
interpreter --model openrouter/deepseek/deepseek-chat-v3.1:free -y "sutvarkyk failus"

export GEMINI_API_KEY=...
interpreter --model gemini/gemini-2.5-flash -y "sutvarkyk failus"
```

Bet: Open Interpreter yra prasčiau prižiūrimas ir neturi Cline tool'ų (diff redagavimas, MCP, hook'ai). Jei tikslas „agentas, kuris realiai padaro darbą“ – Cline CLI stipresnis už abu (ir už Ollamą, ir už Open Interpreterį).

## 8. Testai

```bash
bash test/smoke-test.sh     # 17 patikrų, be rakto ir be tikro cline
```

Naudoja `cline` stub'ą (`CLINE_BIN`), tikrina: auth, tuščią prompt, path traversal, NDJSON `run_result` parsavimą, klaidos `stderr` parsavimą, `aborted` būseną, timeout'ą ir eilės serializavimą.

## 9. Dažnos bėdos

| Požymis | Priežastis |
| - | - |
| `ok:false, error: "401/429"` | blogas raktas arba išsemta nemokama kvota |
| `agentas negrąžino run_result` | `cline` nepaleistas / neteisingas `-P` ID / auth |
| n8n meta `timeout` | HTTP node `options.timeout` (ms) mažesnis už `TASK_TIMEOUT_SECONDS` |
| `ok:false, finishReason:"aborted"` | agentas sustojo po `--retries` klaidų – žiūrėk `stderr` |
| Worker'is restartuojasi | per mažai RAM (`mem_limit`) – mažink `--thinking` arba didink limitą |
