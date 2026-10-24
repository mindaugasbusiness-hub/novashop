$ErrorActionPreference = 'Continue'
$root = 'C:\Users\M\Desktop\Kumstis'
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $kv = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($kv[0].Trim(), $kv[1].Trim().Trim('"'), 'Process')
    }
}
$env:N8N_USER_FOLDER = Join-Path $root 'runtime\n8n-data'
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
$env:N8N_RUNNERS_MODE = 'internal'
$env:N8N_RUNNERS_TASK_BROKER_PORT = '5699'
$env:N8N_RUNNERS_BROKER_PORT = '5699'
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_HOST = 'localhost'
$env:N8N_PORT = '5678'
$env:N8N_PROTOCOL = 'http'
$env:GENERIC_TIMEZONE = 'Europe/Vilnius'
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$node = Join-Path $root 'runtime\node24\node.exe'
$bin  = Join-Path $root 'runtime\n8n\node_modules\n8n\bin\n8n'
'=== LOG PRIES ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 2 -Encoding UTF8
'=== IMPORT TESTINIO ==='
& $node $bin 'import:workflow' '--input=C:\Users\M\CLINE\n8n\test-nukritimas.json' 2>&1 | Out-String
'import exit: ' + $LASTEXITCODE
'=== EXECUTE TESTINIO ==='
$out = & $node $bin 'execute' '--id=aukc-test00000001' 2>&1 | Out-String
$out.Substring([Math]::Max(0, $out.Length - 2500))
'execute exit: ' + $LASTEXITCODE
'=== LOG PO (paskutines 8) ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 8 -Encoding UTF8
