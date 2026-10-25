$log=(Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-cline-restart-*.out.log'|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName
Write-Output ('SIZE='+(Get-Item -LiteralPath $log).Length)
Get-Content -LiteralPath $log -Encoding UTF8 -Tail 120
Write-Output '---ERR---'
$err=[IO.Path]::ChangeExtension($log,'.err.log')
if(Test-Path -LiteralPath $err){Write-Output ('ERRSIZE='+(Get-Item -LiteralPath $err).Length);Get-Content -LiteralPath $err -Encoding UTF8 -Tail 80}
