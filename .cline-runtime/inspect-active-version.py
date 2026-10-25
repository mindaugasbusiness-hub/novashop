import sqlite3, json
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
print('HISTORY_COLS',[r['name'] for r in db.execute('pragma table_info(workflow_history)')])
for r in db.execute("select * from workflow_entity where id='clineAuto0000001'"):
    d=dict(r)
    print('ENTITY',{k:d[k] for k in d if k in ('id','name','active','activeVersionId','triggerCount','versionCounter','updatedAt','staticData')})
    nodes=json.loads(d['nodes'] or '[]')
    print('NODES',[(n.get('name'),n.get('type'),n.get('typeVersion')) for n in nodes])
    print('SETTINGS',d.get('settings'))
for r in db.execute("select id,workflowId,versionId,createdAt,updatedAt from workflow_history where workflowId='clineAuto0000001' order by createdAt desc"):
    print('HISTORY',dict(r))
for r in db.execute("select e.id,e.workflowId,e.status,e.mode,e.startedAt,e.stoppedAt from execution_entity e where e.workflowId='clineAuto0000001' order by e.id desc limit 5"):
    print('EXEC',dict(r))
db.close()
