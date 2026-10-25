$ErrorActionPreference='Stop'
$v='C:\Users\M\CLINE\VISKAS'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE\VISKAS"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath (Join-Path $v 'DUOK_NAUJAM_AI.txt') -Destination (Join-Path $bak 'DUOK_NAUJAM_AI.txt')
Copy-Item -LiteralPath (Join-Path $v 'NUKOPIJUOTI NUORODA.ps1') -Destination (Join-Path $bak 'NUKOPIJUOTI NUORODA.ps1')
$text='Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.'
[IO.File]::WriteAllText((Join-Path $v 'DUOK_NAUJAM_AI.txt'),$text+"`r`n",[Text.UTF8Encoding]::new($false))
$p=Join-Path $v 'NUKOPIJUOTI NUORODA.ps1'
$old=[IO.File]::ReadAllText($p)
$new=$old.Replace('C:\Users\M\CLINE\VISKAS\00_SKAITYK_PIRMA.md','C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md')
if($new -eq $old){throw 'Nuorodos tekste nepakeista'}
[IO.File]::WriteAllText($p,$new,[Text.UTF8Encoding]::new($false))
Write-Output ('BACKUP='+$bak)
Write-Output ('DUOK='+(Get-Content -LiteralPath (Join-Path $v 'DUOK_NAUJAM_AI.txt') -Raw -Encoding UTF8).Trim())
Select-String -LiteralPath $p -Pattern '00_SKAITYK_' | Select-Object LineNumber,Line | Format-Table -AutoSize
