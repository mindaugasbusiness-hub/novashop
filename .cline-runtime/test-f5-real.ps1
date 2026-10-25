$created=$null
try {
    $created=Invoke-RestMethod -Method Put -Uri 'http://127.0.0.1:9222/json/new?http://127.0.0.1:8091/' -TimeoutSec 10
    Write-Output ('TAB_ID='+$created.id+' URL='+$created.url)
    Start-Sleep -Seconds 2
    & 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'C:\Users\M\CLINE\tools\zveris-ensure.ps1' -TestRefresh 2>&1 | Out-String -Width 2000
    Write-Output ('F5_EXIT='+$LASTEXITCODE)
    Get-Content -LiteralPath 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt' -Encoding UTF8 -Tail 3
} finally {
    if($created -and $created.id){
        try { Invoke-RestMethod -Uri ('http://127.0.0.1:9222/json/close/'+$created.id) -Method Get -TimeoutSec 8 | Out-Null; Write-Output 'TEST_TAB_CLOSED' } catch { Write-Output ('TAB_CLOSE_ERROR='+$_.Exception.Message) }
    }
}
