"""
Latchkey daemon — Unix socket server.

Listens on ~/.latchkey/latchkey.sock.
Protocol: JSON request → JSON response, one per line.

Actions:
  {"action": "get", "service": "github.com"}
  {"action": "list", "prefix": "git"}
  {"action": "ping"}
"""

import json
import os
import signal
import socket
import sys

from .core import CredentialStore, SOCKET_PATH


def handle_request(store: CredentialStore, data: dict) -> dict:
    action = data.get("action", "")

    if action == "ping":
        return {"status": "ok", "credentials": store.stats()["total_credentials"]}

    elif action == "get":
        service = data.get("service", "")
        if not service:
            return {"error": "service required"}
        result = store.get(service)
        if result:
            return result
        return {"error": "not_found", "service": service}

    elif action == "list":
        prefix = data.get("prefix")
        services = store.list_services(prefix=prefix)
        return {"services": services, "count": len(services)}

    else:
        return {"error": f"unknown action: {action}"}


def run_daemon():
    store = CredentialStore()

    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(5)

    # Clean shutdown on SIGTERM (launchd)
    def shutdown(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, shutdown)

    print(f"Latchkey listening on {SOCKET_PATH}", file=sys.stderr)

    try:
        while True:
            conn, _ = server.accept()
            conn.settimeout(10)  # Prevent hung connections from blocking daemon
            try:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break

                if data:
                    text = data.decode().strip()
                    request = json.loads(text)
                    response = handle_request(store, request)
                    conn.sendall((json.dumps(response) + "\n").encode())
            except json.JSONDecodeError:
                conn.sendall(json.dumps({"error": "invalid json"}) + "\n".encode())
            except Exception as e:
                conn.sendall(json.dumps({"error": str(e)}) + "\n".encode())
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
    finally:
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)


if __name__ == "__main__":
    run_daemon()
