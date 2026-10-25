$ErrorActionPreference = 'Continue'
$python = 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe'
$collector = 'C:\Users\M\CLINE\tools\surinkti-viska.py'
$ensure = 'C:\Users\M\CLINE\tools\zveris-ensure.ps1'
$log = 'C:\Users\M\CLINE\STARTUP_AUTOMATION_LOG.txt'
function Log([string]$text) { Add-Content -LiteralPath $log -Value ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $text) -Encoding UTF8 }
try {
    & $python -X utf8 $collector 2>&1 | ForEach-Object { Log ('SURINKIMAS: ' + $_) }
    Log ('SURINKIMAS_EXIT=' + $LASTEXITCODE)
} catch { Log ('SURINKIMO_KLAIDA: ' + $_.Exception.Message) }
try {
    & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ensure 2>&1 | ForEach-Object { Log ('ZVERIS: ' + $_) }
    Log ('ZVERIS_EXIT=' + $LASTEXITCODE)
} catch { Log ('ZVERIS_KLAIDA: ' + $_.Exception.Message) }
