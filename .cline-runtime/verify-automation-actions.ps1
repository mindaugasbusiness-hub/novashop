Write-Output '===== AUTOMATION API LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 12
Write-Output '===== ZVERIS AUTO LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt' -Encoding UTF8 -Tail 6 -ErrorAction SilentlyContinue
Write-Output '===== VISKAS ISTORIJOS LAIKAS ====='
Get-Item 'C:\Users\M\CLINE\VISKAS\00_VISKAS_PILNA_ISTORIJA.md','C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md'|Select-Object Name,Length,LastWriteTime|Format-Table -AutoSize
