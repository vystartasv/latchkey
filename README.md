# Latchkey

<!-- REPLACE_ME_DEMO_GIF -->

Credentials for unattended AI agents. Password managers assume a human is present;
Latchkey exists because yours isn't.

---

[![PyPI](https://img.shields.io/pypi/v/latchkey)](https://pypi.org/project/latchkey/)
[![CI](https://github.com/vystartasv/latchkey/actions/workflows/ci.yml/badge.svg)](https://github.com/vystartasv/latchkey/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/vystartasv/latchkey)](LICENSE)

## Install and use

```bash
pip install latchkey
latchkey bootstrap
latchkey serve
# In any agent script:
from latchkey.client import get_credential
gh = get_credential("github.com")
print(gh["password"])
```

## Why this exists

Cron jobs, background tasks, and scheduled agents sometimes need API keys or
passwords. Interactive password managers such as 1Password expect a person to
approve access; Latchkey deliberately does not provide that interaction. Cron
jobs don't have fingers.

Latchkey stores credentials locally and serves them to local processes through
a Unix socket.

## Who it's for / not for

For local, unattended processes that need credentials: scheduled agents, cron
jobs, and background tasks.

Not for interactive-only use, shared or public machines, enterprise compliance
requirements, or password-management workflows. Any process running as your
user can read the socket — that's the design; don't run it on shared machines.

## Security facts

| Property | Detail |
|----------|--------|
| Encryption | Fernet (AES-128-CBC + HMAC-SHA256) at rest |
| Socket | Unix socket chmod 600 — only your user connects |
| Master key | 44 bytes, chmod 600, generated on first init |
| Network | Zero — socket is local only |
| Attestation | No remote attestation, no audit log, no SOC2 |

## CLI reference

```text
latchkey init                          # Generate key + DB
latchkey bootstrap                     # init + import Chrome + verify
latchkey add <service> <user> <pass>   # Store a credential
latchkey get <service>                 # Retrieve (JSON)
latchkey list [--prefix PREFIX]        # List services
latchkey delete <service>              # Delete
latchkey serve                         # Start daemon
latchkey stats                         # Store statistics
latchkey migrate                       # Import from old credential-proxy path
```

## Python API

```python
from latchkey.client import get_credential, list_services, ping
from latchkey.launcher import ensure_daemon

ensure_daemon()                         # Auto-start daemon
gh = get_credential("github.com")       # → {"username": "...", "password": "..."}
svcs = list_services(prefix="git")      # → {"services": [...], "count": 2}
status = ping()                         # → {"status": "ok", "credentials": N}
```

## Optional: Chrome bulk import

Export passwords from Chrome to `Google Passwords.csv`, then import the file:

```bash
latchkey import-chrome path/to.csv
```

## Migration from credential-proxy

If you used the old version:

```bash
latchkey migrate
```

This moves files from `~/.hermes/credential_proxy/` to `~/.latchkey/`.

## License

MIT
