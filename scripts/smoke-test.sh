#!/usr/bin/env bash
# Start an image and verify every route the site depends on.
#
# Used twice in the pipeline: once on the freshly built image (before it may be
# pushed), and once on a previously published image during a rollback. Running
# the same script for both means a rollback cannot sneak past a check that a
# normal deploy has to pass.
#
# Usage: bash scripts/smoke-test.sh <image-uri> [port]
set -euo pipefail

IMAGE_URI="${1:?usage: smoke-test.sh <image-uri> [port]}"
PORT="${2:-8080}"
CONTAINER="smoke-test"

cleanup() {
  docker logs "$CONTAINER" --tail 30 2>/dev/null || true
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
echo "starting ${IMAGE_URI} on port ${PORT}"
docker run -d --name "$CONTAINER" -p "${PORT}:80" "$IMAGE_URI" >/dev/null

healthy=false
for attempt in $(seq 1 15); do
  if curl -fsS "http://localhost:${PORT}/healthz" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done

if [ "$healthy" != "true" ]; then
  echo "::error::container did not answer /healthz within 15s"
  exit 1
fi
echo "healthy after ${attempt}s"

check() {
  local path="$1" expect="${2:-200}" code
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}${path}")
  if [ "${code}" != "${expect}" ]; then
    echo "::error::GET ${path} returned ${code}, expected ${expect}"
    exit 1
  fi
  echo "GET ${path} -> ${code}"
}

check /healthz
check /
check /about.html
check /style.css
check /assets/logo.svg

body=$(curl -fsS "http://localhost:${PORT}/healthz")
if [ "${body}" != "ok" ]; then
  echo "::error::/healthz body was '${body}', expected 'ok'"
  exit 1
fi

if ! curl -fsS "http://localhost:${PORT}/" | grep -q '<title>'; then
  echo "::error::served HTML has no <title>"
  exit 1
fi

echo "smoke test passed for ${IMAGE_URI}"
