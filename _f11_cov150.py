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


seen = set()
prev = None
cons = 0
N = 150
for i in range(N):
    d = call()
    pid = d.get("phrase_id")
    seen.add(str(pid))
    if d.get("text") == prev:
        cons += 1
    prev = d.get("text")
print("%d kvietimu: SKIRTINGU phrase_id = %d | PASIKARTOJIMU is eiles = %d" % (N, len(seen), cons))
print("panaudoti id:", ", ".join(sorted(seen)))
