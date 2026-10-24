import json
import urllib.request

for url in ("http://127.0.0.1:8000/api/state", "http://127.0.0.1:8000/api/vilkas/state"):
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.loads(r.read().decode())
        keys = [k for k in d.keys() if "stage" in k or "lock" in k or "practice" in k or "live" in k]
        print(url, "->", {k: d[k] for k in keys})
    except Exception as e:
        print(url, "->", type(e).__name__, e)
