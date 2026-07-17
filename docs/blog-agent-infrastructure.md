# I Run 19 Autonomous AI Agents. Here's the Infrastructure They Needed That Nobody Talks About

*By Vilius Vystartas | May 2026*

My agents were running blind. Nineteen cron jobs — hourly code reviews, daily self-improvement loops, disaster recovery syncs, family weather briefings — all operating in complete isolation. They shared no state. They couldn't coordinate. When one failed, the others had no idea. And when they needed credentials, the 1Password daemon just stared back at a Touch ID prompt that'd never be answered.

The "agent infrastructure" conversation is all about models and prompts. But running a fleet of autonomous agents is an operations problem. Here's what I had to build before my agents could actually work.

---

## The Four Gaps That Broke Everything

**1. No shared state.** 19 agents writing to shared JSONL files with no locking. Race conditions were inevitable. One agent's output would silently overwrite another's. The hourly skill gap analyzer literally had a comment in its prompt: "read first to check if the entry already exists" — a handshake protocol in natural language.

**2. Credentials were impossible.** `op signin` requires Touch ID. Cron jobs don't have fingers. Any agent that needed a GitHub token, API key, or service password was dead in the water. The workaround was "don't use secrets from cron" — which meant agents couldn't publish, couldn't push, couldn't authenticate.

**3. Context overflow.** Local models (Qwen 8B, 40K context) got the entire repo dumped into their prompt. 2,521 files, 42 megabytes — `node_modules`, build artifacts, lock files. The agent would drown in noise before it ever saw the `AGENTS.md`.

**4. Silent failure cascades.** One bad model config caused every tick to fail — 24 times a day for hourly jobs — with no detection and no auto-pause. The "fix" was me noticing in the morning.

---

## What I Built: Four Tools, One Weekend

### Agent State DB — SQLite+WAL Shared State

The keystone. Every cron job gets a pre-cron hook that registers it in a SQLite database, starts a run, and injects the `run_id` into the agent's prompt. The agent finishes by calling `agent-state run finish <run_id> --status completed`.

What this enables that JSONL files couldn't:

```
# Atomic, versioned key-value state (no race conditions)
INSERT INTO state_kv VALUES (?, ?, ?, 1, ?)
ON CONFLICT DO UPDATE SET version = version + 1

# Advisory locks on shared resources
agent-state lock acquire catalog.json hourly-review --ttl 300

# Cross-agent coordination
agent-state coord working-on hourly-review catalog.json
```

The `ON CONFLICT DO UPDATE SET version = version + 1 RETURNING version` is one SQL statement. No read-modify-write window. Two agents can hit the same key simultaneously and neither loses a version. This took three iterations to get right — the first version had a classic SELECT-then-UPDATE race.

20 agents registered, 5 runs tracked, 0 active locks. The schema is five tables: `agents`, `runs`, `state_kv`, `locks`, `coordination`.

### Latchkey — Encrypted Secrets Without Interactive Auth

A Unix socket daemon that serves Fernet-encrypted credentials from SQLite. Agents call a five-line client:

```python
from latchkey.client import get_credential
gh = get_credential("github.com")
# → {"username": "vystartasv", "password": "ghp_...", "url": "https://github.com"}
```

The bootstrap imports Chrome's saved passwords (424 credentials from a 493-row CSV), encrypts them with Fernet (AES-128-CBC + HMAC-SHA256), and stores them in a chmod 600 SQLite database. The daemon listens on a Unix socket (chmod 600, no network exposure) and responds to JSON requests.

The 1Password dead-end is solved. Agents can now authenticate from cron.

### Context Packer — Token-Budgeted Repo Pruner

Instead of dumping the whole repo, this builds a compact, high-signal context package:

