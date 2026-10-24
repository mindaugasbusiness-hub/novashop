$ErrorActionPreference = 'Continue'
$root = 'C:\Users\M\Desktop\Kumstis'
$f = Join-Path $root 'start-native.ps1'
$all = Get-Content $f
"=== EILUTES 155-205 ==="
$all[154..204] | ForEach-Object { $_ }
'=== KAS KLAUSO 5678/5679/6333/8090 ==='
foreach ($p in 5678, 5679, 6333, 8090, 8791) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($c) { $pr = Get-Process -Id $c[0].OwningProcess -ErrorAction SilentlyContinue; "$p -> PID " + $c[0].OwningProcess + ' (' + $pr.ProcessName + ', pradzia ' + $pr.StartTime + ')' } else { "$p -> niekas neklauso" }
}
'=== broker env kintamojo pavadinimas ==='
Select-String -Path 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\dist\**\*.js' -Pattern "Task Broker's port" -List -ErrorAction SilentlyContinue | Select-Object -First 2 | ForEach-Object { $_.Path }
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\dist' -Recurse -Filter '*.js' -ErrorAction SilentlyContinue | Select-String -Pattern "Task Broker's port" -List -ErrorAction SilentlyContinue | Select-Object -First 2 | ForEach-Object { $_.Path + ' :: ' + $_.Line.Trim().Substring(0,[Math]::Min(200,$_.Line.Trim().Length)) }
