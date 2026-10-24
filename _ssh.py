import sys, paramiko

HOST = "5.175.171.113"
USER = "root"
PWD = "zyiiQkHpo6fSuNFBcQ01"


def client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PWD, timeout=30, banner_timeout=30, auth_timeout=30)
    return c


def run(cmd, timeout=300):
    c = client()
    try:
        stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=False)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err
    finally:
        c.close()


def put(local, remote, mode=None):
    c = client()
    try:
        sftp = c.open_sftp()
        sftp.put(local, remote)
        if mode:
            sftp.chmod(remote, mode)
        sftp.close()
    finally:
        c.close()


def get(remote, local):
    c = client()
    try:
        sftp = c.open_sftp()
        sftp.get(remote, local)
        sftp.close()
    finally:
        c.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "hostname"
    rc, out, err = run(cmd)
    print("RC:", rc)
    if out:
        print(out)
    if err:
        print("STDERR:", err)
