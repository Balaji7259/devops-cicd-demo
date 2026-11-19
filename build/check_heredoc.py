"""Extract the Python block from deploy.yml and verify the chunked commands."""
import base64
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile

import yaml

d = yaml.safe_load(open("../.github/workflows/deploy.yml", encoding="utf-8"))
step = [s for s in d["jobs"]["deploy"]["steps"]
        if s.get("name", "").startswith("Pull, replace")][0]
code = re.search(r"<<'PY'\n(.*?)\nPY\n", step["run"], re.S).group(1)

out_path = os.path.join(tempfile.gettempdir(), "params_check.json").replace("\\", "/")
code = code.replace("/tmp/params.json", out_path)

env = dict(os.environ)
env.update({
    "IMAGE_URI": "576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:abc123",
    "CONTAINER_NAME": "devops-demo",
    "AWS_REGION": "ap-south-1",
})

proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                      env=env, cwd="..")
print("exit:", proc.returncode)
print(proc.stdout.strip())
if proc.stderr.strip():
    print("STDERR:", proc.stderr.strip())

data = json.load(open(out_path, encoding="utf-8"))
cmds = data["commands"]
print("---")
print("commands:", len(cmds))
print("max command length:", max(len(c) for c in cmds))
print("all under 1024 chars:", all(len(c) < 1024 for c in cmds))

# Reassemble the payload exactly as the instance will.
b64 = "".join(
    c.split("printf '%s' '")[1].split("' >>")[0] for c in cmds if "printf '%s' '" in c
)
restored = gzip.decompress(base64.b64decode(b64))
original = open("../scripts/deploy-remote.sh", "rb").read()
print("reassembled payload identical:", restored == original)

print("--- first command ---")
print(cmds[0])
print("--- decode command ---")
print(cmds[-2])
print("--- run command (truncated) ---")
print(cmds[-1][:110] + " ... " + cmds[-1][-60:])
