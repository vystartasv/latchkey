"""
Latchkey client — importable library for agent scripts.

Usage:
    from latchkey.client import get_credential, list_services
    gh = get_credential("github.com")
    print(gh["username"], gh["password"])
"""

import json
import os
import socket

from .core import SOCKET_PATH


def _call(action: str, **kwargs) -> dict:
    """Send a request to the Latchkey daemon."""
    request = json.dumps({"action": action, **kwargs}) + "\n"

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect(SOCKET_PATH)
        sock.sendall(request.encode())
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        return json.loads(data.decode().strip())
    except (socket.timeout, ConnectionRefusedError, FileNotFoundError) as e:
        return {"error": f"daemon unavailable: {e}"}
    finally:
        sock.close()


def get_credential(service: str) -> dict:
    """Get a decrypted credential by service name."""
    return _call("get", service=service)


def list_services(prefix: str = None) -> dict:
    """List all stored service names."""
    kwargs = {}
    if prefix:
        kwargs["prefix"] = prefix
    return _call("list", **kwargs)


def ping() -> dict:
    """Check if the daemon is running."""
    return _call("ping")
