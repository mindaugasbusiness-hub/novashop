# ============================================================
#  Cline Agent - nuotoline prieiga per HTTP (PowerShell + cloudflared)
#  Paleidimas (PowerShell, geriausia Administratorius):
#      iex (irm <URL>)
#  Nieko neinstaliuoja i sistema, naudoja tik PowerShell ir
#  cloudflared (Cloudflare, pasirasytas).
#  Stabdymas: Ctrl+C arba uzdaryti langa.
# ============================================================

$ErrorActionPreference = 'Continue'
$PORT   = 8787
$TOKEN  = -join ((48..57) + (97..122) | Get-Random -Count 28 | ForEach-Object { [char]$_ })
$pwshExe = if ($PSVersionTable.PSEdition -eq 'Desktop') { 'powershell.exe' } else { 'pwsh' }
$TMPDIR  = if ($env:TEMP) { $env:TEMP } else { [IO.Path]::GetTempPath() }

function Send-Text($ctx, $text, $code) {
    if (-not $code) { $code = 200 }
    try {
        $ctx.Response.StatusCode = $code
        $ctx.Response.ContentType = 'text/plain; charset=utf-8'
        $bytes = [Text.Encoding]::UTF8.GetBytes([string]$text)
        $ctx.Response.ContentLength64 = $bytes.Length
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        $ctx.Response.OutputStream.Close()
    } catch { }
}

function Get-Param($query, $name) {
    if ([string]::IsNullOrWhiteSpace($query)) { return $null }
    foreach ($pair in $query.TrimStart('?').Split('&')) {
        $kv = $pair.Split('=', 2)
        if ($kv.Count -eq 2 -and $kv[0] -eq $name) { return [Uri]::UnescapeDataString($kv[1]) }
    }
    return $null
}

function Read-Body($req) {
    if (-not $req.HasEntityBody) { return '' }
    $r = New-Object IO.StreamReader($req.InputStream, [Text.Encoding]::UTF8)
    $t = $r.ReadToEnd()
    $r.Close()
    return $t
}

function Invoke-Cmd([string]$cmd) {
    $id  = [guid]::NewGuid().ToString('N')
    $ps1 = Join-Path $script:TMPDIR "ca_$id.ps1"
    $out = Join-Path $script:TMPDIR "ca_$id.out"
    $err = Join-Path $script:TMPDIR "ca_$id.err"
    Set-Content -Path $ps1 -Value $cmd -Encoding UTF8
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $ps1 + '"'))
    $p = Start-Process -FilePath $script:pwshExe -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.WaitForExit(300000)
    if (-not $p.HasExited) { try { $p.Kill() } catch { } ; return 'TIMEOUT (5 min)' }
    $text = ''
    if (Test-Path $out) { $text += (Get-Content $out -Raw -ErrorAction SilentlyContinue) }
    if (Test-Path $err) { $text += (Get-Content $err -Raw -ErrorAction SilentlyContinue) }
    Remove-Item $ps1, $out, $err -Force -ErrorAction SilentlyContinue
    return $text
}

# ---------- 1. Tunelis (cloudflared) ----------
$tunnelUrl = $null
if ($env:CLINE_AGENT_NO_TUNNEL -ne '1') {
    $cf = Join-Path $TMPDIR 'cloudflared.exe'
    if (-not (Test-Path $cf)) {
        Write-Host 'Siunciu cloudflared...'
        Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $cf -UseBasicParsing
    }
    $errFile = Join-Path $TMPDIR 'cfagent.err'
    $outFile = Join-Path $TMPDIR 'cfagent.out'
    Remove-Item $errFile, $outFile -Force -ErrorAction SilentlyContinue
    $null = Start-Process -FilePath $cf -ArgumentList @('tunnel', '--url', "http://127.0.0.1:$PORT") -RedirectStandardError $errFile -RedirectStandardOutput $outFile -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $errFile) {
            $txt = Get-Content $errFile -Raw -ErrorAction SilentlyContinue
            $m = [regex]::Match([string]$txt, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
            if ($m.Success) { $tunnelUrl = $m.Value; break }
        }
    }
}

Write-Host ''
Write-Host '=========================================================' -ForegroundColor Green
Write-Host '  CLINE AGENTAS VEIKIA' -ForegroundColor Green
Write-Host '---------------------------------------------------------'
Write-Host ('  ADRESAS : ' + $tunnelUrl)
Write-Host ('  RAKTAS  : ' + $TOKEN)
Write-Host '---------------------------------------------------------'
Write-Host '  Atsiusk sitas DVI eilutes i Cline pokalbi.'
Write-Host '  Svarbu: NEUZVERK sio lango.' -ForegroundColor Yellow
Write-Host '=========================================================' -ForegroundColor Green
Write-Host ''

# ---------- 2. HTTP serveris ----------
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$PORT/")
try {
    $listener.Start()
} catch {
    Write-Host ''
    Write-Host ('KLAIDA: nepavyko paleisti serverio (' + $_.Exception.Message + ')') -ForegroundColor Red
    Write-Host 'Uzdaryk si langa ir paleisk komanda ADMINISTRATORIAUS lange.' -ForegroundColor Yellow
    Read-Host 'Spausk Enter, kad uzdarytum'
    return
}

while ($true) {
    $ctx = $null
    try {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        if ($req.Headers['X-Token'] -ne $TOKEN) { Send-Text $ctx 'forbidden' 403; continue }
        $path = $req.Url.AbsolutePath

        if ($path -eq '/ping') {
            Send-Text $ctx 'pong' 200
        }
        elseif ($path -eq '/exec') {
            $cmd = Read-Body $req
            Send-Text $ctx (Invoke-Cmd $cmd) 200
        }
        elseif ($path -eq '/read') {
            $p = Get-Param $req.Url.Query 'path'
            if (-not $p -or -not (Test-Path -LiteralPath $p)) { Send-Text $ctx 'not found' 404 }
            else { Send-Text $ctx ([Convert]::ToBase64String([IO.File]::ReadAllBytes($p))) 200 }
        }
        elseif ($path -eq '/write') {
            $p = Get-Param $req.Url.Query 'path'
            $b64 = Read-Body $req
            $dir = Split-Path -Parent $p
            if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            [IO.File]::WriteAllBytes($p, [Convert]::FromBase64String($b64))
            Send-Text $ctx ('written: ' + $p) 200
        }
        elseif ($path -eq '/ls') {
            $p = Get-Param $req.Url.Query 'path'
            if (-not $p) { $p = '.' }
            if (-not (Test-Path -LiteralPath $p)) { Send-Text $ctx 'not found' 404 }
            else {
                $items = Get-ChildItem -LiteralPath $p -Force -ErrorAction SilentlyContinue |
                    ForEach-Object {
                        $t = if ($_.PSIsContainer) { 'DIR ' } else { 'FILE' }
                        $len = if ($_.PSIsContainer) { '' } else { $_.Length }
                        '{0} {1,12} {2} {3}' -f $t, $len, $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm'), $_.Name
                    }
                Send-Text $ctx (($items -join "`r`n")) 200
            }
        }
        else {
            Send-Text $ctx 'not found' 404
        }
    } catch {
        if ($ctx) { Send-Text $ctx ('error: ' + $_.Exception.Message) 500 }
        Start-Sleep -Milliseconds 100
    }
}