- **Prunes:** `node_modules`, `.git`, `dist`, `lib`, `build`, `__pycache__`, lock files, source maps, files over 500KB
- **Prioritizes:** `AGENTS.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `OPERATING-MANUAL.md` (score 0), recently modified source files (score 20-30)
- **Outputs:** Markdown with full priority files + previews of key sources + file listing

Real result: Origami SPFx lab — 2,521 files (42 MB) → 8 high-signal files in the context. The model can actually see what matters.

### Cron Guard — Failure Detection and Auto-Pause

Prevents the "24 failures before I notice" problem. Runs every 30 minutes, checks the state DB for consecutive failures, and outputs pause instructions:

```json
{
  "pause_instructions": [{
    "action": "pause",
    "job_id": "abc123",
    "reason": "3 consecutive failures — auto-paused by Cron Guard"
  }]
}
```

The Cron Guard agent reads this JSON and calls `cronjob action=pause` with the actual Hermes tool. The split is deliberate: the script detects, the agent acts. Standalone scripts can't call Hermes cron tools — they don't have the execution context.

---

## Architecture

```
~/.hermes/
├── state/
│   ├── agent_state.db          # SQLite+WAL, chmod 600, 5 tables
│   ├── agent_state_db/         # Python package + CLI
│   └── cron_guard.json         # Pause history
├── .latchkey/
│   ├── credentials.db          # Fernet-encrypted, chmod 600
│   ├── .master_key             # 44 bytes, chmod 600
│   ├── latchkey.sock           # Unix socket, chmod 600
│   └── daemon                  # launchd-managed, auto-restart
├── scripts/
│   ├── pre_cron.py             # Unified hook: state DB + context packer
│   ├── context_packer.py       # Repo pruner
│   └── cron_guard.py           # Failure detector
└── skills/                     # 153 skills, now with agent-infra skills
```

**Stack:** Python 3.11, SQLite (WAL mode), Fernet (cryptography), launchd (macOS)

---

## What I Learned

**1. Infrastructure should be invisible to agents.**
The agent shouldn't know about state DB registration or context pruning. It should just see `agent_id: xxx` and `run_id: yyy` in its prompt, do its work, and call `agent-state run finish` at the end. The pre-cron hook handles everything else. Invisible infrastructure is the best infrastructure.

**2. Python packages cannot have hyphens.**
`latchkey/` → works. Symlinked CLI entrypoints also need hardcoded `sys.path` because `__file__`-based resolution breaks through symlinks. Both encoded in memory now, but they each cost 20 minutes of debugging.

**3. Atomicity matters — use the database, not application locks.**
The first `set_state` implementation did SELECT version → increment → INSERT. This is a classic read-modify-write race. The fix was one SQL statement: `ON CONFLICT DO UPDATE SET version = version + 1 RETURNING version`. If two agents increment simultaneously, the database handles it. Application-level locking would have been slower and buggier.

**4. "Detect in script, act in agent" is the right split for cron tools.**
Cron Guard can't call `cronjob action=pause` from a standalone Python script — the Hermes tool API requires agent execution context. The pattern: script outputs structured JSON with instructions, the agent reads it and acts. This generalizes to any infrastructure tool that needs to call Hermes APIs.

**5. Tests at 0.11 seconds are inexcusable to skip.**
Eight tests for Agent State DB, 24 for Latchkey — both suites run in under 0.15s combined. They caught the `get_run` overwrite during patching, the `RETURNING` cursor ordering bug, and the race condition. At this speed, there's no reason not to have them.

**6. Credential security is about defense in depth.**
Fernet encryption at rest (credentials.db), chmod 600 on the DB file, chmod 600 on the master key, chmod 600 on the Unix socket, no network exposure, auto-delete the Chrome CSV after import. Any single layer failing shouldn't expose secrets.

---

## Get It

Everything is open-source under MIT:

- **[Agent State DB](https://github.com/vystartasv/agent-state-db)** — `pip install -e .` — 8 tests, 0.05s
- **[Latchkey](https://github.com/vystartasv/latchkey)** — `pip install -e .` — 24 tests, 0.08s
- Context Packer + Cron Guard — bundled as scripts in the repos above

```bash
# Agent State DB
git clone https://github.com/vystartasv/agent-state-db
cd agent-state-db && pip install -e .

# Latchkey
git clone https://github.com/vystartasv/latchkey
cd latchkey && pip install -e .
latchkey bootstrap  # Import Chrome passwords
latchkey serve       # Start daemon
```

If you're running autonomous agents — especially local models, especially from cron — you're going to hit these same four gaps. The infrastructure matters more than the prompts. Feedback welcome.
