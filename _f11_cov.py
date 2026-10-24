import json
import re
import subprocess
import urllib.request

BASE = "http://127.0.0.1:8000"
env = subprocess.run(["systemctl", "show", "aukcionas.service", "-p", "Environment"],
                     capture_output=True, text=True).stdout
pw = re.search(r"AUKCIONAS_ADMIN_SLAPTAZODIS=(\S+)", env).group(1)


def call():
    req = urllib.request.Request(BASE + "/api/admin/vilkas_phone",
                                 data=json.dumps({"password": pw}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


seen_t, seen_p = set(), set()
cons = 0
prev = None
for i in range(120):
    d = call()
    t = d.get("text")
    seen_t.add(t)
    seen_p.add(str(d.get("phrase_id")))
    if t == prev:
        cons += 1
    prev = t
print("120 kvietimu: SKIRTINGU tekstu =", len(seen_t), "| SKIRTINGU phrase_id =", len(seen_p),
      "| PASIKARTOJIMU is eiles =", cons)
