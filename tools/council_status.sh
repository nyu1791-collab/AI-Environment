#!/usr/bin/env bash
# Read-only status of council agents: which files each agent has written.
# Usage: tools/council_status.sh [council_root]
set -uo pipefail
ROOT="${1:-$HOME/ai-council/round1}"
cd "$ROOT" || { echo "missing: $ROOT" >&2; exit 1; }
printf "%-14s %-9s %-9s %-9s\n" agent proposal critique vote
for d in */; do
  d="${d%/}"
  printf "%-14s %-9s %-9s %-9s\n" "$d" \
    "$(test -s "$d/proposal.md" && echo yes || echo -)" \
    "$(test -s "$d/critique.md" && echo yes || echo -)" \
    "$(test -s "$d/vote.md" && echo yes || echo -)"
done
echo "opencode processes: $(pgrep -fc 'opencode run -m' || true)"
