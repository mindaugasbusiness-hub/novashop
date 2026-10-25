$ErrorActionPreference='Stop'
$root='C:\Users\M\CLINE';$v=Join-Path $root 'VISKAS';$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak=Join-Path $root "BACKUPS\$stamp\CLINE";$bakv=Join-Path $bak 'VISKAS';$bakt=Join-Path $bak 'tools'
New-Item -ItemType Directory -Path $bakv,$bakt -Force|Out-Null
foreach($n in @('02_DIENORASTIS.md','04_TODO.md','09_PAKEITIMAI.md')){Copy-Item -LiteralPath (Join-Path $root $n) -Destination (Join-Path $bak $n)}
foreach($n in @('VISKAS_VISKAS.md','02_ATLIKTI_DARBAI.md','03_SISTEMA_IR_SERVISAI.md','SESIJA_2026-10-25_CLOUD.md')){Copy-Item -LiteralPath (Join-Path $v $n) -Destination (Join-Path $bakv $n)}
foreach($n in @('automation_server.py','automation-server-loop.ps1','startup-automation.ps1','cline-auto-workflow-v2.json','zveris-ensure.ps1','zveris-refresh.cjs','surinkti-viska.py')){Copy-Item -LiteralPath (Join-Path $root "tools\$n") -Destination (Join-Path $bakt $n)}
function Add-AfterTitle([string]$path,[string]$entry){$t=[IO.File]::ReadAllText($path);$i=$t.IndexOf("`n");if($i -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$t.Insert($i+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 14:40 — automatika ĮRODYTA
- n8n workflow `clineAuto0000001` aktyvus; pirmas automatinis paleidimas: execution **206**, status **success**, 2026-10-25 21:40:08 UTC.
- Automatikos žurnalas: `ensure` baigė per 2,8 s (exit 0), `collect` per 0,1 s (exit 0).
- Ankstesnė klaida: n8n neturėjo `executeCommand` mazgo. Sprendimas: vietinis saugus tiltas `:8792`, tik trys fiksuoti veiksmai `/ensure`, `/collect`, `/run`; savavališkos komandos negalimos.
- n8n workflow naudoja `httpRequest` mazgus. Slaptas raktas saugomas `tools\automation-secret.txt` ir nėra rodomas.
- Kas 5 min: Žvėris patikra/taisymas, F5 tik agento naršyklėje, VISKAS istorijos surinkimas.
- Įjungus PC: `CLINE-SURINKTI.lnk` paleidžia surinkimą, Žvėris patikrą ir automatikos serverio loop.
- Istorija: `00_SKAITYK_NAUJAUSIA.md` (~50 KB) ir `00_VISKAS_PILNA_ISTORIJA.md` (~439 KB); 14 vietinių Cline sesijų.
- Žvėris AI modelių skaičius tebėra 0; atsakymams reikia atskiro modelio.
'@
Add-AfterTitle (Join-Path $root '09_PAKEITIMAI.md') $entry
Add-AfterTitle (Join-Path $root '02_DIENORASTIS.md') $entry
Add-AfterTitle (Join-Path $root '04_TODO.md') "- [x] n8n automatinis ciklas įrodytas: execution 206, `ensure` ir `collect` exit 0.`r`n- [ ] Žvėris AI modelių 0; reikia modelio, jei nori, kad Žvėris atsakinėtų."
Add-AfterTitle (Join-Path $v '02_ATLIKTI_DARBAI.md') $entry
Add-AfterTitle (Join-Path $v 'VISKAS_VISKAS.md') $entry
Add-Content -LiteralPath (Join-Path $v '03_SISTEMA_IR_SERVISAI.md') -Encoding UTF8 -Value "`r`n## Automatika — patikrinta 2026-10-25 14:40`r`n- n8n `clineAuto0000001`: kas 5 min, HTTP -> `127.0.0.1:8792`, pirmas execution 206 = success.`r`n- Tiltas: tik `/ensure`, `/collect`, `/run`; raktas `tools\\automation-secret.txt`.`r`n- Startuolis: `CLINE-SURINKTI.lnk`; loop: `tools\\automation-server-loop.ps1`.`r`n"
Add-Content -LiteralPath (Join-Path $v 'SESIJA_2026-10-25_CLOUD.md') -Encoding UTF8 -Value "`r`n## Įgyvendinta 2026-10-25 14:40`r`n- n8n automatinis ciklas įrodytas execution 206 (success); ensure ir collect exit 0.`r`n- Saugus HTTP tiltas :8792 su fiksuotomis komandomis.`r`n- Surinkta 14 Cline sesijų; pilna istorija apie 439 KB, trumpa apie 50 KB.`r`n"
Write-Output ('BACKUP='+$bak)
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT_EXIT='+$LASTEXITCODE)
& (Join-Path $v 'viskas-atnaujinti.ps1')
Get-Item -LiteralPath (Join-Path $v '00_SKAITYK_NAUJAUSIA.md'),(Join-Path $v '00_VISKAS_PILNA_ISTORIJA.md'),(Join-Path $v '06_DABARTINE_BUSENA.md')|Select-Object Name,Length,LastWriteTime|Format-Table -AutoSize
