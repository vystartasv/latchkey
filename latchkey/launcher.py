#!/usr/bin/env python3.11
"""
Latchkey launcher — auto-starts daemon if not running.
Import this from pre-cron scripts or agent code.

Usage:
    from latchkey.launcher import ensure_daemon
    ensure_daemon()
"""

import os
import socket
import subprocess
import sys
import time

SOCKET_PATH = os.path.expanduser("~/.latchkey/latchkey.sock")
HERMES_DIR = os.path.expanduser("~/.hermes")


def is_daemon_running() -> bool:
    """Check whether the Latchkey daemon is accepting requests.

    Returns:
        True when the daemon responds through its Unix socket; otherwise False.
    """
    if not os.path.exists(SOCKET_PATH):
        return False
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(SOCKET_PATH)
        sock.sendall(b'{"action":"ping"}\n')
        sock.recv(4096)
        sock.close()
        return True
    except Exception:
        return False


def ensure_daemon() -> bool:
    """Start the daemon when needed and wait for its socket.

    Returns:
        True if the daemon is running or its socket appears after startup;
        otherwise False.
    """
    if is_daemon_running():
        return True

    try:
        env = os.environ.copy()
        # Ensure ~/.hermes is on PYTHONPATH so latchkey.daemon is importable
        existing_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{HERMES_DIR}:{existing_path}" if existing_path else HERMES_DIR

        subprocess.Popen(
            [sys.executable, "-m", "latchkey.daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=HERMES_DIR,
            env=env,
        )
        # Wait for socket to appear
        for _ in range(30):
            if os.path.exists(SOCKET_PATH):
                return True
            time.sleep(0.1)
        return False
    except Exception:
        return False


if __name__ == "__main__":
    if ensure_daemon():
        print("✓ Latchkey daemon running")
    else:
        print("✗ Failed to start daemon")
        sys.exit(1)
