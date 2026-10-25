$ErrorActionPreference='Stop'
$root='C:\Users\M\CLINE';$v=Join-Path $root 'VISKAS'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss';$bak=Join-Path $root "BACKUPS\$stamp"
$mem=Join-Path $bak 'CLINE';$memv=Join-Path $mem 'VISKAS';$tools=Join-Path $bak 'CLINE\tools'
New-Item -ItemType Directory -Path $memv,$tools -Force|Out-Null
foreach($n in @('00_START_HERE.md','02_DIENORASTIS.md','04_TODO.md','09_PAKEITIMAI.md')){Copy-Item -LiteralPath (Join-Path $root $n) -Destination (Join-Path $mem $n)}
foreach($n in @('VISKAS_VISKAS.md','02_ATLIKTI_DARBAI.md','03_SISTEMA_IR_SERVISAI.md')){Copy-Item -LiteralPath (Join-Path $v $n) -Destination (Join-Path $memv $n)}
foreach($n in @('surinkti-viska.py','zveris-ensure.ps1','zveris-refresh.cjs','startup-automation.ps1','cline-auto-workflow.json')){Copy-Item -LiteralPath (Join-Path $root "tools\$n") -Destination (Join-Path $tools $n)}
function Add-AfterTitle([string]$path,[string]$entry){$t=[IO.File]::ReadAllText($path);$i=$t.IndexOf("`n");if($i -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$t.Insert($i+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 13:46 — automatinis Žvėris, F5 ir VISKAS surinkimas
- Sukurtas ir aktyvuotas n8n workflow `clineAuto0000001` — „CLINE – Žvėris ir VISKAS automatiškai“.
- Kas 5 min: patikrina `:8091`; jei reikia, atstato trūkstamą `index.html`, paleidžia tik `ui_app` procesą ir padaro F5 tik agento naršyklėje.
- Kas 5 min: paleidžia `tools\surinkti-viska.py`, kuris atnaujina `VISKAS\00_SKAITYK_NAUJAUSIA.md` ir `VISKAS\00_VISKAS_PILNA_ISTORIJA.md`.
- Įjungus PC: startuolio `CLINE-SURINKTI.lnk` iškart paleidžia surinkimą ir Žvėris patikrą, nelaukiant pirmo n8n grafiko.
- Įrodyta: F5 skirtuke `http://127.0.0.1:8091/` įvykdytas; testinis skirtukas uždarytas.
- Surinkta 14 vietinių Cline sesijų + VISKAS dokumentai: pilnas failas 432 770 B, trumpas 49 475 B.
- Neaktyvus lieka tik sąmoningai testinis `aukc-test00000001`, kad nesiųstų netikrų pranešimų.
- Žvėris AI modelių skaičius vis dar 0; tam reikia atskiro modelio.
'@
Add-AfterTitle (Join-Path $root '09_PAKEITIMAI.md') $entry
Add-AfterTitle (Join-Path $root '02_DIENORASTIS.md') $entry
Add-AfterTitle (Join-Path $root '04_TODO.md') "- [x] n8n aktyvus workflow kas 5 min tikrina/taiso Žvėrį, daro F5 ir atnaujina VISKAS istoriją.`r`n- [x] Įjungus PC paleidžiamas CLINE-SURINKTI surinkimas.`r`n- [ ] Žvėris AI modelis: 0 modelių; atsakymams reikia atskirai paleisto modelio."
Add-AfterTitle (Join-Path $v '02_ATLIKTI_DARBAI.md') $entry
Add-AfterTitle (Join-Path $v 'VISKAS_VISKAS.md') ("# NAUJAUSIA SESIJA — SKAITYK ŠĮ FAILĄ`r`n`r`n**Naujam DI:** `Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.`**`r`n`r`nTrumpas failas nukreipia į pilną istoriją `00_VISKAS_PILNA_ISTORIJA.md` (VISKAS dokumentai + vietinės Cline sesijos).`r`n`r`n"+$entry)
Add-AfterTitle (Join-Path $root '00_START_HERE.md') ("## NAUJAUSIA SESIJA (automatiškai parengta)`r`nNaujoje sesijoje pirmiausia skaityk: ``C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md``. Ten yra dabartinė būsena ir nuoroda į pilną 14 sesijų istoriją.`r`n")
Add-Content -LiteralPath (Join-Path $v '03_SISTEMA_IR_SERVISAI.md') -Encoding UTF8 -Value "`r`n## CLINE automatinis workflow (2026-10-25)`r`n- n8n ID: ``clineAuto0000001``, aktyvus, kas 5 min.`r`n- Veiksmai: Žvėris ``:8091`` patikra/taisymas + F5 agento naršyklėje + VISKAS istorijos surinkimas.`r`n- Startuolyje: ``CLINE-SURINKTI.lnk``.`r`n"
Write-Output ('BACKUP='+$bak)
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT_EXIT='+$LASTEXITCODE)
Get-Item -LiteralPath (Join-Path $v '00_SKAITYK_NAUJAUSIA.md'),(Join-Path $v '00_VISKAS_PILNA_ISTORIJA.md'),(Join-Path $v 'VISKAS_VISKAS.md')|Select-Object Name,Length,LastWriteTime|Format-Table -AutoSize
