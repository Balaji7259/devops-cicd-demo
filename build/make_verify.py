"""Build a params file for an ad-hoc read-only verification command."""
import json

cmd = (
    'docker ps --format "IMAGE={{.Image}} STATUS={{.Status}}"; '
    'docker inspect --format "started={{.State.StartedAt}}" devops-demo; '
    'echo "--- port 80 ---"; ss -lntp | grep ":80 " || true'
)

with open("verify.json", "w", encoding="utf-8") as fh:
    json.dump({"commands": [cmd]}, fh)

print("wrote verify.json")
