> **Mirror of CLAUDE.md — edit either, they must stay byte-identical.** The pre-commit hook will reject divergence. Run `scripts/sync-agent-docs.sh` if they drift.

# Agent instructions — hammurabi

<!-- BEGIN MANAGED: agent-delegation -->
## Agent Delegation

This repository may use DeepSeek only through `agent-delegate`.

Before delegating, write a task file with YAML front matter declaring `provider`, `topic`, `allowed_read`, `allowed_write`, and `output`. Run `agent-delegate deepseek --dry-run <task-file>` before the first real call.

Use DeepSeek only for bounded, reviewable work. Do not call DeepSeek directly, and do not send secrets, credentials, private logs, compliance-sensitive material, or files outside the declared allowlist.

DeepSeek output is advisory. The active Codex/Claude agent owns final review, tests, edits, and commits.

If you are a Codex agent and Daniel explicitly asks for parallel agents, subagents, or delegation, prefer native Codex subagents for repo-private parallel work. Keep each subagent task bounded, give it a disjoint read/write scope, and merge results only after reviewing them in the parent thread.

For non-interactive Codex delegation, use `codex exec` only with an explicit `--cd`, sandbox, and approval policy. Prefer separate git worktrees for concurrent write tasks.
<!-- END MANAGED: agent-delegation -->

## Identity

Hammurabi is an agent-based society simulator that derives inequality, housing markets, and justice-system outcomes from first principles. Seed it with 4 founding parameters (population, skill variance, risk tolerance, punishment regime) and watch civilization-level statistics emerge from individual agent interactions. The goal is the simplest possible model whose emergent properties qualitatively match real societies.

The project is ~70% idea generation (mechanics, hypotheses, analysis) and ~30% simple UI and visualization (a flat GUI dashboard: 2D map + stats + charts, plots, maybe a thin web viewer later).

## Hard rules

### Read before edit
After ~10 messages, re-read any file before editing it. Auto-compaction destroys your memory of the exact contents, and the Edit tool fails silently on stale `old_string` matches. When in doubt, Read.

### Dead code first, refactor second
Before any structural refactor of a file >300 LOC, remove dead props, unused imports, and debug logs in a separate commit. Do not stack new complexity on top of old garbage.

### Phased refactors
Never touch more than 5 files in one response during a refactor. Finish a phase, verify (tests / typecheck / manual), get approval, continue.

### Navigate by package boundary
In unfamiliar areas, start from `README.md` → `docs/` → top-level directory purposes. Treat the directory layout as the API. Do not grep blindly from root.

### No invention
Do not invent URLs, version numbers, API endpoints, real-world statistics, or citations. Verify or omit.

### Plan first for non-trivial work
For anything beyond a localized edit, output the plan and wait for explicit approval ("yes", "do it") before writing code.

### Testing
For pure functions (economy calculations, statistics, punishment logic), write a test in `tests/`. For simulation runs or exploratory mechanics, write a smoke script in `tests/smoke/` — a minimal script that imports the module, runs a short simulation, and exits 0 on success. No assertions required. If neither fits, log the open risk in the PROJECT_LOG.md entry.

### Keep `docs/NAVIGATION.md` current
When you add a significant doc or top-level directory, append a row to `docs/NAVIGATION.md`. One line per entry. This is the index a future agent hits before anything else.

### Work from real errors
If a bug report has no output, ask the user to run a command and paste the result. Do not guess at error states.

### Ask, don't loop
If a fix does not work after two attempts, stop. State where your mental model is wrong and ask for clarification. Do not keep trying variations.

## File conventions

### All-caps = agent-maintained
Meta-files at the repo root use `UPPER_SNAKE_CASE.md` (CLAUDE.md, AGENTS.md, PROJECT_LOG.md, DESIGN_PRINCIPLES.md). These are agent-maintained.

Human-written reference docs in `docs/` use lowercase (`mechanics.md`, `economy.md`, `punishment.md`). The case is the signal — do not capitalize human docs, do not lowercase agent docs.

Exception: `README.md` is the universal convention and is always caps regardless.

### Conditional files (ship-but-dormant)

One root file ships with every project but stays dormant until summoned. Do **not** engage its conventions on ordinary work:

