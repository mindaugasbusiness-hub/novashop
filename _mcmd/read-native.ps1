$ErrorActionPreference = 'Continue'
$f = 'C:\Users\M\Desktop\Kumstis\start-native.ps1'
$all = Get-Content $f
'BENDRAS EILUCIU: ' + $all.Count
$idx = (Select-String -Path $f -Pattern 'TOOLS_PORT|N8N_USER_FOLDER|GENERIC_TIMEZONE|NODE_EXE|NodeExe' | Select-Object -First 1).LineNumber
'PIRMA RAKTINE EILUTE: ' + $idx
$from = [Math]::Max(1, $idx - 45)
$to = [Math]::Min($all.Count, $idx + 15)
"=== EILUTES $from-$to ==="
$all[($from-1)..($to-1)] | ForEach-Object { $_ }
