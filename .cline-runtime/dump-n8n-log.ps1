$f=(Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-cline-restart2-*.out.log'|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName
Get-Content -LiteralPath $f -Encoding UTF8
Write-Output '---ERR---'
$e=[IO.Path]::ChangeExtension($f,'.err.log');if(Test-Path $e){Get-Content $e -Encoding UTF8}
