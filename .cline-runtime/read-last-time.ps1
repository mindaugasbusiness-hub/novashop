$root = 'C:\Users\M\CLINE\VISKAS'
Write-Output '===== PASKUTINE SESIJOS EILUTE ====='
Get-Content -LiteralPath (Join-Path $root '07_SESIJA_2026-10-25.md') -Encoding UTF8 -Tail 1
Write-Output '===== PASKUTINE VISKAS LOG EILUTE ====='
Get-Content -LiteralPath (Join-Path $root '08_VISKAS_LOG.txt') -Encoding UTF8 -Tail 1
Write-Output '===== FAILU LAIKAI ====='
Get-Item -LiteralPath (Join-Path $root '06_DABARTINE_BUSENA.md'), (Join-Path $root '07_SESIJA_2026-10-25.md'), (Join-Path $root '08_VISKAS_LOG.txt') | Select-Object Name, LastWriteTime | Format-Table -AutoSize
Write-Output '===== PC LAIKAS ====='
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
