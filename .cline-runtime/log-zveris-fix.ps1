$root='C:\Users\M\CLINE'
$v=Join-Path $root 'VISKAS'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$backupDir=Join-Path $root "BACKUPS\$stamp"
$memoryDir=Join-Path $backupDir 'CLINE'
New-Item -ItemType Directory -Path $memoryDir -Force | Out-Null
$names=@('02_DIENORASTIS.md','04_TODO.md','09_PAKEITIMAI.md')
foreach($name in $names){Copy-Item -LiteralPath (Join-Path $root $name) -Destination (Join-Path $memoryDir $name)}
New-Item -ItemType Directory -Path (Join-Path $memoryDir 'VISKAS') -Force | Out-Null
foreach($name in @('VISKAS_VISKAS.md','02_ATLIKTI_DARBAI.md')){Copy-Item -LiteralPath (Join-Path $v $name) -Destination (Join-Path $memoryDir "VISKAS\$name")}
$indexBackup=Join-Path $backupDir 'workspace\zveris\ui\static'
New-Item -ItemType Directory -Path $indexBackup -Force | Out-Null
Copy-Item -LiteralPath 'C:\workspace\zveris\ui\static\index.html' -Destination (Join-Path $indexBackup 'index.html')
function Add-AfterTitle([string]$path,[string]$entry){$text=[IO.File]::ReadAllText($path);$pos=$text.IndexOf("`n");if($pos -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$text.Insert($pos+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 13:19 — Žvėris UI atkurtas
- Priežastis: trūko `C:\workspace\zveris\ui\static\index.html`; dėl to pagrindinis `:8091` puslapis grąžindavo 500.
- Sukurtas naujas 5 230 B puslapis pagal esamą API; `ui_app.py` nekeistas, servisas neperkrautas.
- Patikra: pagrindinis puslapis 200, `/api/status` 200, `/api/memory/chat` 200, JavaScript sintaksė OK.
- Naujo failo kopija: BACKUPS po šio įrašo kataloge `workspace\zveris\ui\static\index.html`.
- Pastaba: `/api/status` rodo 0 Ollama modelių; AI atsakymai priklauso nuo atskiro modelio paleidimo.
'@
$f6=@'
## 2026-10-25 12:54 — F6 atkurtas
- F1 užėmė kitas procesas ir senas scriptas dėl to blokuodavo F6–F11; pataisyta, kad F6–F11 veiktų atskirai.
- F6 :8766 = 200; originalo kopija `BACKUPS\2026-10-25_125157`.
'@
Add-AfterTitle (Join-Path $root '09_PAKEITIMAI.md') $entry
Add-AfterTitle (Join-Path $root '02_DIENORASTIS.md') $entry
Add-AfterTitle (Join-Path $root '04_TODO.md') ("- [x] Žvėris pagrindinis puslapis :8091 atkurtas (200).`r`n- [ ] Žvėris AI: šiuo metu API rodo 0 Ollama modelių; pokalbio atsakymams reikia modelio.")
Add-AfterTitle (Join-Path $v '02_ATLIKTI_DARBAI.md') ($entry+"`r`n"+$f6)
Add-AfterTitle (Join-Path $v 'VISKAS_VISKAS.md') ("# NAUJAUSI PAKEITIMAI PO SUKŪRIMO`r`n"+$entry+"`r`n"+$f6)
Add-Content -LiteralPath (Join-Path $v '07_SESIJA_2026-10-25.md') -Encoding UTF8 -Value '- **13:19:41** — Žvėris UI trūkstamas index.html atkurtas; pagrindinis puslapis/status/atmintis = 200; AI modelių = 0.'
& (Join-Path $v 'viskas-atnaujinti.ps1')
Write-Output ('BACKUP='+$backupDir)
Write-Output '===== GALUTINIS TESTAS ====='
& curl.exe -sS -o NUL -w 'Zveris_root=%{http_code}\n' --max-time 10 'http://127.0.0.1:8091/'
Get-Content -LiteralPath (Join-Path $v 'VISKAS_VISKAS.md') -Encoding UTF8 -TotalCount 16
