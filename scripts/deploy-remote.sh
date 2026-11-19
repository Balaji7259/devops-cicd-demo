#!/usr/bin/env bash
# Runs ON the EC2 instance, delivered by the deploy job through AWS Systems
# Manager (RunCommand -> AWS-RunShellScript). There is no SSH connection and no
# key on the instance; the agent picks the command up and runs it as root.
#
# Contract: replace the running container with a new image. If the new image
# does not serve traffic, put the previous image back and exit non-zero.
#
# The exit code is always 1 when the deployment was not a success - a rollback
# is a recovery, not a pass. The pipeline must still go red so somebody looks.
#
# Inputs (environment):
#   IMAGE_URI       required, full ECR URI with tag
#   CONTAINER       container name            (default devops-demo)
#   REGION          AWS region                (default ap-south-1)
#   HOST_PORT       port published on the host (default 80)
#   HEALTH_ATTEMPTS poll count                (default 10)
#   HEALTH_SLEEP    seconds between polls     (default 2)
set -euo pipefail

: "${IMAGE_URI:?IMAGE_URI is required}"
CONTAINER="${CONTAINER:-devops-demo}"
REGION="${REGION:-ap-south-1}"
HOST_PORT="${HOST_PORT:-80}"
HEALTH_ATTEMPTS="${HEALTH_ATTEMPTS:-10}"
HEALTH_SLEEP="${HEALTH_SLEEP:-2}"

log() { printf '%s\n' "$*"; }

start_container() {
  docker run -d --name "$CONTAINER" -p "${HOST_PORT}:80" \
    --restart unless-stopped "$1" >/dev/null
}

wait_healthy() {
  local attempt
  for attempt in $(seq 1 "$HEALTH_ATTEMPTS"); do
    if curl -fsS "http://localhost:${HOST_PORT}/healthz" >/dev/null 2>&1; then
      log "healthy after ${attempt} attempt(s)"
      return 0
    fi
    sleep "$HEALTH_SLEEP"
  done
  return 1
}

# --- 1. what is running right now, before anything is touched ----------------
PREV_IMAGE=""
if docker inspect "$CONTAINER" >/dev/null 2>&1; then
  PREV_IMAGE="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
  log "currently running: ${PREV_IMAGE}"
else
  log "no container named ${CONTAINER} yet - this is a first deploy"
fi

# --- 2. authenticate and pull ------------------------------------------------
# Pull happens BEFORE the old container is removed, so a registry problem
# leaves the site untouched.
REGISTRY="${IMAGE_URI%%/*}"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null

log "pulling ${IMAGE_URI}"
docker pull "$IMAGE_URI"

# --- 3. swap -----------------------------------------------------------------
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
start_container "$IMAGE_URI"

if wait_healthy; then
  log "deployed and healthy: ${IMAGE_URI}"
  exit 0
fi

# --- 4. it failed: diagnose, then recover ------------------------------------
log "health check failed for ${IMAGE_URI}"
docker logs "$CONTAINER" --tail 50 >&2 || true

if [ -z "$PREV_IMAGE" ]; then
  log "nothing to roll back to - this was the first deploy"
  exit 1
fi

if [ "$PREV_IMAGE" = "$IMAGE_URI" ]; then
  log "previous image is the same tag - restarting it to restore service"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  start_container "$PREV_IMAGE"
  wait_healthy || log "restart did not become healthy either"
  exit 1
fi

log "ROLLING BACK to ${PREV_IMAGE}"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
start_container "$PREV_IMAGE"

if wait_healthy; then
  log "ROLLED BACK to ${PREV_IMAGE} - the previous version is serving again"
else
  log "ROLLBACK ALSO FAILED - the site is down and needs a human"
  docker logs "$CONTAINER" --tail 50 >&2 || true
fi

# Non-zero on purpose: the site is up, but this deployment did not succeed.
exit 1
