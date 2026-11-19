"""Mirror the workflow's SSM payload builder so it can be tested directly.

Usage: python make_params.py [dry|live] [output.json]
"""
import base64
import gzip
import json
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
out_name = sys.argv[2] if len(sys.argv) > 2 else "params.json"

workdir = "/var/lib/deploy-ci"

raw = open("../scripts/deploy-remote.sh", "rb").read()
payload = base64.b64encode(gzip.compress(raw, 9)).decode()

chunk_size = 800
chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)]

commands = [
    "install -d -m 700 " + workdir,
    "rm -f " + workdir + "/payload.b64",
]
for chunk in chunks:
    commands.append("printf '%s' '" + chunk + "' >> " + workdir + "/payload.b64")

commands.append("base64 -d " + workdir + "/payload.b64 | gzip -dc > " + workdir + "/deploy.sh")

if mode == "dry":
    commands.append(
        "bash -n " + workdir + "/deploy.sh && echo SYNTAX_OK && wc -c < " + workdir + "/deploy.sh"
        "; rc=$?; rm -f " + workdir + "/payload.b64 " + workdir + "/deploy.sh; exit $rc"
    )
else:
    commands.append(
        "IMAGE_URI='576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:459a8b0febd84c3d49898ad5e6e7269964ce5aa4'"
        " CONTAINER='devops-demo' REGION='ap-south-1' bash " + workdir + "/deploy.sh"
        "; rc=$?; rm -f " + workdir + "/payload.b64 " + workdir + "/deploy.sh; exit $rc"
    )

with open(out_name, "w", encoding="utf-8") as fh:
    json.dump({"commands": commands}, fh)

print("mode:", mode)
print("script bytes:", len(raw))
print("payload chars:", len(payload))
print("commands:", len(commands))
print("longest command:", max(len(c) for c in commands))
