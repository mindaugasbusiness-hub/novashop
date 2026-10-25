$ErrorActionPreference='Stop'
$desktop='C:\Users\M\Desktop\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md'
$viskas='C:\Users\M\CLINE\VISKAS\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md'
$bytes=[Convert]::FromBase64String('__PAYLOAD__')
foreach($target in @($viskas,$desktop)){
  $dir=Split-Path -Parent $target
  if(-not (Test-Path -LiteralPath $dir)){New-Item -ItemType Directory -Path $dir -Force|Out-Null}
  [IO.File]::WriteAllBytes($target,$bytes)
  $f=Get-Item -LiteralPath $target
  Write-Output ('IRASYTA: '+$f.FullName+' | '+$f.Length+' B | '+$f.LastWriteTime)
}
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath 'C:\Users\M\CLINE\02_DIENORASTIS.md' -Destination (Join-Path $bak '02_DIENORASTIS.md')
Copy-Item -LiteralPath 'C:\Users\M\CLINE\09_PAKEITIMAI.md' -Destination (Join-Path $bak '09_PAKEITIMAI.md')
function Add-AfterTitle([string]$path,[string]$entry){$t=[IO.File]::ReadAllText($path);$i=$t.IndexOf("`n");if($i -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$t.Insert($i+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 15:15 — ataskaita padėta stabliai
- Ataskaita įrašyta dviem vietom: `Desktop\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md` ir `VISKAS\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md`.
- Pastebėta: darbalaukio tvarkytojas laisvus failus sukelia į `Desktop\2026010.24d\`; ten jau yra ir ankstesnė ataskaita.
- Todėl stabili kopija laikoma VISKAS aplanke, kurio tvarkytojas neliečia.
- Tvarkytojo neliečiau ir jo neišjungiau (taisyklė Nr.1).
'@
Add-AfterTitle 'C:\Users\M\CLINE\02_DIENORASTIS.md' $entry
Add-AfterTitle 'C:\Users\M\CLINE\09_PAKEITIMAI.md' $entry
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT_EXIT='+$LASTEXITCODE)
Write-Output '===== PATIKRA ====='
foreach($p in @($viskas,$desktop,'C:\Users\M\Desktop\2026010.24d\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md')){
  if(Test-Path -LiteralPath $p){$f=Get-Item -LiteralPath $p;Write-Output ('YRA: '+$p+' | '+$f.Length+' B')}else{Write-Output ('NERA: '+$p)}
}
Get-Content -LiteralPath $viskas -Encoding UTF8 -TotalCount 8