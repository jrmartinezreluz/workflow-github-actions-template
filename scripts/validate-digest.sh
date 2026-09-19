#!/usr/bin/env bash
# Fail unless stdin/arg is sha256:<64 hex>.
set -euo pipefail
value="${1:-}"
if [[ ! "$value" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid digest: ${value:-<empty>}" >&2
  exit 1
fi
echo "digest_ok=${value}"
