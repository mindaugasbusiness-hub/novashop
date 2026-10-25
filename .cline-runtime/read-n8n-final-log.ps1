$f=(Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-final-*.out.log'|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName
Write-Output ('LOG='+$f)
Get-Content -LiteralPath $f -Encoding UTF8 -Tail 40
