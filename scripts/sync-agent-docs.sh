#!/usr/bin/env bash
# Keep CLAUDE.md and AGENTS.md byte-identical.
# Copies whichever was modified more recently over the other.
# Run manually, or rely on the pre-commit hook to catch divergence.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ ! -f CLAUDE.md || ! -f AGENTS.md ]]; then
    echo "sync-agent-docs: both CLAUDE.md and AGENTS.md must exist" >&2
    exit 1
fi

if cmp -s CLAUDE.md AGENTS.md; then
    echo "sync-agent-docs: already identical"
    exit 0
fi

if [[ CLAUDE.md -nt AGENTS.md ]]; then
    cp CLAUDE.md AGENTS.md
    echo "sync-agent-docs: CLAUDE.md → AGENTS.md"
else
    cp AGENTS.md CLAUDE.md
    echo "sync-agent-docs: AGENTS.md → CLAUDE.md"
fi
