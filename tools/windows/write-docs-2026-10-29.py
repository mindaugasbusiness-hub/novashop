# -*- coding: utf-8 -*-
"""1 darbas: iraso KUMSTIS AI dokumentacija i C:\\Users\\M\\CLINE\\VISKAS.
NIEKO NETRINA. 02 ir 04 papildomi (.bak kopija daroma pries), 15 sukuriamas.
"""
import os
import shutil
from datetime import datetime

VISKAS = r"C:\Users\M\CLINE\VISKAS"
CLINE = r"C:\Users\M\CLINE"
STAMP = "2026-10-29"
BAK = ".bak-" + STAMP

D15 = r"""# 15 - 2026-10-29 KUMSTIS AI: n8n + Cline worker (be Ollamos)

Sukurta: 2026-10-29. Autorius: Cline (per relay is Cline Cloud).
Tikslas: pakeisti Ollama (per silpnas) Cline agentu su esama prenumerata.

## Grandine

```
n8n (:5678)  --POST-->  Cline worker (:7070)  --spawn-->  cline CLI
                                                              |
                                                    ~/.cline (cline-pass, nemokamas modelis)
                                                              |
                                                    failai: C:\Users\M\CLINE\ai-stack\work\<projektas>
```

- Ollamos NERA ir nereikia (patikrinta: `ollama` PC neidiegtas).
- Open Interpreter nenaudojamas - Cline atlieka ir "rankas", ir "prota".

## Faktai

| Kas | Reiksme |
|---|---|
| Worker | `http://127.0.0.1:7070` (`POST /run`, `GET /healthz`) |
| n8n | `http://127.0.0.1:5678` |
| Workflow ID | `FHBgsP2YZSZ5GCqX` |
| Provider | `cline-pass` (prenumerata) |
| Modelis | `cline-free/nemotron-3.5-super-vl` (nemokamas) |
| Cline CLI | 3.0.74 |
| Aplankas | `C:\Users\M\CLINE\ai-stack` |
| Smelio deze | `C:\Users\M\CLINE\ai-stack\work` |
| Git | MinGit 2.56.0.windows.4 -> `ai-stack\tools\git\cmd\git.exe` |

## Failai (C:\Users\M\CLINE\ai-stack)

| Failas | Paskirtis |
|---|---|
| `server.js` | worker: priima `{prompt, cwd, timeout}`, paleidzia `cline --json --auto-approve`, grazina `{ok, text, model, iterations, durationMs}` |
| `start-worker.ps1` | paleidzia worker fone; prideda Git i PATH; provider/model parametrai |
| `e2e-test.ps1` | tikras testas: agentas sukuria faila smelio dezeje |
| `START-AI-STACK.ps1` | paleidzia n8n + worker ir parodo busena |
| `install-autostart.ps1` | iraso / pasalina (`-Remove`) nuoroda Startup aplanke |
| `install-git.ps1` | parsiuncia MinGit (be admin) |
| `worker-token.txt` | 40 simboliu raktas n8n <-> worker |
| `logs\` | `n8n.log`, `n8n.err.log`, `worker.err.log`, `git-install.log` |
| `*.bak-2026-10-29` | senos skriptu versijos (netrinti) |

## Autostart

`CLINE-AI-STACK.lnk` -> `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`
Nuoroda paleidzia `START-AI-STACK.ps1` (pasleptas langas):
1. jei n8n :5678 neveikia - paleidzia n8n tiesiogiai su `.env` kintamaisiais;
2. jei worker :7070 neveikia - paleidzia worker;
3. laukia iki 120 s ir parodo busena.

## Kaip tai buvo patikrinta (ne teorija)

Testas `e2e-test.ps1` (3 kartai):
- 1 bandymas: `ok:false` - `Insufficient balance. Your Cline Credits balance is $-0.11`
  (buvo provider `cline` + `anthropic/claude-sonnet-5.5` - mokamas);
- 2 bandymas (po perjungimo i `cline-pass`): `ok:true`, 4 iteracijos, 37,7 s,
  failas `work\projektas\labas-024621.txt`;
- 3 bandymas (po Git idiegimo): `ok:true`, 2 iteracijos, 5,7 s - git klaida dingo.

## Svarbus radinys: Ju start-native.ps1 nebeveikia

`C:\Users\M\Desktop\Kumstis\start-native.ps1` krenta ties 192 eilute
(`POST http://127.0.0.1:8090/embed`) - `Could not load model
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
Del to n8n nepaleidziamas is viso (n8n start yra 212 eiluteje).
Be to, n8n be `.env` kintamojo `N8N_ENCRYPTION_KEY` is viso neina paleisti
("Mismatching encryption keys").

Todel `START-AI-STACK.ps1` n8n paleidzia TIESIOGIAI ir pats ikelia `.env`
(taip pat, kaip 145-149 eilutese daro ju skriptas) + `N8N_RESTRICT_FILE_ACCESS_TO`.

## Saugumas

- Worker naudoja `--auto-approve` -> vykdo komandas be klausimo. Neko slapto i `work\` nedeti.
- Worker klauso tik 127.0.0.1 ir reikalauja `x-worker-token`.
- Uzduotys vykdomos po viena (eile), timeout 1800 s; timeout zudo visa procesu grupe.
- `cwd` negali išeiti uz `work` aplanko.

## Kas liko (TODO)

- [ ] Ju `fastembed` modelis - kol neveikia, `start-native.ps1` visada kris;
      KUMSTIS AI skriptas tai apeina.
- [ ] Pakibes procesas PID 9200 (`n8n import:workflow ...Kumstis\workflow.json`)
      nuo ankstesniu sesiju - neliestas (taisykle nr. 1).
- [ ] Pulto (:8790) KUMSTIS AI sekcija - kodas irasytas, rodoma po pulto perkrovimo.
"""


