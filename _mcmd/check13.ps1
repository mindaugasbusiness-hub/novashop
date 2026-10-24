$ErrorActionPreference = 'Continue'
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare('select id,name,nodes from workflow_entity').all();
for (const r of rows) {
  const nodes = JSON.parse(r.nodes || '[]');
  console.log('### ' + r.name + ' (' + r.id + ')');
  for (const n of nodes) console.log('  ' + n.type + ' v' + n.typeVersion + '  [' + n.name + ']' + (n.onError ? ' onError=' + n.onError : ''));
}
const s = db.prepare('select key,value from settings').all();
console.log('=== settings ===');
for (const x of s) console.log('  ' + x.key + ' = ' + String(x.value).substring(0, 80));
'@
$tmp = Join-Path $env:TEMP 'wf_nodes.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' $tmp 2>&1 | Out-String
