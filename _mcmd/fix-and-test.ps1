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
'=== 1) IMPORT PRODUKCINIO (su pataisytu IF) ==='
& $node $bin 'import:workflow' '--input=C:\Users\M\CLINE\n8n\aukciono-stebejimas.json' 2>&1 | Select-String -Pattern 'Import|Successfully|Deactivating' | Out-String
'=== 2) PUBLISH PRODUKCINIO ==='
& $node $bin 'publish:workflow' '--id=aukcionas0000001' 2>&1 | Select-String -Pattern 'Publishing|Note' | Out-String
'=== 3) IMPORT TESTINIO ==='
& $node $bin 'import:workflow' '--input=C:\Users\M\CLINE\n8n\test-nukritimas.json' 2>&1 | Select-String -Pattern 'Import|Successfully' | Out-String
'=== 4) EXECUTE TESTINIS (turi eiti i PRANESTI saka) ==='
$t = & $node $bin 'execute' '--id=aukc-test00000001' '--rawOutput' 2>&1 | Out-String
($t -split "`n" | Select-String -Pattern 'lastNodeExecuted|statusCode|Execution was|error' | Select-Object -First 8) | Out-String
'=== 5) EXECUTE PRODUKCINIS (turi eiti i ok saka) ==='
$p = & $node $bin 'execute' '--id=aukcionas0000001' '--rawOutput' 2>&1 | Out-String
($p -split "`n" | Select-String -Pattern 'lastNodeExecuted|statusCode|Execution was|error' | Select-Object -First 8) | Out-String
'=== 6) PRANESIMU_LOG (paskutines 8) ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 8 -Encoding UTF8
'=== 7) EXECUTIONS ==='
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const ex = db.prepare('select id,workflowId,status,mode,startedAt from execution_entity order by id desc limit 8').all();
for (const e of ex) console.log('#' + e.id + ' ' + e.workflowId + ' ' + e.status + ' ' + e.mode + ' ' + e.startedAt);
'@
$tmp = Join-Path $env:TEMP 'ex3.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& $node $tmp 2>&1 | Out-String
