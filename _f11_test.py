import json
import re
import subprocess
import time
import urllib.request

BASE = "http://127.0.0.1:8000"
env = subprocess.run(["systemctl", "show", "aukcionas.service", "-p", "Environment"],
                     capture_output=True, text=True).stdout
m = re.search(r"AUKCIONAS_ADMIN_SLAPTAZODIS=(\S+)", env)
pw = m.group(1) if m else ""
print("slaptazodzio ilgis:", len(pw))


def call(payload):
    req = urllib.request.Request(BASE + "/api/admin/vilkas_phone",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


print("=== C) 12 kvietimu be n (F11 paspaudimas) ===")
texts, ns, pids, srcs = [], [], [], []
for i in range(12):
    d = call({"password": pw})
    texts.append(d.get("text"))
    ns.append(d.get("n"))
    pids.append(d.get("phrase_id"))
    srcs.append(d.get("source"))
    print("%2d. n=%s src=%s cc=%s pid=%s | %s"
          % (i + 1, d.get("n"), d.get("source"), d.get("core_count"),
             d.get("phrase_id"), str(d.get("text"))[:72]))
    time.sleep(0.2)

print("SKIRTINGU tekstu: %d/12" % len(set(texts)))
print("SKIRTINGU phrase_id: %d/12" % len(set(str(x) for x in pids)))
print("PASIKARTOJIMU is eiles: %d" % sum(1 for i in range(1, len(texts)) if texts[i] == texts[i - 1]))
print("source reiksmes:", sorted(set(srcs)))
print("PIRMI 5 tekstai:")
for t in texts[:5]:
    print("  -", t)

print()
print("=== D) rankinis n ===")
for k in (5, 1, 12, 7):
    d = call({"password": pw, "n": k})
    print("n=%s -> n=%s src=%s | %s" % (k, d.get("n"), d.get("source"), str(d.get("text"))[:72]))

print()
print("=== D2) ar grazintas n=5 sutampa su 5-u VILKAS8_PHONE elementu ===")
d = call({"password": pw, "n": 5})
print("n=5 text:", d.get("text"))

print()
print("=== B) 40 kvietimu — kiek skirtingu (rodo, kad naudojamos visos smegenu frazes) ===")
t40 = []
for i in range(40):
    d = call({"password": pw})
    t40.append(d.get("text"))
    time.sleep(0.05)
print("SKIRTINGU tekstu per 40: %d" % len(set(t40)))
