# 20 - 2026-11-02 RELAY: prisijungimo grandine paleista is naujo

Sukurta: 2026-11-02. Autorius: Cline (nauja sesija, sandbox).
Tikslas: M prase "junkis per power shell" - t. y. atkurti rysi su M kompiuteriu (variantas B: relay + tunelis).

## 1. Kas padaryta (patikrinta)

| Zingsnis | Busena | Irodymas |
|---|---|---|
| Darbo saka | sukurta `cline/e2xxxbsm` nuo `main` (b3f1915) | `git checkout -b` |
| Relay irankiai repo | ideti `tools/relay/` (relay.py, agent-template.ps1, pc.py, test-relay.py, README.md) | commit 6166c7a, 68b3173 |
| relay.py | VEIKIA, portas 8798, tokenas /tmp/relay.token | `/health` -> ok |
| cloudflared | parsiustas (2026.10.7), tunelis pakilo | /tmp/bin/cloudflared |
| Viesas adresas | `https://playstation-burning-equality-ran.trycloudflare.com` | `GET /agent.ps1` -> 200, tokenas iterptas |
| Adresas paskelbtas M kompiuteriui | ntfy tema `cline-a967f1b1a3d5792c`, formatas `CLINE\|<secret>\|https://.../agent.ps1` | ntfy id BVlCJP0eTi89 |
| Savitikra | **11 OK / 0 FAIL** (relay -> agent.ps1 -> pc.py grandis) | `python3 tools/relay/test-relay.py` |
| M kompiuteris prisijunges | **NE** (klientu 0) | `/status` -> `{"clients": {}}` |

## 2. Ko reikia is M

- Kompiuteris ijungtas ir prisijunges prie interneto.
- Budetojas `C:\Users\M\CLINE\tools\autoconnect.ps1` veikia (autostart nuoroda `CLINE-AUTOCONNECT.lnk`) - tada prisijungia pats per ~20 s.
- Jei budetojas neveikia - rankiniu keliu PowerShell lange:

```powershell
iex (irm https://playstation-burning-equality-ran.trycloudflare.com/agent.ps1)
```

arba dukart spaudi darbalaukio nuoroda "CLINE RYSYS" ir iklijuojant si adresa.

## 3. Kaip Cline puseje tikrinti ir siusti komandas

```bash
python3 tools/relay/pc.py status                       # kas prisijunge
python3 tools/relay/pc.py cmd "Get-Date"               # ivykdyti komanda
python3 tools/relay/pc.py cmd --lines 60 "Get-ChildItem C:\Users\M\CLINE"
```

- Adresas laikomas `/tmp/relay.base`, raktas - `/tmp/relay.token`.
- `--lines` riboja ekrana; visa isvestis irasoma i `/tmp/pc-out/out-<id>.txt`.

## 4. Svarbu ateičiai

- Adresas gyvas TIK kol gyva sio sesija (sandbox isjungiamas - adresas miršta).
- Sioje masinoje `C:\` disko NERA - tai atskira smeliadeze, ne M kompiuteris (taisykle 4: sakyti tiesa).
- `relay-adresas.txt` lenta (GitHub saka `cline/lenta`) NENAUDOTA: repo `novashop` yra VIESAS,
  o `lenta.py` tokiu atveju skelbima blokuoja be `--force`. Naudota ntfy tema (kaip 2026-10-22 sprendime).
- NIEKO M kompiuteryje nepakeista, netrinta ir neperrasyta (taisykle 1). Tik rysio kanalas.
