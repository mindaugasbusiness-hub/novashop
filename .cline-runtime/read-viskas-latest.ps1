$root = 'C:\Users\M\CLINE\VISKAS'
Write-Output '===== 05 TODO ====='
Get-Content -LiteralPath (Join-Path $root '05_TODO.md') -Raw -Encoding UTF8
Write-Output "`n===== 06 DABARTINE BUSENA ====="
Get-Content -LiteralPath (Join-Path $root '06_DABARTINE_BUSENA.md') -Raw -Encoding UTF8
Write-Output "`n===== NAUJAUSIAS SESIJOS IRASAS ====="
$session = Get-ChildItem -LiteralPath $root -File -Filter '07_SESIJA_*.md' | Sort-Object Name -Descending | Select-Object -First 1
if ($session) { Get-Content -LiteralPath $session.FullName -Encoding UTF8 -Tail 40 }
Write-Output "`n===== VISKAS LOG ====="
Get-Content -LiteralPath (Join-Path $root '08_VISKAS_LOG.txt') -Encoding UTF8 -Tail 15
Write-Output "`n===== PAGRINDINIO DIENORASCIO PRADZIA ====="
Get-Content -LiteralPath 'C:\Users\M\CLINE\02_DIENORASTIS.md' -Encoding UTF8 -TotalCount 35
Write-Output "`n===== PAGRINDINIO TODO PRADZIA ====="
Get-Content -LiteralPath 'C:\Users\M\CLINE\04_TODO.md' -Encoding UTF8 -TotalCount 30
