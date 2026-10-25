$ErrorActionPreference='Stop'
$path='C:\Users\M\CLINE\tools\startup-automation.ps1'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE\tools"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath $path -Destination (Join-Path $bak 'startup-automation.ps1')
$text=[IO.File]::ReadAllText($path)
$anchor="function Log([string]`$text) { Add-Content -LiteralPath `$log -Value ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), `$text) -Encoding UTF8 }"
if(-not $text.Contains($anchor)){throw 'Nerastas tikslinis startup-automation blokas'}
$addition=@'

# Uztikrina, kad n8n turetu vietini automatizavimo tilta po PC ijungimo.
try {
    $apiUp = Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue
    if (-not $apiUp) {
        $loop = 'C:\Users\M\CLINE\tools\automation-server-loop.ps1'
        Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',$loop) -WindowStyle Hidden
        for ($i=0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            if (Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue) { break }
        }
        Log 'AUTOMATION_API_STARTED'
    } else {
        Log 'AUTOMATION_API_JAU_VEIKIA'
    }
} catch { Log ('AUTOMATION_API_KLAIDA: ' + $_.Exception.Message) }
'@

$new=$text.Replace($anchor,$anchor+$addition)
if($new -eq $text){throw 'Pakeitimas neivyko'}
[IO.File]::WriteAllText($path,$new,[Text.UTF8Encoding]::new($false))
Write-Output ('BACKUP='+$bak)
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $path 2>&1 | Out-String -Width 2000
Write-Output ('STARTUP_TEST_EXIT='+$LASTEXITCODE)
Get-Content -LiteralPath 'C:\Users\M\CLINE\STARTUP_AUTOMATION_LOG.txt' -Encoding UTF8 -Tail 8
