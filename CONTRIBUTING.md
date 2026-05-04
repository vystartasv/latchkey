# Contributing to Credential Proxy

Thanks for contributing. Here's how to get started.

## Dev Environment

```bash
git clone https://github.com/vystartasv/credential-proxy.git
cd credential-proxy
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before You Start

- Open an issue first for features or large changes — saves you wasting time
  if it doesn't fit the roadmap
- Bug fixes can go straight to PR
- **Security-sensitive changes**: if your change touches encryption, key
  handling, or socket permissions, tag it in the PR description

## Branch Naming

```
feat/short-description    # New features
fix/short-description     # Bug fixes
docs/short-description    # Documentation only
chore/short-description   # Tooling, CI, dependencies
```

## Pull Request Checklist

- [ ] Tests pass: `pytest`
- [ ] New code has tests
- [ ] Lint passes: `ruff check .`
- [ ] README updated if needed
- [ ] CHANGELOG entry added under `[Unreleased]`
- [ ] No credentials or keys committed (check `.gitignore`)

## Code Style

- Python 3.11+
- Ruff for linting and formatting
- Type hints on all public functions
- Docstrings for public APIs (Google style)
- Never log credentials — mask before printing

## Testing

```bash
pytest -v
```

Tests live in `tests/` mirroring the `src/` structure.

## Security Review

Changes that touch any of these require extra scrutiny:
- `crypto.py` — encryption/decryption
- `server.py` — socket server
- `bootstrap.py` — key generation and Chrome import
