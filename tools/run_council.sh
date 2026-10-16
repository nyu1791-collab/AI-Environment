#!/usr/bin/env bash
# Run one council agent with retries, timeouts, and logs.
# Usage: tools/run_council.sh <model: glm|deepseek> <index> <workdir> [round]
# Safe to re-run: skips agents whose vote.md already exists (unless FORCE=1).
set -uo pipefail

MODEL_KEY="${1:?glm|deepseek}"
IDX="${2:?index}"
WORKDIR="${3:?workdir}"
ROUND="${4:-round1}"
MAX_TRIES="${MAX_TRIES:-4}"
TIMEOUT_SEC="${TIMEOUT_SEC:-86400}"
OPENCODE="${OPENCODE:-$HOME/.opencode/bin/opencode}"
LOGDIR="$WORKDIR/../logs"

case "$MODEL_KEY" in
  glm) MODEL="opencode/glm-5.3-flash-free" ;;
  deepseek) MODEL="opencode/deepseek-v4.1-flash-free" ;;
  *) echo "unknown model: $MODEL_KEY" >&2; exit 2 ;;
esac

[ -d "$WORKDIR" ] || { echo "missing workdir: $WORKDIR" >&2; exit 2; }
[ -x "$OPENCODE" ] || { echo "opencode not found: $OPENCODE" >&2; exit 2; }
mkdir -p "$LOGDIR"
NAME="${MODEL_KEY}-${IDX}"
LOG="$LOGDIR/${NAME}.log"

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

if [ -s "$WORKDIR/vote.md" ] && [ "${FORCE:-0}" != "1" ]; then
  log "skip: vote.md exists"; exit 0
fi

PROMPT="Read brief.md in this directory and carry out every step it describes. Work only inside this directory."

for try in $(seq 1 "$MAX_TRIES"); do
  log "start try=$try model=$MODEL"
  out="$LOGDIR/${NAME}.try${try}.jsonl"
  err="$LOGDIR/${NAME}.try${try}.err"
  timeout "$TIMEOUT_SEC" "$OPENCODE" run -m "$MODEL" --format json --dir "$WORKDIR" "$PROMPT" >"$out" 2>"$err" < /dev/null
  rc=$?
  bytes=$(wc -c < "$out")
  if [ "$rc" -eq 0 ] && [ "$bytes" -gt 0 ]; then
    log "finished rc=0 bytes=$bytes"
    exit 0
  fi
  log "failed rc=$rc bytes=$bytes"
  # Back off before retrying: 30s, 60s, 120s ...
  [ "$try" -lt "$MAX_TRIES" ] && sleep $((30 * (2 ** (try - 1))))
done

log "gave up after $MAX_TRIES tries"
exit 1
