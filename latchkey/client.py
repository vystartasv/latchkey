"""
Latchkey client — importable library for agent scripts.

Usage:
    from latchkey.client import get_credential, list_services
    gh = get_credential("github.com")
    print(gh["username"], gh["password"])
"""

import json
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
    """Get a decrypted credential by service name.

    Args:
        service: Exact service name used when the credential was stored.

    Returns:
        The daemon response containing the decrypted credential, or an error.
    """
    return _call("get", service=service)


def list_services(prefix: str = None) -> dict:
    """List stored service names, optionally filtered by a prefix.

    Args:
        prefix: Optional prefix that matching service names must start with.

    Returns:
        The daemon response containing matching service names, or an error.
    """
    kwargs = {}
    if prefix:
        kwargs["prefix"] = prefix
    return _call("list", **kwargs)


def ping() -> dict:
    """Check whether the daemon is responding.

    Returns:
        The daemon ping response, or an error if it is unavailable.
    """
    return _call("ping")
