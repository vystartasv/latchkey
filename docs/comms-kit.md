# Comms Kit — Agent Infrastructure Launch

## 1. Twitter/X Thread

**Tweet 1:** I run 19 autonomous AI agents from cron. Here's the infrastructure they needed that nobody talks about.

**Tweet 2:** 4 problems: no shared state (race conditions on JSONL), no credentials (Touch ID unreachable from cron), context overflow (42MB repos into 40K context windows), silent failure cascades (24 fails before I notice).

**Tweet 3:** Built 4 tools in a weekend:
• Agent State DB — SQLite+WAL, atomic state, advisory locks, coordination
• Latchkey — Fernet-encrypted, Unix socket daemon, imported 424 Chrome passwords
• Context Packer — 2,521 files → 8 high-signal files
• Cron Guard — auto-pause at 3 consecutive failures

**Tweet 4:** The meta-lesson: infrastructure should be invisible to agents. They see `run_id: yyy` in their prompt and call `agent-state run finish` at the end. Everything else happens in the pre-cron hook.

**Tweet 5:** All open-source (MIT). 32 tests, 0.13s suite. github.com/vystartasv/agent-state-db + github.com/vystartasv/latchkey

---

## 2. LinkedIn Post

**I run 19 autonomous AI agents. The infrastructure nearly broke them.**

Four gaps nobody talks about: shared state for concurrent agents, credential access from cron (Touch ID doesn't work without fingers), context windows drowning in full repo dumps, and silent failure cascades.

Built the fix in a weekend — four tools that run as invisible infrastructure before the agent even sees its prompt:

• Agent State DB: SQLite+WAL, atomic key-value, advisory locks, cross-agent coordination
• Latchkey: Fernet-encrypted secrets served over a Unix socket. Imported 424 passwords from Chrome.
• Context Packer: 2,521 files → 8 high-signal files. Local models can actually see what matters.
• Cron Guard: Auto-pauses jobs after 3 consecutive failures.

Open source, MIT. 32 tests, 0.13 seconds. Links in comments.

If you're running agents from cron — especially local models — you're going to hit these same gaps.

#AIagents #autonomousagents #python #devops #infrastructure

---

## 3. Telegram / Short

**Agent Infrastructure: 4 tools, 1 weekend, 19 agents enabled**

Built the missing infrastructure for autonomous AI agents:
• `agent-state` — shared state DB with locks & coordination
• `latchkey` — encrypted secrets, no Touch ID needed
• `context-packer` — repo pruner for local models
• `cron-guard` — auto-pause failing jobs

32 tests, 0.13s. MIT. github.com/vystartasv/agent-state-db

---

## 4. Hacker News / Show HN

**Title:** Show HN: Agent State DB + Latchkey — infrastructure for autonomous AI agents

I run 19 autonomous cron jobs (code review, self-improvement, disaster recovery) and kept hitting the same four gaps: no shared state, no credential access from cron, context window overflow for local models, and silent failure cascades.

Built four tools to fix it: a SQLite+WAL state DB with atomic key-value and advisory locks, a Unix socket daemon for encrypted credentials (imported 424 Chrome passwords), a context packer that prunes 2,521-file repos to 8 high-signal files, and a cron guard that auto-pauses jobs after 3 failures.

32 tests, 0.13s suite. MIT license. Would love feedback on the architecture.
