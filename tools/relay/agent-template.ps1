$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$base = '__BASE__'
$key  = '__KEY__'
$cid  = [guid]::NewGuid().ToString('N')
$TMP  = if ($env:TEMP) { $env:TEMP } else { '.' }

function Run-Cmd([string]$cmd) {
    $id  = [guid]::NewGuid().ToString('N')
    $ps1 = Join-Path $TMP "ca_$id.ps1"
    $out = Join-Path $TMP "ca_$id.out"
    $err = Join-Path $TMP "ca_$id.err"
    Set-Content -Path $ps1 -Value $cmd -Encoding UTF8
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $ps1 + '"'))
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.WaitForExit(300000)
    if (-not $p.HasExited) { try { $p.Kill() } catch { } ; return 'TIMEOUT (5 min)' }
    $t = ''
    if (Test-Path $out) { $t += (Get-Content $out -Raw -ErrorAction SilentlyContinue) }
    if (Test-Path $err) { $t += (Get-Content $err -Raw -ErrorAction SilentlyContinue) }
    Remove-Item $ps1, $out, $err -Force -ErrorAction SilentlyContinue
    return $t
}

$hdr = @{ 'X-Key' = $key }
Write-Host ''
Write-Host '=========================================================' -ForegroundColor Green
Write-Host '  CLINE PRISIJUNGE. Laukiu komandu...' -ForegroundColor Green
Write-Host ('  Klientas: ' + $cid.Substring(0, 8)) -ForegroundColor DarkGray
Write-Host '  NEUZVERK sio lango.' -ForegroundColor Yellow
Write-Host '=========================================================' -ForegroundColor Green
Write-Host ''

$since = 0
while ($true) {
    try {
        $r = Invoke-RestMethod -Uri "$base/next?since=$since&cid=$cid" -Headers $hdr -TimeoutSec 25
        if ($r -and $r.id) {
            $since = [int]$r.id
            Write-Host ('> ' + [string]$r.cmd) -ForegroundColor Cyan
            $res = Run-Cmd ([string]$r.cmd)
            $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($res))
            Invoke-RestMethod -Uri "$base/out?id=$since" -Method POST -Headers $hdr -Body $b64 -TimeoutSec 60 | Out-Null
            Write-Host '  [ivykdyta]' -ForegroundColor DarkGray
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}
