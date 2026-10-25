$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
$tab=$null
try {
    $json=& curl.exe -sS --max-time 8 -X PUT 'http://127.0.0.1:9222/json/new?http://127.0.0.1:8091/' 2>&1 | Out-String
    $tab=$json|ConvertFrom-Json
    Write-Output ('TEST_TAB='+$tab.id)
    $conn=Get-NetTCPConnection -LocalPort 8091 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
    if(-not $conn){throw '8091 neveikia pries testa'}
    Write-Output ('STOP_UI_PID='+$conn.OwningProcess)
    Stop-Process -Id $conn.OwningProcess -Force
    Start-Sleep -Seconds 2
    $after=Get-NetTCPConnection -LocalPort 8091 -State Listen -ErrorAction SilentlyContinue
    Write-Output ('PORT_PO_SUSTABDYMO='+[bool]$after)
    Write-Output '===== ENSURE PER API ====='
    & curl.exe -sS --max-time 60 -X POST -H "X-Automation-Key: $token" -w "`nENSURE_HTTP=%{http_code}`n" 'http://127.0.0.1:8792/ensure'
    Write-Output '===== PUSLAPIS PO ====='
    & curl.exe -sS -o NUL --max-time 8 -w 'PAGE_HTTP=%{http_code}`n' 'http://127.0.0.1:8091/'
    Write-Output '===== F5 LOG ====='
    Get-Content -LiteralPath 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt' -Encoding UTF8 -Tail 8
} catch {
    Write-Output ('TEST_KLAIDA='+$_.Exception.Message)
} finally {
    if($tab -and $tab.id){try{& curl.exe -sS --max-time 8 ('http://127.0.0.1:9222/json/close/'+$tab.id)|Out-Null;Write-Output 'TEST_TAB_CLOSED'}catch{}}
}
