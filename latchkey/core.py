"""
Latchkey — Encrypted credential store for autonomous agents.

Stores credentials encrypted at rest (Fernet + AES-128). Serves them over
a local Unix socket so agents never need interactive auth.

Chrome CSV import: reads Google Passwords.csv format.
"""

import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet


DEFAULT_DIR = os.path.expanduser("~/.latchkey")
MASTER_KEY_FILE = os.path.join(DEFAULT_DIR, ".master_key")
DB_PATH = os.path.join(DEFAULT_DIR, "credentials.db")
SOCKET_PATH = os.path.join(DEFAULT_DIR, "latchkey.sock")

SCHEMA = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL,
    url TEXT DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    password_encrypted TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_credentials_service ON credentials(service);
"""


class CredentialStore:
    """Encrypted credential storage using SQLite and Fernet.

    Args:
        db_path: Optional path to the SQLite credential database.
        key_path: Optional path to the Fernet master key.
    """

    def __init__(self, db_path: str = None, key_path: str = None):
        self.db_path = db_path or DB_PATH
        self.key_path = key_path or MASTER_KEY_FILE
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._fernet = self._load_or_create_key()
        self._init_db()

    def _load_or_create_key(self) -> Fernet:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                key = f.read()
            return Fernet(key)
        key = Fernet.generate_key()
        with open(self.key_path, "wb") as f:
            f.write(key)
        os.chmod(self.key_path, 0o600)
        return Fernet(key)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add(
        self,
        service: str,
        username: str = "",
        password: str = "",
        url: str = "",
        note: str = "",
    ) -> int:
        """Add a credential or update the existing credential for a service.

        Args:
            service: Unique name for the credential.
            username: Credential username.
            password: Credential password, encrypted before storage.
            url: Optional related login URL.
            note: Optional descriptive note.

        Returns:
            The row ID of the created or updated credential.
        """
        now = self._now()
        encrypted = self._fernet.encrypt(password.encode()).decode()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM credentials WHERE service = ?", (service,)
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE credentials SET username=?, password_encrypted=?,
                       url=?, note=?, updated_at=? WHERE service=?""",
                    (username, encrypted, url, note, now, service),
                )
                conn.commit()
                return existing["id"]
            cursor = conn.execute(
                """INSERT INTO credentials (service, url, username, password_encrypted, note, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (service, url, username, encrypted, note, now, now),
            )
            conn.commit()
            return cursor.lastrowid

    def get(self, service: str) -> Optional[dict]:
        """Retrieve and decrypt a credential.

        Args:
            service: Exact service name to retrieve.

        Returns:
            The decrypted credential dictionary, or None when not found.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM credentials WHERE service = ?", (service,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["password"] = self._fernet.decrypt(d["password_encrypted"].encode()).decode()
        except Exception:
            d["password"] = "[decryption failed]"
        del d["password_encrypted"]
        return d

    def list_services(self, prefix: str = None) -> list[str]:
        """List stored service names in alphabetical order.

        Args:
            prefix: Optional prefix that matching service names must start with.

        Returns:
            A list of matching service names.
        """
        with self._conn() as conn:
            if prefix:
                rows = conn.execute(
                    "SELECT service FROM credentials WHERE service LIKE ? ORDER BY service",
                    (f"{prefix}%",),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT service FROM credentials ORDER BY service"
                ).fetchall()
        return [r["service"] for r in rows]

    def delete(self, service: str) -> bool:
        """Delete a credential by service name.

        Args:
            service: Exact service name to delete.

        Returns:
            True if a credential was deleted; otherwise False.
        """
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM credentials WHERE service = ?", (service,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def import_chrome_csv(self, csv_path: str) -> dict:
        """Import credentials from a Chrome password-export CSV file.

        Args:
            csv_path: Path to a CSV containing Chrome's credential columns.

        Returns:
            A summary with imported, skipped, error, and row-count details.
        """
        if not os.path.exists(csv_path):
            return {"error": f"File not found: {csv_path}", "imported": 0}

        imported = 0
        skipped = 0
        errors = []

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                name = row.get("name", "").strip()
                url = row.get("url", "").strip()
                username = row.get("username", "").strip()
                password = row.get("password", "").strip()
                note = row.get("note", "").strip()

                if not name:
                    skipped += 1
                    continue
                if not password:
                    skipped += 1
                    continue

                try:
                    self.add(
                        service=name,
                        username=username,
                        password=password,
                        url=url,
                        note=note,
                    )
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {i} ({name}): {e}")
                    skipped += 1

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:10],  # Cap error list
            "total_rows": imported + skipped,
        }

    def stats(self) -> dict:
        """Return metadata and credential-count statistics for this store.

        Returns:
            A dictionary describing the store paths, key availability, and count.
        """
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
        return {
            "total_credentials": count,
            "db_path": self.db_path,
            "key_path": self.key_path,
            "has_master_key": os.path.exists(self.key_path),
        }
