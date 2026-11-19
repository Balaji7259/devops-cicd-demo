#!/usr/bin/env bash
# Simulate the workflow's parameter construction without calling AWS.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE_URI="576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:abc123"
CONTAINER_NAME="devops-demo"
AWS_REGION="ap-south-1"

SCRIPT_B64="$(base64 -w0 scripts/deploy-remote.sh)"
echo "base64 length: ${#SCRIPT_B64}"
case "$SCRIPT_B64" in
  *[\"\']*) echo "PROBLEM: base64 contains quotes" ;;
  *) echo "base64 is quote-free: OK" ;;
esac

REMOTE="echo '${SCRIPT_B64}' | base64 -d > /tmp/deploy-remote.sh"
REMOTE="${REMOTE} && IMAGE_URI='${IMAGE_URI}' CONTAINER='${CONTAINER_NAME}' REGION='${AWS_REGION}' bash /tmp/deploy-remote.sh"
REMOTE="${REMOTE}; rc=\$?; rm -f /tmp/deploy-remote.sh; exit \$rc"

PAYLOAD="{\"commands\":[\"${REMOTE}\"]}"
echo "$PAYLOAD" | sed 's/^\(.\{110\}\).*/\1.../' 
echo "payload length: ${#PAYLOAD}"
printf '%s' "$PAYLOAD" > /tmp/payload.json

python - <<'PY'
import json
raw = open("/tmp/payload.json", encoding="utf-8").read()
data = json.loads(raw)
cmds = data["commands"]
print("JSON valid, commands count:", len(cmds))
print("starts:", cmds[0][:60])
print("ends:  ", cmds[0][-70:])
assert "base64 -d" in cmds[0]
assert "IMAGE_URI=" in cmds[0]
PY
