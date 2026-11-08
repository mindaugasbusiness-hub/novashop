# -*- coding: utf-8 -*-
"""K2: perraso naudojimas() JS funkcija svarei (be escape problemu)."""
import io
import shutil
import sys

AS = r"C:\Users\viliu\CLINE\ai-stack\agent_server.py"
with io.open(AS, "r", encoding="utf-8") as f:
    a = f.read()

start = a.find("function naudojimas(){")
end = a.find('window.addEventListener("load"', start)
if start < 0 or end < 0:
    sys.exit("nerasti funkcijos ribos")

NAUJA = '''function naudojimas(){
  fetch('/usage').then(function(r){return r.json()}).then(function(u){
    var ms = ['openai/gpt-oss-120b','qwen/qwen3.8-27b','openai/gpt-oss-20b','allam-2-7b','openai/gpt-oss-safeguard-20b'];
    var eil = '';
    for (var i=0;i<ms.length;i++){
      var m = ms[i];
      var d = u[m] || {};
      var rp = (d.req_limit>0) ? Math.round(100*(d.req_limit-d.req_left)/d.req_limit) : -1;
      var tp = (d.tok_limit>0) ? Math.round(100*(d.tok_limit-d.tok_left)/d.tok_limit) : -1;
      var spalva = (rp>80) ? '#e06c6c' : (rp>50 ? '#d8a657' : '#7ec699');
      var rtekst = (rp<0) ? '-' : (rp + '% (' + (d.req_limit-d.req_left) + '/' + d.req_limit + ')');
      var ttekst = (tp<0) ? '-' : (tp + '%');
      eil += (VARD[m]||m) + ': uzklausos <b style="color:' + spalva + '">' + rtekst +
             '</b> / zetonai/min ' + ttekst + '<br>';
    }
    document.getElementById('usage').innerHTML = '<b>Kvotos isnaudojimas siandien:</b><br>' + eil;
  }).catch(function(){});
}
'''

a = a[:start] + NAUJA + a[end:]
shutil.copy2(AS, AS + ".bak-2026-11-08-js2")
with io.open(AS, "w", encoding="utf-8", newline="") as f:
    f.write(a)

import py_compile
try:
    py_compile.compile(AS, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(AS + ".bak-2026-11-08-js2", AS)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: naudojimas() perrasyta")