ADD_02 = r"""

## 2026-10-29 - KUMSTIS AI (n8n + Cline worker, be Ollamos)

Naujausias irasas (placiai - zr. `15_2026-10-29_KUMSTIS_AI_SISTEMA.md`).

- Idiegta grandine: n8n (:5678) -> Cline worker (:7070) -> `cline` CLI su `cline-pass`
  prenumerata ir nemokamu modeliu `cline-free/nemotron-3.5-super-vl`.
- Ollama nenaudojama (PC neidiegta), Open Interpreter nereikalingas.
- Workflow `FHBgsP2YZSZ5GCqX` importuotas ir ijungtas (`active = 1`).
- Autostartas: `Startup\CLINE-AI-STACK.lnk` -> `START-AI-STACK.ps1` (n8n + worker).
- Idiegtas Git: MinGit 2.56.0.windows.4 i `ai-stack\tools\git` (be admin).
- End-to-end testas praejo 3 kartus; paskutinis: `ok:true`, 5,7 s, failas sukurtas.
- Rasta: `start-native.ps1` krenta ties embedding patikra (192 eil.), todel n8n
  paleidziamas tiesiogiai su `.env` (isk. `N8N_ENCRYPTION_KEY`).
- NIEKO neistrynta ir neperrasyta be M leidimo; skriptu senos versijos - `*.bak-2026-10-29`.
"""

ADD_04 = r"""

## 2026-10-29 - KUMSTIS AI: ka liko padaryti

Sukurta dabar; ankstesni TODO punktai (5 vnt., "neliesti") - zr. `05_TODO.md`.

- [ ] Sutvarkyti `fastembed` modeli (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
      -> be jo `C:\Users\M\Desktop\Kumstis\start-native.ps1` krenta ir n8n nepaleidzia.
- [ ] Perkrauti pulta (:8790), kad atsirastu sekcija "KUMSTIS AI" (kodas jau irasytas).
- [ ] Nuspresti del pakibusio proceso PID 9200 (`n8n import:workflow`).
- [ ] Nuspresti, ar workflow grafikas (kas 6 h) tinka, ar keisti dazni/trigeri.
- [ ] Nuspresti del `work\` smelio dezes turinio (testiniai `labas-*.txt`, `e2e-result*.txt`).
- [ ] `N8N_ENCRYPTION_KEY` ir kiti `.env` kintamieji - NELIESTI, palikti kaip buvo.
"""


def append_if_missing(path, block, marker):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(block.lstrip("\n"))
        print("SUKURTAS:", path)
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        old = f.read()
    if marker in old:
        print("JAU YRA (nekeiciu):", path)
        return
    bak = path + BAK
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("kopija:", bak)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(block)
    print("PRIDETA:", path, "->", os.path.getsize(path), "B")


print("Laikas:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
p15 = os.path.join(VISKAS, "15_2026-10-29_KUMSTIS_AI_SISTEMA.md")
append_if_missing(p15, D15, "KUMSTIS AI: n8n + Cline worker")

append_if_missing(os.path.join(VISKAS, "02_ATLIKTI_DARBAI.md"), ADD_02, "2026-10-29 - KUMSTIS AI")
append_if_missing(os.path.join(CLINE, "04_TODO.md"), ADD_04, "2026-10-29 - KUMSTIS AI")

print("BAIGTA")
