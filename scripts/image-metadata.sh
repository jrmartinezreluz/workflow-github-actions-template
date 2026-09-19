#!/usr/bin/env bash
# Print image metadata after docker buildx / crane inspect.
set -euo pipefail

IMAGE_URI="${1:?usage: image-metadata.sh <image-ref>}"

digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE_URI" 2>/dev/null || true)"
if [[ -z "$digest" || "$digest" == "<no value>" ]]; then
  # image-ref may already be repo@sha256:...
  if [[ "$IMAGE_URI" == *@sha256:* ]]; then
    digest="${IMAGE_URI#*@}"
    repo="${IMAGE_URI%@*}"
  else
    echo "Could not resolve digest for $IMAGE_URI" >&2
    exit 1
  fi
else
  repo="${digest%@*}"
  digest="${digest#*@}"
fi

if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid digest: $digest" >&2
  exit 1
fi

echo "IMAGE_REPOSITORY=${repo}"
echo "IMAGE_DIGEST=${digest}"
echo "IMAGE_URI=${repo}@${digest}"
