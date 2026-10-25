param([switch]$TestRefresh)
$ErrorActionPreference = 'Continue'
$Root = 'C:\Users\M\Desktop\pakeitimai 111\_zveris_watch'
$Python = 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe'
$Node = 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
$Refresh = 'C:\Users\M\CLINE\tools\zveris-refresh.cjs'
$Static = 'C:\workspace\zveris\ui\static\index.html'
$Log = 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt'

function HttpStatus([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
        return [int]$r.StatusCode
    } catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return 0
    }
}

function Log([string]$Message) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    Write-Output $line
}

$api = HttpStatus 'http://127.0.0.1:8091/api/status'
$page = HttpStatus 'http://127.0.0.1:8091/'
if ($TestRefresh) {
    if (Test-Path -LiteralPath $Refresh) {
        & $Node $Refresh 2>&1 | ForEach-Object { Log ('F5: ' + $_) }
    }
    exit 0
}
if ($api -eq 200 -and $page -eq 200) { exit 0 }

$repaired = $false
if (-not (Test-Path -LiteralPath $Static)) {
    $backup = Get-ChildItem -LiteralPath 'C:\Users\M\CLINE\BACKUPS' -Recurse -File -Filter 'index.html' -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match 'workspace\\zveris\\ui\\static\\index\.html$' } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($backup) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Static) -Force | Out-Null
        Copy-Item -LiteralPath $backup.FullName -Destination $Static
        Log ('INDEX atstatytas is ' + $backup.FullName)
        $repaired = $true
        $api = HttpStatus 'http://127.0.0.1:8091/api/status'
        $page = HttpStatus 'http://127.0.0.1:8091/'
    } else {
        Log 'KLAIDA: index.html ir jo kopijos nera'
    }
}

if ($api -ne 200 -or $page -ne 200) {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'uvicorn\s+ui_app:app' -and $_.CommandLine -match '--port\s+8091'
    }
    foreach ($proc in $processes) {
        Log ('SUSTABDYTAS tik ui_app PID=' + $proc.ProcessId)
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $out = "C:\Users\M\CLINE\logs\zveris-auto-$stamp.out.log"
    $err = "C:\Users\M\CLINE\logs\zveris-auto-$stamp.err.log"
    New-Item -ItemType Directory -Path 'C:\Users\M\CLINE\logs' -Force | Out-Null
    $env:ZVERIS_UI_PORT = '8091'
    Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','ui_app:app','--host','127.0.0.1','--port','8091') -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $api = HttpStatus 'http://127.0.0.1:8091/api/status'
        $page = HttpStatus 'http://127.0.0.1:8091/'
        if ($api -eq 200 -and $page -eq 200) { break }
    }
    Log ('ZVERIS paleistas; API=' + $api + ' PUSLAPIS=' + $page)
    $repaired = $true
}

if ($repaired -and (Test-Path -LiteralPath $Refresh)) {
    & $Node $Refresh 2>&1 | ForEach-Object { Log ('F5: ' + $_) }
}
if ($api -eq 200 -and $page -eq 200) {
    Log 'ZVERIS SVEIKAS: API=200 PUSLAPIS=200'
    exit 0
}
Log ('ZVERIS NESUTVARKYTAS: API=' + $api + ' PUSLAPIS=' + $page)
exit 1
