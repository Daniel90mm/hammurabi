# Agent Instructions


<!-- BEGIN MANAGED: agent-delegation -->
## Agent Delegation

This repository may use DeepSeek only through `agent-delegate`.

Before delegating, write a task file with YAML front matter declaring `provider`, `topic`, `allowed_read`, `allowed_write`, and `output`. Run `agent-delegate deepseek --dry-run <task-file>` before the first real call.

Use DeepSeek only for bounded, reviewable work. Do not call DeepSeek directly, and do not send secrets, credentials, private logs, compliance-sensitive material, or files outside the declared allowlist.

DeepSeek output is advisory. The active Codex/Claude agent owns final review, tests, edits, and commits.

If you are a Codex agent and Daniel explicitly asks for parallel agents, subagents, or delegation, prefer native Codex subagents for repo-private parallel work. Keep each subagent task bounded, give it a disjoint read/write scope, and merge results only after reviewing them in the parent thread.

For non-interactive Codex delegation, use `codex exec` only with an explicit `--cd`, sandbox, and approval policy. Prefer separate git worktrees for concurrent write tasks.
<!-- END MANAGED: agent-delegation -->
