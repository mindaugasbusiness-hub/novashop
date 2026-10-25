#!/usr/bin/env python3
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY = (ROOT / "operator_key").read_text().strip()
BASE = "http://127.0.0.1:8765"


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    run = sub.add_parser("run")
    run.add_argument("--file", required=True)
    run.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps(request("/api/status"), ensure_ascii=False, indent=2))
        return
    command = Path(args.file).read_text(encoding="utf-8")
    job_id = request("/api/enqueue", {"command": command})["id"]
    print("JOB " + job_id, flush=True)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        job = request("/api/job?id=" + job_id)
        if job["status"] == "done":
            print(job["output"], end="")
            print("\nREMOTE_EXIT_CODE=" + str(job["exit_code"]))
            raise SystemExit(job["exit_code"])
        time.sleep(1)
    raise SystemExit("Remote command timed out; job id: " + job_id)


if __name__ == "__main__":
    main()
