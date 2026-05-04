# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue.

Email the maintainer directly at vilius.vystartas@gmail.com.

You should receive a response within 48 hours. If the issue is confirmed,
we'll release a fix as soon as possible — typically within 72 hours.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model

Credential Proxy is a **local-only** tool designed for single-user machines.
It does not expose anything to the network.

- **Encryption at rest**: Fernet (AES-128-CBC + HMAC-SHA256)
- **Master key**: 44 bytes, `chmod 600`, generated on first init
- **Socket**: Unix domain socket, `chmod 600` — only the owning user can connect
- **Database**: SQLite with `chmod 600` on the file
- **No network exposure**: The server binds to a Unix socket, not TCP
- **Chrome CSV**: Auto-deleted after import
- **No telemetry, no phoning home**

## Threat Model

Credential Proxy assumes your local machine and user account are trusted.
It does not protect against:

- Malware running as your user (can read the socket)
- Physical access to your unlocked machine
- Memory inspection of the running daemon

If you need defense against these threats, use a hardware token or a
networked secrets manager with per-request auth.
