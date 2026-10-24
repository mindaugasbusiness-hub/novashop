$ErrorActionPreference = 'Continue'
$js = @'
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('C:/Users/M/Desktop/Kumstis/runtime/n8n-data/.n8n/database.sqlite', { readOnly: true });
const row = db.prepare("select nodes from workflow_entity where id='kumstis0000000001'").get();
const nodes = JSON.parse(row.nodes);
const ifNode = nodes.find(n => n.type === 'n8n-nodes-base.if');
console.log('=== VEIKIANTIS IF NODE (is kumstis workflow) ===');
console.log(JSON.stringify(ifNode, null, 2));
'@
$tmp = Join-Path $env:TEMP 'if_dump.js'
Set-Content -Path $tmp -Value $js -Encoding UTF8
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' $tmp 2>&1 | Out-String
