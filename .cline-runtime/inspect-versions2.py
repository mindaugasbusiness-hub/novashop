import sqlite3, json
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
for r in db.execute("select id,name,active,activeVersionId,versionCounter,updatedAt,nodes from workflow_entity where name like '%Žvėris%' or id='clineAuto0000001'"):
    d=dict(r);nodes=json.loads(d.pop('nodes') or '[]')
    print('ENTITY',d)
    print('ENTITY_NODES',[(n.get('name'),n.get('type'),n.get('typeVersion')) for n in nodes])
for r in db.execute("select versionId,workflowId,createdAt,nodes from workflow_history where workflowId='clineAuto0000001' order by createdAt desc limit 5"):
    d=dict(r);nodes=json.loads(d.pop('nodes') or '[]')
    print('HISTORY',d)
    print('HISTORY_NODES',[(n.get('name'),n.get('type'),n.get('typeVersion')) for n in nodes])
db.close()
