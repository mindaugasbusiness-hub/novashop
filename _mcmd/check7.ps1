$ErrorActionPreference = 'Continue'
'=== node versija ==='
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' -v
'=== sqlite per node:sqlite ==='
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare('select id,name,active,nodes,updatedAt from workflow_entity order by name').all();
console.log('WORKFLOW KIEKIS: ' + rows.length);
for (const r of rows) {
  let nodes = [];
  try { nodes = JSON.parse(r.nodes || '[]'); } catch (e) {}
  const types = nodes.map(n => n.type);
  console.log('---');
  console.log('PAVADINIMAS: ' + r.name);
  console.log('ID: ' + r.id + ' | ACTIVE: ' + r.active + ' | MAZGU: ' + nodes.length + ' | ATNAUJINTA: ' + r.updatedAt);
  console.log('TIPAI: ' + [...new Set(types)].map(t => t.replace('n8n-nodes-base.', '')).join(', '));
  const wh = nodes.filter(n => /webhook|formTrigger/i.test(n.type));
  if (wh.length) console.log('WEBHOOK: ' + wh.map(n => (n.parameters && n.parameters.path) || n.name).join(', '));
}
try {
  const t = db.prepare("select name from sqlite_master where type='table'").all().map(x => x.name);
  console.log('=== LENTELES ===');
  console.log(t.join(', '));
} catch (e) { console.log('lenteliu klaida: ' + e.message); }
'@
$tmp = Join-Path $env:TEMP 'wf_dump.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' $tmp 2>&1 | Out-String
