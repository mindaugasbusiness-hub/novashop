$root = 'C:\Users\M\CLINE\VISKAS'
Write-Output '===== 06 DABARTINE BUSENA ====='
Get-Content -LiteralPath (Join-Path $root '06_DABARTINE_BUSENA.md') -Raw -Encoding UTF8
Write-Output "`n===== NAUJAUSIA SESIJA ====="
$session = Get-ChildItem -LiteralPath $root -File -Filter '07_SESIJA_*.md' | Sort-Object Name -Descending | Select-Object -First 1
if ($session) { Write-Output $session.FullName; Get-Content -LiteralPath $session.FullName -Encoding UTF8 -Tail 25 }
Write-Output "`n===== ATSTATYMO LOG ====="
$restore = Join-Path $root '09_ATSTATYMO_LOG.txt'
if (Test-Path -LiteralPath $restore) { Get-Content -LiteralPath $restore -Encoding UTF8 -Tail 40 }
Write-Output "`n===== VISKAS LOG ====="
Get-Content -LiteralPath (Join-Path $root '08_VISKAS_LOG.txt') -Encoding UTF8 -Tail 12
