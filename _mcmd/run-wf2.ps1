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
$env:WEBHOOK_URL = 'http://localhost:5678/'
$env:GENERIC_TIMEZONE = 'Europe/Vilnius'
$env:EXECUTIONS_TIMEOUT = '3600'
$env:EXECUTIONS_TIMEOUT_MAX = '7200'
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$env:N8N_RESTRICT_FILE_ACCESS_TO = (Join-Path $root 'DeFi ataskaitos')
'=== n8n execute --id=aukcionas0000001 (broker 5699) ==='
& (Join-Path $root 'runtime\node24\node.exe') (Join-Path $root 'runtime\n8n\node_modules\n8n\bin\n8n') 'execute' '--id=aukcionas0000001' 2>&1 | Out-String
'execute exit: ' + $LASTEXITCODE
'=== EXECUTION IRASAI DB ==='
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const ex = db.prepare('select id,workflowId,status,mode,startedAt,stoppedAt from execution_entity order by id desc limit 6').all();
for (const e of ex) console.log('#' + e.id + ' wf=' + e.workflowId + ' ' + e.status + ' ' + e.mode + ' ' + e.startedAt + ' -> ' + e.stoppedAt);
'@
$tmp = Join-Path $env:TEMP 'ex2.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& (Join-Path $root 'runtime\node24\node.exe') $tmp 2>&1 | Out-String
