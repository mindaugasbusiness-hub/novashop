$root = 'C:\Users\M\CLINE'
Write-Output '===== SESIJOS ATASKAITA ====='
$report = Join-Path $root 'SESIJOS_ATASKAITA.txt'
if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report -Encoding UTF8 -Tail 180 }
Write-Output "`n===== VISKAS DABARTINE BUSENA ====="
$state = Join-Path $root 'VISKAS\06_DABARTINE_BUSENA.md'
if (Test-Path -LiteralPath $state) { Get-Content -LiteralPath $state -Raw -Encoding UTF8 }
Write-Output "`n===== VISKAS LOG ====="
$log = Join-Path $root 'VISKAS\08_VISKAS_LOG.txt'
if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Encoding UTF8 -Tail 20 }
Write-Output "`n===== NAUJAUSI CLINE FAILAI ====="
Get-ChildItem -LiteralPath $root -File | Sort-Object LastWriteTime -Descending | Select-Object -First 15 Name, Length, LastWriteTime | Format-Table -AutoSize
