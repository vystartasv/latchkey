"""
Tests for Latchkey — encrypted credential store.

Run: python3 -m pytest latchkey/tests/ -v
"""

import os
import sqlite3
import tempfile

import pytest

from latchkey.core import CredentialStore
from latchkey.daemon import handle_request
from latchkey import cli


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def store():
    """Create a temporary credential store."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_creds.db")
        key_path = os.path.join(tmp, "test.key")
        store = CredentialStore(db_path=db_path, key_path=key_path)
        yield store


# ── Core Store Tests ──────────────────────────────────────────────────────

class TestKeyManagement:
    def test_key_generation(self, store):
        """Master key is generated on first init."""
        assert os.path.exists(store.key_path)
        assert os.path.getsize(store.key_path) == 44  # Fernet key is 44 bytes base64

    def test_key_persistence(self, store):
        """Reopening with same key path reuses the key."""
        store.add("test", "user", "pass123")
        # Reopen
        s2 = CredentialStore(db_path=store.db_path, key_path=store.key_path)
        result = s2.get("test")
        assert result["password"] == "pass123"

    def test_key_permissions(self, store):
        """Master key file is readable only by owner."""
        mode = os.stat(store.key_path).st_mode
        assert mode & 0o077 == 0  # No group/other permissions


class TestAddGet:
    def test_add_and_get(self, store):
        store.add("github.com", "vystartasv", "ghp_test_token")
        result = store.get("github.com")
        assert result["username"] == "vystartasv"
        assert result["password"] == "ghp_test_token"

    def test_add_with_url_and_note(self, store):
        store.add("example.com", "admin", "secret", url="https://example.com/login", note="GoDaddy")
        result = store.get("example.com")
        assert result["url"] == "https://example.com/login"
        assert result["note"] == "GoDaddy"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_update_existing(self, store):
        store.add("github.com", "old", "oldpass")
        store.add("github.com", "new_user", "newpass")
        result = store.get("github.com")
        assert result["username"] == "new_user"
        assert result["password"] == "newpass"

    def test_encryption_at_rest(self, store):
        """Raw DB never contains plaintext password."""
        store.add("github.com", "user", "supersecret")
        conn = sqlite3.connect(store.db_path)
        row = conn.execute(
            "SELECT password_encrypted FROM credentials WHERE service='github.com'"
        ).fetchone()
        conn.close()
        assert "supersecret" not in row[0]
        assert row[0].startswith("gAAAAA")  # Fernet prefix


class TestList:
    def test_list_all(self, store):
        store.add("a.com", "u", "p")
        store.add("b.com", "u", "p")
        store.add("c.com", "u", "p")
        services = store.list_services()
        assert len(services) == 3
        assert services == ["a.com", "b.com", "c.com"]

    def test_list_prefix(self, store):
        store.add("github.com", "u", "p")
        store.add("gitlab.com", "u", "p")
        store.add("ghost.org", "u", "p")
        assert store.list_services(prefix="git") == ["github.com", "gitlab.com"]


class TestDelete:
    def test_delete(self, store):
        store.add("test", "u", "p")
        assert store.delete("test") is True
        assert store.get("test") is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False


# ── Chrome Import Tests ───────────────────────────────────────────────────

class TestChromeImport:
    def test_import_csv(self, store):
        csv_content = "name,url,username,password,note\n"
        csv_content += "github.com,https://github.com,user1,pass1,\n"
        csv_content += "dev.to,https://dev.to,user2,pass2,API key\n"
        csv_content += "blank.com,,,,\n"  # Should be skipped (no name, no pass)
        csv_content += "nopass.com,https://nopass.com,user3,,\n"  # Skipped (no password)

        csv_path = os.path.join(os.path.dirname(store.db_path), "test.csv")
        with open(csv_path, "w") as f:
            f.write(csv_content)

        result = store.import_chrome_csv(csv_path)
        assert result["imported"] == 2
        assert result["skipped"] == 2

        # Verify imported credentials work
        gh = store.get("github.com")
        assert gh["username"] == "user1"
        assert gh["password"] == "pass1"
        assert gh["url"] == "https://github.com"

        dev = store.get("dev.to")
        assert dev["password"] == "pass2"
        assert dev["note"] == "API key"

    def test_import_nonexistent_file(self, store):
        result = store.import_chrome_csv("/nonexistent/file.csv")
        assert "error" in result
        assert result["imported"] == 0


# ── Daemon Protocol Tests ─────────────────────────────────────────────────

class TestDaemonProtocol:
    def test_ping(self, store):
        response = handle_request(store, {"action": "ping"})
        assert response["status"] == "ok"

    def test_get_credential(self, store):
        store.add("github.com", "user", "token123")
        response = handle_request(store, {"action": "get", "service": "github.com"})
        assert response["username"] == "user"
        assert response["password"] == "token123"

    def test_get_not_found(self, store):
        response = handle_request(store, {"action": "get", "service": "nonexistent"})
        assert response["error"] == "not_found"

    def test_list_services(self, store):
        store.add("a.com", "u", "p")
        store.add("b.com", "u", "p")
        response = handle_request(store, {"action": "list"})
        assert response["count"] == 2
        assert response["services"] == ["a.com", "b.com"]

    def test_list_with_prefix(self, store):
        store.add("github.com", "u", "p")
        store.add("gitlab.com", "u", "p")
        store.add("google.com", "u", "p")
        response = handle_request(store, {"action": "list", "prefix": "git"})
        assert response["count"] == 2

    def test_unknown_action(self, store):
        response = handle_request(store, {"action": "destroy_everything"})
        assert "error" in response
        assert "unknown" in response["error"].lower()


# ── Stats Tests ───────────────────────────────────────────────────────────

class TestStats:
    def test_empty_stats(self, store):
        s = store.stats()
        assert s["total_credentials"] == 0
        assert s["has_master_key"] is True

    def test_populated_stats(self, store):
        for i in range(5):
            store.add(f"site{i}.com", "user", "pass")
        assert store.stats()["total_credentials"] == 5


# ── Legacy Migration Tests ───────────────────────────────────────────────

class TestLegacyMigration:
    def test_migrate_legacy_store_moves_files(self, tmp_path, monkeypatch):
        legacy_dir = tmp_path / "legacy"
        new_dir = tmp_path / "latchkey"
        legacy_dir.mkdir()
        for filename in (".master_key", "credentials.db"):
            (legacy_dir / filename).write_text(filename)

        monkeypatch.setattr(cli, "LEGACY_DIR", str(legacy_dir))
        monkeypatch.setattr(cli, "LEGACY_SOCKET_PATH", str(legacy_dir / "proxy.sock"))
        monkeypatch.setattr(cli, "DEFAULT_DIR", str(new_dir))

        moved = cli.migrate_legacy_store()

        assert len(moved) == 2
        assert (new_dir / ".master_key").read_text() == ".master_key"
        assert (new_dir / "credentials.db").read_text() == "credentials.db"
        assert not (legacy_dir / ".master_key").exists()
        assert not (legacy_dir / "credentials.db").exists()

    def test_migrate_legacy_store_without_legacy_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "LEGACY_DIR", str(tmp_path / "missing"))

        assert cli.migrate_legacy_store() == []


# ── Concurrency Tests ─────────────────────────────────────────────────────

class TestConcurrency:
    def test_multiple_readers(self, store):
        """SQLite WAL allows concurrent readers."""
        store.add("shared.com", "user", "pass")

        # Simulate two readers (two connections)
        conn1 = sqlite3.connect(store.db_path)
        conn2 = sqlite3.connect(store.db_path)

        r1 = conn1.execute("SELECT * FROM credentials WHERE service='shared.com'").fetchone()
        r2 = conn2.execute("SELECT * FROM credentials WHERE service='shared.com'").fetchone()

        assert r1[1] == "shared.com"
        assert r2[1] == "shared.com"

        conn1.close()
        conn2.close()

    def test_wal_mode_enabled(self, store):
        conn = sqlite3.connect(store.db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode.lower() == "wal"
