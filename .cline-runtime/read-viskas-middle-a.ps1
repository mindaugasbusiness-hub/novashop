$lines = Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\VISKAS_VISKAS.md' -Encoding UTF8
Write-Output ('LINES=' + $lines.Count)
$lines | Select-Object -Skip 70 -First 190
