$ErrorActionPreference = 'Continue'
$root = 'C:\Users\M\Desktop\Kumstis'
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare('select id,name,active,versionId,updatedAt from workflow_entity order by name').all();
console.log('WORKFLOW KIEKIS: ' + rows.length);
for (const r of rows) console.log('  ' + r.id + ' | ' + r.name + ' | active=' + r.active + ' | ver=' + r.versionId + ' | ' + r.updatedAt);
console.log('=== TRIGGER STATUS (paskutines 6) ===');
const ts = db.prepare('select workflowId,nodeId,versionId,status,createdAt,updatedAt from workflow_publication_trigger_status order by updatedAt desc limit 6').all();
for (const t of ts) console.log('  ' + t.workflowId + ' ' + t.nodeId.substring(0, 12) + ' ver=' + String(t.versionId).substring(0, 12) + ' ' + t.status + ' upd=' + t.updatedAt);
console.log('=== EXECUTIONS (paskutines 6) ===');
const ex = db.prepare('select id,workflowId,status,mode,startedAt from execution_entity order by id desc limit 6').all();
for (const e of ex) console.log('  #' + e.id + ' ' + e.workflowId + ' ' + e.status + ' ' + e.mode + ' ' + e.startedAt);
'@
$tmp = Join-Path $env:TEMP 'st.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& (Join-Path $root 'runtime\node24\node.exe') $tmp 2>&1 | Out-String
'=== n8n.out.log (paskutines 15) ==='
Get-Content (Join-Path $root 'runtime\logs\n8n.out.log') -Tail 15 -Encoding UTF8
'=== CLINE HealthCheck uzduotis ==='
$t = Get-ScheduledTask -TaskName 'CLINE HealthCheck' -ErrorAction SilentlyContinue
if ($t) { $t.Actions | Format-List | Out-String; 'Trigeriai:'; $t.Triggers | Format-List | Out-String } else { 'nera' }
'=== start.ps1 (pirmos 20 eil.) ==='
Get-Content (Join-Path $root 'start.ps1') -TotalCount 20 -Encoding UTF8
