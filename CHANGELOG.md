# Changelog

All notable changes to Credential Proxy are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-04

### Added
- Fernet-encrypted SQLite credential store
- Unix socket server with SIGTERM handling and 30s idle timeout
- Client library: `get_credential(domain)` lookup
- Chrome CSV import with deduplication (424 → 353 unique credentials)
- Bootstrap wizard: key generation, import, verification
- Auto-deletion of Chrome CSV after import
- launchd plist for auto-start on macOS boot
- launcher module: `ensure_daemon()` auto-starts the proxy
- File permissions enforcement: `.db`, `.master_key`, socket all `chmod 600`
- 24 tests with 100% pass rate
