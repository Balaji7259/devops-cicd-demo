set -euo pipefail

# Build the SSM parameter file with Python. Passing a 4.5 KB base64
# string as a shell-quoted CLI argument is the kind of thing that
# works until it meets a character it does not like; a JSON file has
# no quoting rules left to get wrong.
python3 - <<'PY'
import base64, gzip, json, os

raw = open("scripts/deploy-remote.sh", "rb").read()
# gzip before base64: 3.4 KB becomes ~2 KB of text.
payload = base64.b64encode(gzip.compress(raw, 9)).decode()
image = os.environ["IMAGE_URI"]
container = os.environ["CONTAINER_NAME"]
region = os.environ["AWS_REGION"]

# Split into short commands. RunCommand has a per-command length
# limit, and a single 4.8 KB command is what made the earlier
# attempts fail before they ever reached the instance. Several small
# commands reassemble the file on disk instead.
# A private root-owned directory, not /tmp. Ubuntu sets
# fs.protected_regular=2, which makes even root fail to open a file it
# does not own inside a sticky directory - the exact error that made
# earlier attempts fail with "cannot create /tmp/...: Permission
# denied" while looking like a payload problem.
workdir = "/var/lib/deploy-ci"

chunk_size = 800
chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)]

commands = [
    "install -d -m 700 " + workdir,
    "rm -f " + workdir + "/payload.b64",
]
for chunk in chunks:
    commands.append("printf '%s' '" + chunk + "' >> " + workdir + "/payload.b64")

commands.append(
    "base64 -d " + workdir + "/payload.b64 | gzip -dc > " + workdir + "/deploy.sh"
)
commands.append(
    "IMAGE_URI='" + image + "'"
    + " CONTAINER='" + container + "'"
    + " REGION='" + region + "'"
    + " bash " + workdir + "/deploy.sh"
    + "; rc=$?"
    + "; rm -f " + workdir + "/payload.b64 " + workdir + "/deploy.sh"
    + "; exit $rc"
)

with open("/tmp/params.json", "w", encoding="utf-8") as fh:
    json.dump({"commands": commands}, fh)

print("script bytes:", len(raw))
print("payload chars:", len(payload))
print("command count:", len(commands))
print("longest command:", max(len(c) for c in commands))
PY

# SSM rejects a comment longer than 100 characters, and a full ECR URI
# is ~108. Use the tag alone, which is the part that identifies the
# deploy anyway.
COMMENT="deploy ${IMAGE_URI##*:}"
COMMENT="${COMMENT:0:100}"

# Keep the CLI's own error text, and push it into an annotation so the
# reason is visible on the run page without opening the raw log.
if ! SEND_OUT="$(aws ssm send-command \
      --document-name "AWS-RunShellScript" \
      --instance-ids "${EC2_INSTANCE_ID}" \
      --comment "${COMMENT}" \
      --timeout-seconds 300 \
      --parameters file:///tmp/params.json \
      --query "Command.CommandId" --output text 2>&1)"; then
  # Skip blank lines: the AWS CLI prefixes its error with a newline,
  # and an annotation with an empty message is silently dropped.
  FIRST_LINE="$(printf '%s\n' "${SEND_OUT}" | sed '/^[[:space:]]*$/d' | head -n 1 | cut -c1-800)"
  echo "::error title=SSM CLI error::${FIRST_LINE}"
  printf '%s\n' "${SEND_OUT}"
  {
    echo '### SSM send-command failed'
    echo '```'
    printf '%s\n' "${SEND_OUT}"
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
  exit 1
fi

CMD_ID="${SEND_OUT}"
echo "SSM command id: ${CMD_ID}"

STATUS="Pending"
for attempt in $(seq 1 90); do
  STATUS="$(aws ssm get-command-invocation \
    --command-id "${CMD_ID}" \
    --instance-id "${EC2_INSTANCE_ID}" \
    --query Status --output text 2>/dev/null || echo "Pending")"
  case "${STATUS}" in
    Success|Failed|Cancelled|TimedOut) break ;;
  esac
  sleep 2
done

echo "----- remote stdout -----"
aws ssm get-command-invocation --command-id "${CMD_ID}" \
  --instance-id "${EC2_INSTANCE_ID}" \
  --query StandardOutputContent --output text || true

ERR_TEXT="$(aws ssm get-command-invocation --command-id "${CMD_ID}" \
  --instance-id "${EC2_INSTANCE_ID}" \
  --query StandardErrorContent --output text 2>/dev/null || echo '')"
echo "----- remote stderr -----" >&2
printf '%s\n' "${ERR_TEXT}" >&2

CODE="$(aws ssm get-command-invocation --command-id "${CMD_ID}" \
  --instance-id "${EC2_INSTANCE_ID}" \
  --query ResponseCode --output text 2>/dev/null || echo unknown)"
echo "final status: ${STATUS}, exit code: ${CODE}"

if [ "${STATUS}" != "Success" ]; then
  SHORT_ERR="$(printf '%s' "${ERR_TEXT}" | tr '\n' ' ' | cut -c1-600)"
  echo "::error title=Deployment failed::${STATUS} (exit ${CODE}): ${SHORT_ERR}"
  {
    echo '### Deployment did not succeed'
    echo "Status: \`${STATUS}\`, exit code: \`${CODE}\`"
    echo '```'
    printf '%s\n' "${ERR_TEXT}"
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
  exit 1
fi
