$ErrorActionPreference = 'Continue'
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const t = db.prepare("select name from sqlite_master where type='table' and name like '%trigger%'").all().map(x => x.name);
console.log('TRIGGER LENTELES: ' + t.join(', '));
for (const tab of t) {
  try {
    const rows = db.prepare('select * from ' + tab).all();
    console.log('--- ' + tab + ' (' + rows.length + ') ---');
    for (const r of rows.slice(-6)) console.log('  ' + JSON.stringify(r).substring(0, 220));
  } catch (e) { console.log('  ' + tab + ' klaida: ' + e.message); }
}
console.log('=== EXECUTIONS (paskutines 12) ===');
try {
  const ex = db.prepare('select id,workflowId,status,mode,startedAt,stoppedAt from execution_entity order by id desc limit 12').all();
  for (const e of ex) console.log('  #' + e.id + ' wf=' + e.workflowId + ' ' + e.status + ' ' + e.mode + ' ' + e.startedAt + ' -> ' + e.stoppedAt);
} catch (e) { console.log('exec klaida: ' + e.message); }
console.log('=== scheduled_job / poller_state ===');
for (const tab of ['scheduled_job', 'poller_state', 'workflow_publish_history']) {
  try {
    const rows = db.prepare('select * from ' + tab).all();
    console.log('--- ' + tab + ' (' + rows.length + ') ---');
    for (const r of rows.slice(-4)) console.log('  ' + JSON.stringify(r).substring(0, 240));
  } catch (e) { console.log('  ' + tab + ': ' + e.message); }
}
'@
$tmp = Join-Path $env:TEMP 'exec_check.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' $tmp 2>&1 | Out-String
