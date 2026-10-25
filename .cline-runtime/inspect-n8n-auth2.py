import sqlite3
from pathlib import Path
p=Path(r'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row
print('COLUMNS', [r['name'] for r in db.execute('pragma table_info(user_api_keys)')])
for r in db.execute('select * from user_api_keys'):
    d=dict(r)
    for key in list(d):
        if 'key' in key.lower() and isinstance(d[key],str) and len(d[key])>24:
            d[key]='[ILGIS='+str(len(d[key]))+']'
    print('APIKEY',d)
for r in db.execute('select id,email,roleSlug,disabled from user'):
    print('USER',dict(r))
db.close()
