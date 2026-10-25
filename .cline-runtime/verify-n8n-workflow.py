import sqlite3, json
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
for r in db.execute("select id,name,active,activeVersionId,triggerCount,updatedAt from workflow_entity order by active desc,name"):
    print(dict(r))
print('--- EXECUTIONS ---')
for r in db.execute("select id,workflowId,status,mode,startedAt,stoppedAt from execution_entity order by id desc limit 8"):
    print(dict(r))
db.close()
