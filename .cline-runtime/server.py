#!/usr/bin/env python3
import json
import os
import secrets
import threading
import time
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
AGENT_KEY = os.environ["CLINE_AGENT_KEY"]
OPERATOR_KEY = os.environ["CLINE_OPERATOR_KEY"]
LOCK = threading.Condition()
QUEUE = deque()
JOBS = {}
CLIENT = {"last_seen": None, "name": None}


def authorized(handler, key):
    supplied = handler.headers.get("Authorization", "")
    return secrets.compare_digest(supplied, "Bearer " + key)


class Handler(BaseHTTPRequestHandler):
    server_version = "ClineRelay/1.0"

    def log_message(self, fmt, *args):
        pass

    def send_bytes(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False))

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 8 * 1024 * 1024:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def local_operator(self):
        return self.client_address[0] in ("127.0.0.1", "::1") and authorized(self, OPERATOR_KEY)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_json(200, {"ok": True})
            return
        if parsed.path == "/agent.ps1":
            key = parse_qs(parsed.query).get("key", [""])[0]
            expected_host = urlparse(os.environ["CLINE_PUBLIC_URL"]).netloc
            request_host = self.headers.get("Host", "")
            valid_key = secrets.compare_digest(key, AGENT_KEY)
            valid_shortcut = not key and secrets.compare_digest(request_host, expected_host)
            if not (valid_key or valid_shortcut):
                self.send_json(404, {"error": "Not found"})
                return
            script = (ROOT / "agent-template.ps1").read_text(encoding="utf-8")
            script = script.replace("__SERVER__", os.environ["CLINE_PUBLIC_URL"].rstrip("/"))
            script = script.replace("__KEY__", AGENT_KEY)
            self.send_bytes(200, script, "text/plain; charset=utf-8")
            return
        if parsed.path == "/api/status" and self.local_operator():
            with LOCK:
                self.send_json(200, {"client": CLIENT, "pending": len(QUEUE), "jobs": len(JOBS)})
            return
        if parsed.path == "/api/job" and self.local_operator():
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            with LOCK:
                job = JOBS.get(job_id)
                if job is None:
                    self.send_json(404, {"error": "Unknown job"})
                else:
                    self.send_json(200, job)
            return
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            if parsed.path == "/api/enqueue" and self.local_operator():
                command = data.get("command")
                if not isinstance(command, str) or not command.strip():
                    self.send_json(400, {"error": "command is required"})
                    return
                job = {"id": uuid.uuid4().hex, "command": command, "status": "queued", "created_at": time.time()}
                with LOCK:
                    JOBS[job["id"]] = job
                    QUEUE.append(job["id"])
                    LOCK.notify_all()
                self.send_json(202, {"id": job["id"]})
                return
            if parsed.path == "/api/poll" and authorized(self, AGENT_KEY):
                with LOCK:
                    CLIENT.update(last_seen=time.time(), name=str(data.get("client", "Windows"))[:100])
                    deadline = time.monotonic() + 25
                    while not QUEUE:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        LOCK.wait(remaining)
                    if QUEUE:
                        job = JOBS[QUEUE.popleft()]
                        job["status"] = "running"
                        response = {"id": job["id"], "command": job["command"]}
                    else:
                        response = {"id": None}
                self.send_json(200, response)
                return
            if parsed.path == "/api/result" and authorized(self, AGENT_KEY):
                with LOCK:
                    job = JOBS.get(str(data.get("id", "")))
                    if job is None:
                        self.send_json(404, {"error": "Unknown job"})
                        return
                    job.update(
                        status="done",
                        output=str(data.get("output", "")),
                        exit_code=int(data.get("exit_code", 1)),
                        finished_at=time.time(),
                    )
                self.send_json(200, {"ok": True})
                return
            self.send_json(404, {"error": "Not found"})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    server.serve_forever()
