#!/usr/bin/env bash
# Copy an image *manifest* between ECR repositories in the same registry (no rebuild).
# Verifies the destination has the same digest.
set -euo pipefail

SRC_REPO="${1:?src repo name (no registry)}"
DST_REPO="${2:?dst repo name}"
DIGEST="${3:?sha256:...}"
TAG="${4:?human tag to attach on dest}"
REGION="${AWS_REGION:-us-east-1}"

if [[ ! "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid digest: $DIGEST" >&2
  exit 1
fi

manifest="$(aws ecr batch-get-image \
  --region "$REGION" \
  --repository-name "$SRC_REPO" \
  --image-ids imageDigest="$DIGEST" \
  --query 'images[0].imageManifest' \
  --output text)"

if [[ -z "$manifest" || "$manifest" == "None" ]]; then
  echo "source manifest not found ${SRC_REPO}@${DIGEST}" >&2
  exit 1
fi

media="$(aws ecr batch-get-image \
  --region "$REGION" \
  --repository-name "$SRC_REPO" \
  --image-ids imageDigest="$DIGEST" \
  --query 'images[0].imageManifestMediaType' \
  --output text)"

put_args=(
  --region "$REGION"
  --repository-name "$DST_REPO"
  --image-manifest "$manifest"
  --image-tag "$TAG"
)
if [[ -n "$media" && "$media" != "None" ]]; then
  put_args+=(--image-manifest-media-type "$media")
fi

aws ecr put-image "${put_args[@]}" >/dev/null

got="$(aws ecr describe-images \
  --region "$REGION" \
  --repository-name "$DST_REPO" \
  --image-ids imageDigest="$DIGEST" \
  --query 'imageDetails[0].imageDigest' \
  --output text)"

if [[ "$got" != "$DIGEST" ]]; then
  echo "digest mismatch after copy: got ${got}" >&2
  exit 1
fi

echo "copied ${SRC_REPO}@${DIGEST} → ${DST_REPO}:${TAG} (digest preserved)"
