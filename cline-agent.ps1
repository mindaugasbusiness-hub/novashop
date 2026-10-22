# ============================================================
#  Cline Agent - nuotoline prieiga per HTTP (PowerShell + cloudflared)
#  Paleidimas:  iex (irm <URL>)
#  Stabdymas: Ctrl+C arba uzdaryti langa.
# ============================================================

$ErrorActionPreference = 'Continue'
$PORT   = 8787
$TOKEN  = -join ((48..57) + (97..122) | Get-Random -Count 28 | ForEach-Object { [char]$_ })
$pwshExe = if ($PSVersionTable.PSEdition -eq 'Desktop') { 'powershell.exe' } else { 'pwsh' }
$TMPDIR  = if ($env:TEMP) { $env:TEMP } else { [IO.Path]::GetTempPath() }
$ERRFILE = Join-Path $TMPDIR 'cfagent.err'

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

# ---------- 1. Serveris (pirmiau, kad cloudflared rastu origin) ----------
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$PORT/")
try {
    $listener.Start()
} catch {
    Write-Host ''
    Write-Host ('KLAIDA: nepavyko paleisti serverio (' + $_.Exception.Message + ')') -ForegroundColor Red
    Write-Host 'Uzdaryk langa ir paleisk komanda ADMINISTRATORIAUS lange.' -ForegroundColor Yellow
    Read-Host 'Spausk Enter'
    return
}
Write-Host ('Serveris klauso 127.0.0.1:' + $PORT) -ForegroundColor DarkGray

# ---------- 2. Tunelis ----------
$tunnelUrl = $null
$cfOk = $false
if ($env:CLINE_AGENT_NO_TUNNEL -ne '1') {
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $cf = Join-Path $TMPDIR 'cloudflared.exe'
    if (-not (Test-Path $cf)) {
        Write-Host 'Siunciu cloudflared...'
        Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $cf -UseBasicParsing
    }
    Remove-Item $ERRFILE -Force -ErrorAction SilentlyContinue
    $null = Start-Process -FilePath $cf -ArgumentList @('tunnel', '--url', "http://127.0.0.1:$PORT", '--no-autoupdate') -RedirectStandardError $ERRFILE -RedirectStandardOutput (Join-Path $TMPDIR 'cfagent.out') -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $ERRFILE) {
            $txt = [string](Get-Content $ERRFILE -Raw -ErrorAction SilentlyContinue)
            if (-not $tunnelUrl) {
                $m = [regex]::Match($txt, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
                if ($m.Success) { $tunnelUrl = $m.Value }
            }
            if ($txt -match 'Registered tunnel connection') { $cfOk = $true; break }
            if ($txt -match 'no more connections active and exiting') { break }
        }
    }
}

Write-Host ''
Write-Host '=========================================================' -ForegroundColor Green
if ($cfOk -or $env:CLINE_AGENT_NO_TUNNEL -eq '1') {
    Write-Host '  CLINE AGENTAS VEIKIA' -ForegroundColor Green
} else {
    Write-Host '  DEMESIO: TUNELIS NEPRISIJUNGE' -ForegroundColor Red
}
Write-Host '---------------------------------------------------------'
Write-Host ('  ADRESAS : ' + $tunnelUrl)
Write-Host ('  RAKTAS  : ' + $TOKEN)
Write-Host '---------------------------------------------------------'
if ($cfOk -or $env:CLINE_AGENT_NO_TUNNEL -eq '1') {
    Write-Host '  Atsiusk sitas DVI eilutes i Cline pokalbi.'
    Write-Host '  Svarbu: NEUZVERK sio lango.' -ForegroundColor Yellow
} else {
    Write-Host '  Paskutines cloudflared zinutes:' -ForegroundColor Yellow
    if (Test-Path $ERRFILE) { Get-Content $ERRFILE -Tail 12 | ForEach-Object { Write-Host ('   ' + $_) } }
    Write-Host '  Nukopijuok jas ir atsiusk i Cline pokalbi.' -ForegroundColor Yellow
}
Write-Host '=========================================================' -ForegroundColor Green
Write-Host ''

# ---------- 3. Uzklausu apdorojimas ----------
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
            Send-Text $ctx (Invoke-Cmd (Read-Body $req)) 200
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
        elseif ($path -eq '/diag') {
            $t = ''
            if (Test-Path $ERRFILE) { $t += ((Get-Content $ERRFILE -Tail 20) -join "`r`n") }
            $t += "`r`n--- procesai ---`r`n"
            $t += ((Get-Process cloudflared -ErrorAction SilentlyContinue | ForEach-Object { 'cloudflared pid=' + $_.Id }) -join "`r`n")
            Send-Text $ctx $t 200
        }
        else {
            Send-Text $ctx 'not found' 404
        }
    } catch {
        if ($ctx) { Send-Text $ctx ('error: ' + $_.Exception.Message) 500 }
        Start-Sleep -Milliseconds 100
    }
}
