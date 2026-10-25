import json, sqlite3
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row

def rows(sql):
    try:return db.execute(sql).fetchall()
    except Exception as e:return [{'error':str(e)}]
print('TABLES', [r['name'] for r in rows("select name from sqlite_master where type='table' and (name like '%api%' or name like '%user%')")])
for table in ('api_key','user'):
    print(table, 'columns', [r['name'] for r in rows(f'pragma table_info({table})')])
if rows("select name from sqlite_master where type='table' and name='api_key'"):
    print('API_KEY_COUNT', rows('select count(*) as n from api_key')[0]['n'])
    for r in rows('select id,userId,label,length(apiKey) as key_len,substr(apiKey,1,18) as prefix,createdAt from api_key'):
        print(dict(r))
if rows("select name from sqlite_master where type='table' and name='user'"):
    for r in rows('select id,email,role,createdAt from user'):
        print('USER',dict(r))
db.close()
