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
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_HOST = 'localhost'
$env:N8N_PORT = '5678'
$env:N8N_PROTOCOL = 'http'
$node = Join-Path $root 'runtime\node24\node.exe'
$bin  = Join-Path $root 'runtime\n8n\node_modules\n8n\bin\n8n'
'=== IMPORT ==='
& $node $bin 'import:workflow' '--input=C:\Users\M\CLINE\n8n\aukciono-stebejimas.json' 2>&1 | Out-String
'import exit: ' + $LASTEXITCODE
'=== PUBLISH (aktyvavimas) ==='
& $node $bin 'publish:workflow' '--id=aukcionas0000001' 2>&1 | Out-String
'publish exit: ' + $LASTEXITCODE
'=== DB PATIKRA ==='
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare('select id,name,active,nodes from workflow_entity order by name').all();
console.log('WORKFLOW KIEKIS: ' + rows.length);
for (const r of rows) {
  const n = JSON.parse(r.nodes || '[]');
  console.log('  ' + r.id + ' | ' + r.name + ' | active=' + r.active + ' | mazgu=' + n.length);
}
'@
$tmp = Join-Path $env:TEMP 'wf_check.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& $node $tmp 2>&1 | Out-String
