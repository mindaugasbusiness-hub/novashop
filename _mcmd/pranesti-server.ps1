# PRANESTI SERVER v1 - vietinis HTTP tiltas: n8n -> pranesti.ps1 (ntfy + SMS + Windows + log)
# Klauzo tik 127.0.0.1:8791. Endpointai:
#   GET  /healthz                      -> ok
#   POST /pranesti   JSON {tema,tekstas,svarbu}  -> paleidzia pranesti.ps1, grazina JSON su log eilutemis
#   GET  /log?n=20                     -> PRANESIMU_LOG.txt paskutines eilutes
param([int]$Port = 8791)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Web
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pranesti = Join-Path $here 'pranesti.ps1'
$log = 'C:\Users\M\CLINE\PRANESIMU_LOG.txt'
$srvLog = 'C:\Users\M\CLINE\tools\pranesti-server.log'
function WLog($m) { Add-Content -Path $srvLog -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
function Respond($ctx, $code, $text, $ctype) {
    try {
        $ctx.Response.StatusCode = $code
        $ctx.Response.ContentType = $ctype
        $b = [Text.Encoding]::UTF8.GetBytes([string]$text)
        $ctx.Response.ContentLength64 = $b.Length
        $ctx.Response.OutputStream.Write($b, 0, $b.Length)
        $ctx.Response.OutputStream.Close()
    } catch { }
}
function ReadBody($req) {
    if (-not $req.HasEntityBody) { return '' }
    $r = New-Object IO.StreamReader($req.InputStream, [Text.Encoding]::UTF8)
    $t = $r.ReadToEnd(); $r.Close(); return $t
}
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
try { $listener.Start() } catch { WLog ('START KLAIDA: ' + $_.Exception.Message); exit 1 }
WLog ('server start, port ' + $Port + ', pranesti.ps1 yra: ' + (Test-Path $pranesti))
while ($listener.IsListening) {
    try {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        $path = $req.Url.AbsolutePath
        $q = [System.Web.HttpUtility]::ParseQueryString($req.Url.Query)
        if ($path -eq '/healthz') { Respond $ctx 200 'ok' 'text/plain; charset=utf-8'; continue }
        if ($path -eq '/log') {
            $n = 20; if ($q['n']) { $n = [int]$q['n'] }
            $tail = if (Test-Path $log) { (Get-Content $log -Tail $n -Encoding UTF8) -join "`n" } else { 'log nerastas' }
            Respond $ctx 200 $tail 'text/plain; charset=utf-8'; continue
        }
        if ($path -eq '/pranesti') {
            $tema = ''; $tekstas = ''; $svarbu = $false
            $body = ReadBody $req
            if ($body) {
                try {
                    $j = $body | ConvertFrom-Json
                    if ($j.tema) { $tema = [string]$j.tema }
                    if ($j.tekstas) { $tekstas = [string]$j.tekstas }
                    if ($j.svarbu) { $svarbu = [bool]$j.svarbu }
                } catch { WLog ('body parse KLAIDA: ' + $_.Exception.Message) }
            }
            if (-not $tema -and $q['tema']) { $tema = $q['tema'] }
            if (-not $tekstas -and $q['tekstas']) { $tekstas = $q['tekstas'] }
            if ($q['svarbu'] -eq '1') { $svarbu = $true }
            if (-not $tema) { $tema = 'n8n pranesimas' }
            if (-not $tekstas) { $tekstas = 'be teksto' }
            WLog ('pranesti: ' + $tema + ' | svarbu=' + $svarbu)
            $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $pranesti, '-Tema', $tema, '-Tekstas', $tekstas)
            if ($svarbu) { $a += '-Svarbu' }
            $out = & powershell.exe @a 2>&1 | Out-String
            $tail = if (Test-Path $log) { (Get-Content $log -Tail 4 -Encoding UTF8) -join ' | ' } else { '' }
            $payload = @{ ok = $true; tema = $tema; svarbu = $svarbu; log = $tail } | ConvertTo-Json -Compress
            Respond $ctx 200 $payload 'application/json; charset=utf-8'
            continue
        }
        Respond $ctx 404 'not found' 'text/plain; charset=utf-8'
    } catch { WLog ('KLAIDA: ' + $_.Exception.Message); Start-Sleep -Milliseconds 200 }
}
