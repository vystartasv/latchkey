"""
Latchkey — Encrypted credential store for autonomous agents.

Solves the 1Password dead-end: agents call a local Unix socket daemon
instead of needing interactive Touch ID auth.

Usage:
    # CLI
    latchkey import-chrome ~/Downloads/Google\\ Passwords.csv
    latchkey add github.com myuser mytoken
    latchkey get github.com
    latchkey serve  # Start daemon

    # Client library (from agent scripts)
    from latchkey.client import get_credential
    gh = get_credential("github.com")
"""

from .core import CredentialStore

__all__ = ["CredentialStore"]
