#!/usr/bin/env python3.11
"""
Latchkey — Encrypted credential store for autonomous agents.

Usage:
    latchkey init
    latchkey import-chrome [CSV_PATH]
    latchkey add <service> <username> <password> [--url URL] [--note NOTE]
    latchkey get <service>
    latchkey list [--prefix PREFIX]
    latchkey delete <service>
    latchkey serve
    latchkey stats
    latchkey migrate
"""

import argparse
import json
import os
import shutil
import sys

from latchkey.core import CredentialStore, DEFAULT_DIR
from latchkey.daemon import run_daemon


LEGACY_DIR = os.path.join(os.path.expanduser("~/.hermes"), "credential" + "_proxy")
LEGACY_SOCKET_PATH = os.path.join(LEGACY_DIR, "proxy.sock")


def migrate_legacy_store() -> list[str]:
    """Move the legacy store into Latchkey's data directory."""
    if not os.path.isdir(LEGACY_DIR):
        return []

    os.makedirs(DEFAULT_DIR, exist_ok=True)
    moved = []
    for filename in (".master_key", "credentials.db", "proxy.sock"):
        source = os.path.join(LEGACY_DIR, filename)
        if not os.path.exists(source):
            continue
        destination = os.path.join(
            DEFAULT_DIR, "latchkey.sock" if filename == "proxy.sock" else filename
        )
        shutil.move(source, destination)
        os.chmod(destination, 0o600)
        moved.append(f"{source} → {destination}")

    if os.path.lexists(LEGACY_SOCKET_PATH):
        os.unlink(LEGACY_SOCKET_PATH)
    os.symlink(os.path.join(DEFAULT_DIR, "latchkey.sock"), LEGACY_SOCKET_PATH)
    return moved


def main():
    parser = argparse.ArgumentParser(
        prog="latchkey",
        description="Encrypted credential store for autonomous agents",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize master key and database")

    bootstrap_p = subparsers.add_parser("bootstrap", help="Full setup: init + import Chrome + verify")
    bootstrap_p.add_argument(
        "--csv", default=None,
        help="Path to Chrome CSV (default: auto-detect in ~/Downloads)"
    )

    verify_p = subparsers.add_parser("verify", help="Verify encryption: spot-check decrypted credentials")

    import_p = subparsers.add_parser("import-chrome", help="Import Google Chrome password CSV")
    import_p.add_argument(
        "csv_path", nargs="?", default=None,
        help="Path to CSV (default: ~/Downloads/Google Passwords.csv)"
    )

    add_p = subparsers.add_parser("add", help="Add a credential")
    add_p.add_argument("service")
    add_p.add_argument("username")
    add_p.add_argument("password")
    add_p.add_argument("--url", default="")
    add_p.add_argument("--note", default="")

    get_p = subparsers.add_parser("get", help="Retrieve a credential")
    get_p.add_argument("service")

    list_p = subparsers.add_parser("list", help="List stored services")
    list_p.add_argument("--prefix")

    delete_p = subparsers.add_parser("delete", help="Delete a credential")
    delete_p.add_argument("service")

    subparsers.add_parser("serve", help="Start Unix socket daemon")
    subparsers.add_parser("stats", help="Show store statistics")
    subparsers.add_parser("migrate", help="Migrate a legacy store")

    args = parser.parse_args()

    if args.command == "init":
        store = CredentialStore()
        print(f"✓ Latchkey initialized")
        print(f"  Master key: {store.key_path}")
        print(f"  Database:   {store.db_path}")
        print(f"  Next: latchkey import-chrome ~/Downloads/Google\\ Passwords.csv")
        return

    if args.command == "bootstrap":
        store = CredentialStore()
        print(f"✓ Store initialized ({store.key_path})")

        # Auto-detect Chrome CSV
        csv_path = args.csv
        if not csv_path:
            candidates = [
                os.path.expanduser("~/Downloads/Google Passwords.csv"),
                os.path.expanduser("~/Downloads/Chrome Passwords.csv"),
                os.path.expanduser("~/Downloads/google-passwords.csv"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    csv_path = c
                    break
            if not csv_path:
                print("✗ No Chrome CSV found. Usage: latchkey bootstrap --csv <path>")
                sys.exit(1)

        print(f"\nImporting: {csv_path}")
        result = store.import_chrome_csv(csv_path)
        print(f"  Imported: {result['imported']}")
        print(f"  Skipped:  {result['skipped']}")

        if result["errors"]:
            for e in result["errors"][:3]:
                print(f"  ⚠  {e}")

        # Verify spot-check
        services = store.list_services()
        if services:
            sample = services[:min(3, len(services))]
            print(f"\n  Spot-check (first 3 of {len(services)}):")
            for svc in sample:
                cred = store.get(svc)
                status = "✓" if cred and cred["password"] else "✗"
                url_hint = f" ({cred['url'][:40]})" if cred.get("url") else ""
                print(f"  {status} {svc}{url_hint}")

        print(f"\n✓ Bootstrap complete. {result['imported']} credentials ready.")
        print(f"  Start daemon: latchkey serve")
        print(f"  Use in scripts: from latchkey.client import get_credential")
        return

    if args.command == "verify":
        store = CredentialStore()
        services = store.list_services()
        if not services:
            print("No credentials stored.")
            return

        good = 0
        bad = 0
        sample = services[:min(10, len(services))]
        for svc in sample:
            cred = store.get(svc)
            if cred and cred["password"]:
                good += 1
            else:
                bad += 1
                print(f"  ✗ {svc}: decryption failed")

        total = store.stats()["total_credentials"]
        if bad == 0:
            print(f"✓ All {total} credentials verified ({good} spot-checked)")
        else:
            print(f"⚠  {bad}/{total} credentials failed decryption")
            sys.exit(1)
        return

    if args.command == "serve":
        run_daemon()
        return

    if args.command == "migrate":
        legacy_exists = os.path.isdir(LEGACY_DIR)
        moved = migrate_legacy_store()
        if moved:
            print("✓ Migrated legacy store files:")
            for path in moved:
                print(f"  {path}")
            print(f"  {LEGACY_SOCKET_PATH} → {os.path.join(DEFAULT_DIR, 'latchkey.sock')}")
        elif legacy_exists:
            print("Legacy store had no migratable files; compatibility socket symlink created.")
        else:
            print("No legacy store directory found; nothing to migrate.")
        return

    store = CredentialStore()

    if args.command == "import-chrome":
        csv_path = args.csv_path or os.path.expanduser("~/Downloads/Google Passwords.csv")
        print(f"Importing from: {csv_path}")
        result = store.import_chrome_csv(csv_path)
        print(json.dumps(result, indent=2))

    elif args.command == "add":
        store.add(
            service=args.service,
            username=args.username,
            password=args.password,
            url=args.url,
            note=args.note,
        )
        print(f"✓ Credential stored: {args.service}")

    elif args.command == "get":
        result = store.get(args.service)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"✗ Not found: {args.service}")
            sys.exit(1)

    elif args.command == "list":
        services = store.list_services(prefix=args.prefix)
        for s in services:
            print(f"  • {s}")
        print(f"\n{len(services)} credentials")

    elif args.command == "delete":
        ok = store.delete(args.service)
        print(f"{'✓ Deleted' if ok else '✗ Not found'}: {args.service}")

    elif args.command == "stats":
        print(json.dumps(store.stats(), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
