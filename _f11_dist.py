import collections
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


cnt = collections.Counter()
for i in range(60):
    d = call()
    cnt[d.get("phrase_id")] += 1
print("60 kvietimu: skirtingu phrase_id =", len(cnt))
for pid, c in cnt.most_common():
    print("  %-10s %d" % (pid, c))