- **`DESIGN_PRINCIPLES.md`** — read and obey when making UI/visualization decisions (GUI dashboard, charts, plots, web viewer). For pure simulation/logic work, ignore. This project has ~30% UI so it will be engaged often.

If unsure whether to engage, ask once.

## PROJECT_LOG.md conventions

PROJECT_LOG.md is the single append-only record of decisions, ideas, findings, and open threads. It replaces the template's split between `IDEAS_TRAIL.md` and `RESEARCH_LOG.md`.

### When to append

- A mechanic, hypothesis, or experiment worth exploring arises.
- A project direction is decided or changes.
- A simulation run produces an interesting finding.
- An idea is considered and explicitly rejected (with reason).
- An earlier statement is corrected.
- A question or unresolved thread needs follow-up.

Do not log routine Q&A, tool-use details, or ordinary implementation steps. Filter: *would a future session be meaningfully worse off without this entry?*

### Entry format

```markdown
## YYYY-MM-DD - Short title

Type: Idea | Decision | Finding | Rejected | Correction | Open thread

Brief context in 2-6 sentences. Include the caveat, rejected alternative, or uncertainty when relevant.
```

### Entry types

| Type | When to use |
|------|-------------|
| **Idea** | New mechanic, hypothesis, experiment, or question worth exploring |
| **Decision** | Committed direction, architecture choice, pivot |
| **Finding** | Result from a simulation run or analysis |
| **Rejected** | Idea considered and explicitly ruled out (with reason) |
| **Correction** | Earlier statement was wrong or incomplete |
| **Open thread** | Unresolved question needing follow-up |

## Git conventions

### Commit and push on new content
When any of the following happens, stage the changed files, write a short commit message, and push:

- A new file is created anywhere in the repo.
- An entry is appended to `PROJECT_LOG.md`.
- A meaningful section is added to `docs/NAVIGATION.md`.

Do not batch unrelated changes into one commit. Do not wait to be asked. Do not force-push or amend published commits.

Commit message style: imperative, lowercase, no period. Examples:
- `add gini coefficient calculation`
- `log idea: reputation system`
- `reject insurance markets as out of scope`

## Protocols

### Session handoff — `handoffs/SESSION_<YYYY-MM-DD_HHMM>.md`

Write one when any of these triggers fire:

- **Coherence degrading** — you are asking the same question twice, misremembering file contents you just read, or contradicting yourself.
- **User frustration** — the user is visibly annoyed, the session has lost its thread, or the user says "start over".
- **Natural phase boundary** — a clean checkpoint (exploration → implementation, simulation → visualization, mechanics → calibration).

Do **not** trigger on conversation length or proximity to compaction. Auto-compaction is routine and is not a signal.

Contents:

- **Just completed** — what actually got done, not what was attempted.
- **Next exact step** — the single next action.
- **Files touched** — paths, so the next agent re-reads them fresh.
- **Open threads** — deferred decisions and assumptions still in-head.
- **Do not** — things already tried that failed, so the next session does not loop.

### Consult — `consults/CONSULT_<topic>.md`

When you are stuck, **ask the user first**: *"I'm stuck on X. Want me to write a consult?"* Only proceed on explicit agreement.

Structure:

```
## For the consultant

[Register, depth, format. This is LLM-to-LLM — human readability is
not required. Example: "Answer in raw causal chains. No preamble.
No hedging. If you need more data, list exact grep commands."]

## Problem

[What the project is in 3–5 sentences. What has been tried, with
file:line references and why each attempt failed. Numbered specific
questions — answerable, not "what should I do". Inlined relevant
code (the consultant has no repo access). Hard constraints.]
```

The user pastes section-by-section into another model and saves the reply as `consults/CONSULT_<topic>_REPLY.md`. The requesting agent reads the reply and continues.

The act of writing the Problem section resolves a large fraction of consults before they are sent. This is intentional.

## Mirror enforcement

CLAUDE.md and AGENTS.md must be byte-identical. When you edit one, immediately overwrite the other (`cp CLAUDE.md AGENTS.md` or the reverse). The pre-commit hook will reject commits where they differ.

## Learned conventions

<!--
Append-only. Add an entry when you discover a structural fact worth persisting across sessions.

Filter: would a future session be meaningfully worse off without this entry? If no, skip it.

Keep entries to one or two lines. Prefix with date: `YYYY-MM-DD: <fact>`.
-->
