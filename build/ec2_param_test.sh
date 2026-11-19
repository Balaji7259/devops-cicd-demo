#!/usr/bin/env bash
# Runs ON EC2 to prove whether the send-command payload parses.
# The instance role cannot send commands, so an AccessDenied here means
# "payload fine, permissions differ" - not "payload broken".
set -uo pipefail

IMAGE_URI="576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:f584873"
CONTAINER_NAME="devops-demo"
AWS_REGION="ap-south-1"
EC2_INSTANCE_ID="i-01c13546bb8b4b707"
SCRIPT="/tmp/deploy-remote.sh"

echo "--- script present? ---"
ls -l "$SCRIPT" || exit 2

SCRIPT_B64="$(base64 -w0 "$SCRIPT")"
echo "base64 length: ${#SCRIPT_B64}"

REMOTE="echo '${SCRIPT_B64}' | base64 -d > /tmp/deploy-check.sh"
REMOTE="${REMOTE} && IMAGE_URI='${IMAGE_URI}' CONTAINER='${CONTAINER_NAME}' REGION='${AWS_REGION}' bash /tmp/deploy-check.sh"
REMOTE="${REMOTE}; rc=\$?; exit \$rc"

PAYLOAD="{\"commands\":[\"${REMOTE}\"]}"
echo "payload length: ${#PAYLOAD}"

echo "--- does the CLI accept this payload? ---"
aws ssm send-command \
  --region "$AWS_REGION" \
  --document-name "AWS-RunShellScript" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --comment "parameter parse test" \
  --timeout-seconds 300 \
  --parameters "$PAYLOAD" \
  --query "Command.CommandId" --output text 2>&1 | tail -4

echo "--- exit: $? ---"
