# Latchkey

Encrypted credential store that serves secrets to autonomous AI agents over a
local Unix socket. Agents get passwords and API tokens without interactive auth —
solving the "your password manager wants a fingerprint but cron jobs don't have
fingers" problem.

---

## Summary

AI agents running on schedules (cron jobs, background tasks) often need passwords,
API keys, or access tokens to do their work — publish a blog post, push to GitHub,
send an email. But password managers and keychains require interactive
authentication: a fingerprint, a master password, a hardware key tap. Scheduled
agents can't provide that.

Credentials for unattended AI agents. Password managers assume a human is present; Latchkey exists because yours isn't.

Latchkey decrypts your credentials once when your machine boots, then
holds them in memory behind a local Unix socket. Agents connect through that
socket to retrieve credentials on demand — no Touch ID, no popups, no human in
the loop.

Everything stays on your machine. Nothing touches the network. Only your user
account can read the socket.

---

## Who it's for

- Anyone running **scheduled AI agents** that need API keys, tokens, or
  passwords to do their work
- **CI-like pipelines on a local machine** where interactive auth is impossible
- **Multi-agent fleets** that all need access to the same set of credentials
- **macOS users** stuck behind Touch ID / Keychain prompts in cron contexts

## Who it's NOT for

- **Interactive-only use** — if you're always at the keyboard when credentials
  are needed, use your normal password manager
- **Public cloud or shared servers** — this is a single-user, local-machine
  tool. Anyone with access to the socket has access to your credentials
- **High-security enterprise** — secrets are decrypted at boot and held in
  memory for the session. It's safe for personal use but not SOC2-compliant
- **Password management** — this is a proxy, not a password manager. Credentials
  are imported from Chrome or added manually

---

## Install

```bash
pip install -e .
```

## Bootstrap

```bash
latchkey bootstrap                          # Init + import Chrome + verify
latchkey import-chrome ~/Downloads/Google\ Passwords.csv
latchkey add myservice user password --url https://example.com
latchkey serve                              # Start daemon
```

## Client (from agent scripts)

```python
from latchkey.client import get_credential
from latchkey.launcher import ensure_daemon

ensure_daemon()
gh = get_credential("github.com")
# → {"username": "vystartasv", "password": "***", "url": "https://github.com"}
```

## Security

- **Fernet encryption** (AES-128-CBC + HMAC-SHA256) at rest
- **Unix socket chmod 600** — only the owning user can connect
- **Master key chmod 600** — 44 bytes, generated on first init
- **All DB files chmod 600**
- **Chrome CSV auto-deleted** after import
- **No network exposure** — socket is local only

## License

MIT
