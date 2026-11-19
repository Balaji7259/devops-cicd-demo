"""Reproduce the workflow's parameter-file generation locally and validate it."""
import base64
import json
import os

script = base64.b64encode(
    open("../scripts/deploy-remote.sh", "rb").read()
).decode()

image = "576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:f584873"
container = "devops-demo"
region = "ap-south-1"

remote = (
    "echo '" + script + "' | base64 -d > /tmp/deploy-remote.sh"
    + " && IMAGE_URI='" + image + "'"
    + " CONTAINER='" + container + "'"
    + " REGION='" + region + "'"
    + " bash /tmp/deploy-remote.sh"
    + "; rc=$?; rm -f /tmp/deploy-remote.sh; exit $rc"
)

params = {"commands": [remote]}
with open("params.json", "w", encoding="utf-8") as fh:
    json.dump(params, fh)

size = os.path.getsize("params.json")
print("params.json bytes:", size)
print("under the 100 KB SSM limit:", size < 100_000)

reloaded = json.load(open("params.json", encoding="utf-8"))
cmds = reloaded["commands"]
print("command count:", len(cmds))
print("head:", cmds[0][:45])
print("tail:", cmds[0][-55:])

# The decoded script must be byte-identical to the original.
decoded = base64.b64decode(cmds[0].split("'")[1])
original = open("../scripts/deploy-remote.sh", "rb").read()
print("round-trip identical:", decoded == original)
