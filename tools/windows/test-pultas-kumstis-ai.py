import sys
import json

d = sys.argv[1]
sys.path.insert(0, d)
import pultas  # noqa: E402

print('HTML turi id="sSYS"     :', 'id="sSYS"' in pultas.HTML_PAGE)
print('HTML turi KUMSTIS AI    :', 'KUMSTIS AI' in pultas.HTML_PAGE)
print('JS funkcija rSYS        :', 'function rSYS(d)' in pultas.HTML_PAGE)
print('load() kviecia rSYS     :', 'rSYS(d);' in pultas.HTML_PAGE)
print('collect_status turi rakta:', 'kumstis_ai' in open(pultas.__file__, encoding='utf-8').read())
print('--- collect_kumstis_ai() ---')
print(json.dumps(pultas.collect_kumstis_ai(), ensure_ascii=False, indent=1))
