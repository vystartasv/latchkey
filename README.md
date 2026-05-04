# Credential Proxy

Encrypted credential store for autonomous AI agents. Fernet-encrypted SQLite
with a Unix socket daemon — agents get secrets without interactive auth.

Solves the 1Password Touch ID deadlock for cron jobs.

---

### 🧸 If you're 5:

Your robots need passwords to do their jobs — like a key to open a door.
But the password-keeper (1Password) wants a fingerprint, and robots don't have fingers.

Credential Proxy is like a trusted friend who:
- 🔐 **Holds all the keys** in a locked box that only they can open
- 🏠 **Lives in your house** (not on the internet — nobody outside can reach them)
- 🤫 **Whispers passwords** to your robots through a special tube (a Unix socket)
- 🧹 **Cleaned up** after borrowing your Chrome passwords (imported them, then deleted the file)

Now your robots can open doors without needing fingers.

---

## Install

```bash
pip install -e .
```

## Bootstrap

```bash
credential-proxy bootstrap                          # Init + import Chrome + verify
credential-proxy import-chrome ~/Downloads/Google\ Passwords.csv
credential-proxy add myservice user password --url https://example.com
credential-proxy serve                              # Start daemon
```

## Client (from agent scripts)

```python
from credential_proxy.client import get_credential
from credential_proxy.launcher import ensure_daemon

ensure_daemon()
gh = get_credential("github.com")
# → {"username": "vystartasv", "password": "ghp_...", "url": "https://github.com"}
```

## Security

- Fernet (AES-128-CBC + HMAC-SHA256) encryption at rest
- Unix socket chmod 600 — only the owning user can connect
- Master key chmod 600 — 44 bytes, generated on first init
- All DB files chmod 600
- Chrome CSV auto-deleted after import

## License

MIT
