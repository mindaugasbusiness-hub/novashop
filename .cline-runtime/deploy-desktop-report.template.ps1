$ErrorActionPreference='Stop'
$target='C:\Users\M\Desktop\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md'
if(Test-Path -LiteralPath $target){throw ('Failas jau yra, neperrasau: '+$target)}
[IO.File]::WriteAllBytes($target,[Convert]::FromBase64String('__PAYLOAD__'))
$file=Get-Item -LiteralPath $target
Write-Output ('ATASKAITA='+$file.FullName)
Write-Output ('DYDIS='+$file.Length+' B')
Write-Output ('LAIKAS='+$file.LastWriteTime)
$text=Get-Content -LiteralPath $target -Raw -Encoding UTF8
foreach($needle in @('# CLINE ATASKAITA','KO PRASEI IR AR PADARYTA','KAS VEIKIA DABAR','N8N — KĄ JIS DARO','KAS DAR NEPADARYTA','00_SKAITYK_NAUJAUSIA.md','clineAuto0000001','Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.')){
  Write-Output ('TURINYJE: '+$needle+' => '+$text.Contains($needle))
}
Write-Output ('EILUCIU='+(($text -split "`n").Count))
Write-Output '===== DIENORASTIS ====='
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath 'C:\Users\M\CLINE\02_DIENORASTIS.md' -Destination (Join-Path $bak '02_DIENORASTIS.md')
Copy-Item -LiteralPath 'C:\Users\M\CLINE\09_PAKEITIMAI.md' -Destination (Join-Path $bak '09_PAKEITIMAI.md')
Copy-Item -LiteralPath 'C:\Users\M\CLINE\VISKAS\VISKAS_VISKAS.md' -Destination (Join-Path $bak 'VISKAS_VISKAS.md')
function Add-AfterTitle([string]$path,[string]$entry){$t=[IO.File]::ReadAllText($path);$i=$t.IndexOf("`n");if($i -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$t.Insert($i+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 15:05 — ataskaita darbalaukyje
- Sukurta ataskaita: `Desktop\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md` (senoji ataskaita neperrasyta).
- Ataskaitoje: ko prašei, kas veikia (11 servisų), ką daro n8n, kaip padaryta, kas pataisyta, nukreipimai, kas dar nepadaryta.
- n8n automatikos vykdymai įrodyti: 206, 208, 210, 212, 214 = success; tiltas `:8792` veikia.
- Visi servisai 9/9; svetainė 200; VPS servisai active.
'@
Add-AfterTitle 'C:\Users\M\CLINE\02_DIENORASTIS.md' $entry
Add-AfterTitle 'C:\Users\M\CLINE\09_PAKEITIMAI.md' $entry
Add-AfterTitle 'C:\Users\M\CLINE\VISKAS\VISKAS_VISKAS.md' $entry
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT_EXIT='+$LASTEXITCODE)
Get-Item -LiteralPath $target,'C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md','C:\Users\M\CLINE\VISKAS\00_VISKAS_PILNA_ISTORIJA.md'|Select-Object Name,Length,LastWriteTime|Format-Table -AutoSize