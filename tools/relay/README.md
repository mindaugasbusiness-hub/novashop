# Cline relay — ryšys su M kompiuteriu (Windows) be SSH ir be diegimų

Tikslas: aš (Cline, debesyse) matau ir valdau M kompiuterį. Be SSH, be antiviruso problemų,
be jokių diegimų tavo mašinoje.

## Kaip tai veikia

1. Aš paleidžiu `relay.py` (portas 8798) — jis laiko komandų eilę ir atsakymus.
2. `cloudflared tunnel --url http://127.0.0.1:8798` sukuria viešą HTTPS adresą.
3. Relay atiduoda klientą: `https://<adresas>/agent.ps1` (raktas įrašomas automatiškai).
4. Tu dukart spaudi darbalaukyje **CLINE RYSYS** → langas suranda adresą ir paleidžia klientą.
5. Klientas long-pollina `/next`, vykdo PowerShell komandą, rezultatą siunčia į `/out`.

## Vienas paleidimas (aš, kiekvienos sesijos pradžioje)

```bash
bash tools/relay/start.sh            # cloudflared + relay + tunelis + patikra (~1-3 min: DNS)
python3 tools/relay/test-relay.py    # savitikra, turi būti 11/11 OK
```

`start.sh` atspausdina eilutę, kurią perduodu direktoriui:
`iex (irm https://<adresas>/agent.ps1)`

## Komandos į M kompiuterį

```bash
python3 tools/relay/pc.py status
python3 tools/relay/pc.py cmd "Get-Date"
python3 tools/relay/pc.py cmd --lines 60 "Get-ChildItem 'C:\Users\M\Desktop' -Force"
python3 tools/relay/pc.py cmd --file /tmp/skriptas.ps1 --timeout 300
```

Visas išvedimas visada įrašomas į failą (`/tmp/pc-out/out-N.txt`), ekrane — tik pradžia
(`--lines`, numatyta 40). Tai saugo pokalbio kontekstą. `--full` naudok atsargiai.

## Adresų lenta (atsarginis kelias)

```bash
python3 tools/relay/lenta.py busena     # ką lenta sako dabar
python3 tools/relay/lenta.py skelbti    # įrašyti dabartinį adresą (reikia privataus repo!)
python3 tools/relay/lenta.py isvalyti   # „nėra aktyvaus adreso“
```

Lenta gyvena nuolatinėje šakoje `cline/lenta` — todėl adresas, kurį skaito tavo kompiuterio
paleidėjas, visada tame pačiame kelyje:
`https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/relay-adresas.txt`

**Saugumas:** repo viešas → `skelbti` atsisako be `--force`, nes kas perskaitytų lentą galėtų
vykdyti komandas M kompiuteryje, kol gyva sesija.

## API (reikia `X-Key: <raktas>`)

| Kelias | Ką daro |
|---|---|
| `POST /cmd` (body = komanda) | įdeda į eilę → `{"id":N}` |
| `GET /next?since=N&cid=...` | long-poll 15 s → `{"id":N,"cmd":"..."}` |
| `POST /out?id=N` (body = base64) | agentas siunčia rezultatą |
| `GET /out?id=N` | base64 arba 404 (dar nepabaigta) |
| `GET /cmds` | visos komandos |
| `GET /status` | kas prisijungę, kiek komandų |
| `GET /health` | be autentifikacijos, patikrai |
| `GET /agent.ps1` | klientas (raktas įrašytas viduje) |

## Svarbu žinoti

- Raktas generuojamas paleidimo metu → `/tmp/relay.token`. Jis gyvas tik kol gyva sesija.
- Po kiekvieno naujo tunelio **adresas naujas**, o DNS propagacija užtrunka 1–2 min.
  `start.sh` to laukia ir pats pasako, ar DNS jau veikia.
- Klientas suderinamas su PowerShell 5.1 (`powershell.exe -File`, base64 per UTF-8).
- Ilgos komandos (rekursyvus disko skenavimas) blokuoja eilę iki 5 min — venk `-Recurse` per visą diską.
- Savitikra nieko neliečia: naudoja savo portą ir savo laikinus failus.

## Susiję failai

- `windows/` — viskas, kas veikia M kompiuteryje (paleidėjas, PRADZIA, nuorodos, įrašymas).
- `CLINE/01_RYSYS.md` — kaip tai atrodo direktoriaus akimis, su patikrintais faktais.
