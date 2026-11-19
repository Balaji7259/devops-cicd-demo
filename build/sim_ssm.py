"""Check that the base64 payload and the JSON parameter survive intact."""
import base64
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
script = os.path.join(here, "..", "scripts", "deploy-remote.sh")
raw = open(script, "rb").read()
b64 = base64.b64encode(raw).decode()

print("script bytes:", len(raw))
print("base64 length:", len(b64))
print("contains quote:", ('"' in b64) or ("'" in b64))
print("contains backslash:", "\\" in b64)
print("contains space:", " " in b64)

image = "576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:abc123"
remote = (
    "echo '" + b64 + "' | base64 -d > /tmp/deploy-remote.sh"
    + " && IMAGE_URI='" + image + "' CONTAINER='devops-demo' REGION='ap-south-1' bash /tmp/deploy-remote.sh"
    + "; rc=$?; cleanup_tmp; exit $rc"
)

payload = json.dumps({"commands": [remote]})
print("payload length:", len(payload))
data = json.loads(payload)
print("round-trip OK, commands:", len(data["commands"]))
print("head:", data["commands"][0][:50])
print("tail:", data["commands"][0][-60:])
