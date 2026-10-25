import json, sqlite3, re
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row

def rows(sql,args=()):
    return db.execute(sql,args).fetchall()

def clean(value,key=''):
    if re.search(r'(pass|token|secret|key|auth|cookie|credential)',key,re.I):
        return '[PASLEPTA]'
    if isinstance(value,dict):
        return {k:clean(v,k) for k,v in value.items() if k not in ('credentials','jsCode','functionCode')}
    if isinstance(value,list):
        return [clean(v,key) for v in value]
    if isinstance(value,str) and len(value)>500:
        return value[:500]+'...'
    return value

print('===== WORKFLOW LENTELES STULPELIAI =====')
print(', '.join(r['name'] for r in rows('pragma table_info(workflow_entity)')))
workflows=rows('select * from workflow_entity order by active desc, name')
print('\n===== WORKFLOW =====')
for w in workflows:
    print(f"\nID={w['id']} | {w['name']} | ACTIVE={w['active']} | updated={w['updatedAt']}")
    nodes=json.loads(w['nodes'] or '[]')
    print('NODES='+str(len(nodes)))
    for n in nodes:
        typ=n.get('type','')
        params=n.get('parameters') or {}
        keep={}
        for k,v in params.items():
            if k in ('jsCode','functionCode','credentials'):
                continue
            if typ.endswith('httpRequest') and k not in ('method','url','authentication','options','sendQuery','sendHeaders','sendBody','contentType'):
                continue
            if typ.endswith('scheduleTrigger') and k!='rule':
                continue
            if typ.endswith('webhook') and k not in ('httpMethod','path','responseMode','options'):
                continue
            if len(json.dumps(v,ensure_ascii=False,default=str))>1200:
                continue
            keep[k]=clean(v,k)
        text=json.dumps(keep,ensure_ascii=False,default=str)
        if len(text)>1400:text=text[:1400]+'...'
        print(f"- {n.get('name')} | {typ} | {text}")
print('\n===== PASKUTINIAI VYKDYMAI =====')
cols=[r['name'] for r in rows('pragma table_info(execution_entity)')]
print('COLUMNS='+','.join(cols))
select=[c for c in ('id','workflowId','status','finished','mode','startedAt','stoppedAt') if c in cols]
if 'workflowId' in cols:
    sql='select '+','.join(select)+' from execution_entity order by id desc limit 25'
    for e in rows(sql):
        print(json.dumps(dict(e),ensure_ascii=False,default=str))
print('\n===== SIANDIENOS VYKDYMU SKAICIUS =====')
if 'startedAt' in cols and 'workflowId' in cols:
    for r in rows("select workflowId,status,count(*) as n from execution_entity where startedAt >= '2026-10-25' group by workflowId,status order by workflowId,status"):
        print(json.dumps(dict(r),ensure_ascii=False))
db.close()
