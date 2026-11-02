# Cline relay (variantas B)

Tikslas: Cline (debesyje) mato ir valdo M kompiuteri (Windows) be SSH, be diegimu, be antiviruso problemu.

## Kaip tai veikia
1. Cline puseje paleidziamas `relay.py` (portas 8798) – jis laiko komandu eile ir atsakymus.
2. `cloudflared tunnel --url http://127.0.0.1:8798` sukuria viesa HTTPS adresa.
3. Relay atiduoda PC pusei klienta: `https://<adresas>/agent.ps1` (tokenas iterptas automatskai).
4. M paleidzia darbalaukio nuoroda „CLINE RYSYS“ -> `connect.ps1` paima komanda is atmintines ir paleidzia.
5. Klientas long-pollina `/next`, vykdo PowerShell komanda, rezultata siuncia i `/out`.

## Komandos Cline puseje
```bash
python3 tools/relay/relay.py &            # portas 8798, tokenas -> /tmp/relay.token
/tmp/cloudflared tunnel --url http://127.0.0.1:8798 --no-autoupdate &
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cf2.log | head -1
```
Tada M duodama: `iex (irm https://<adresas>/agent.ps1)`

## API (reikia `X-Key: <token>`)
- `POST /cmd` body=komanda -> `{"id":N}`
- `GET /next?since=N` -> `{"id":N,"cmd":"..."}` (long-poll 15 s)
- `POST /out?id=N` body=base64(rezultatas)
- `GET /out?id=N` -> base64 arba 404 (dar nepabaigta)
- `GET /cmds` -> visos komandos
- `GET /health` -> be autentifikacijos

## Svarbu
- Tokenas generuojamas kiekviena paleidima -> `/tmp/relay.token`.
- Klientas PowerShell 5.1 suderinamumas: `powershell.exe -File`, base64 per UTF-8.
- Ilgos komandos (rekursyvus disk scan) blokuoja eile iki 5 min – venk `-Recurse` per visa disk.
