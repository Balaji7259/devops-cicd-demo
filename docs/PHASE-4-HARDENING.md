# Phase 4 — Hardening

**Started:** 18 November 2026
**State:** in progress — items 1 and 2 shipped and verified; two items remain
(ECR lifecycle, failure notification), plus two console steps to finish 4.2.

Phase 3 made deployment automatic. Phase 4 makes it survivable: what happens when
the thing being deployed is wrong, when SSH itself is the risk, and when the
registry quietly grows forever.

---

## 4.1 Automatic rollback on a failed health check

**Commit:** `2134e71` · **Run:** #11, success, 60s

### The gap it closes

Before this change, the deploy sequence was: destroy the working container →
start the new one → poll `/healthz` → if it never answers, fail the job. The job
went red, but by then the site was already down and stayed down until a human
intervened. That is monitoring, not resilience.

### What it does now

The remote logic lives in `scripts/deploy-remote.sh`, piped over SSH by the
deploy job:

```
1. read the currently running image                        -> PREV
2. authenticate to ECR and pull the new image               (site untouched)
3. remove the old container, start the new one
4. poll /healthz up to HEALTH_ATTEMPTS times
     healthy   -> exit 0
     unhealthy -> dump the last 50 log lines
                  remove the failed container
                  start PREV
                  poll again
                  exit 1 in every case
```

Three decisions worth defending:

**The pull happens before the swap.** A registry outage, an expired token or a
missing tag leaves the running site completely untouched — the failure costs
nothing.

**A successful rollback still exits 1.** The site is up, but the deployment did
not succeed. Returning zero here would produce a green run that hides a real
defect, which is the failure mode Phase 3's guard job exists to prevent.

**The script is a separate file, not an inline heredoc.** It can be linted
(`bash -n`), reviewed as a unit, and — the reason it exists — executed directly
on the server without going through GitHub at all.

### Edge cases handled

| Situation | Behaviour |
|---|---|
| First ever deploy, nothing running | no PREV; the failed container is left in place for inspection, exit 1 |
| Redeploying the same tag (rollback run) | PREV equals the new URI; the container is simply restarted, exit 1 |
| Pull fails | old container never removed, site unaffected |
| Rollback itself fails to become healthy | explicit "the site is down and needs a human" in the log, container logs dumped |

### How it was verified

Testing was done on the real instance, not by reading the code. A deliberately
unhealthy image was built (bare `nginx:alpine`, no site files, so `/healthz`
returns 404) and pushed to ECR as `broken-test`. Two runs against a throwaway
container on port 8081, leaving the live site alone:

**Test A — healthy deploy**

```
no container named devops-demo-test yet - this is a first deploy
pulling ...:273f415d3a44...
healthy after 2 attempt(s)
deployed and healthy: ...:273f415d3a44...
```

**Test B — unhealthy deploy over a healthy container**

```
currently running: ...:273f415d3a44...
pulling ...:broken-test
health check failed for ...:broken-test
ROLLING BACK to ...:273f415d3a44...
healthy after 2 attempt(s)
ROLLED BACK to ...:273f415d3a44... - the previous version is serving again
exit code 1
```

Server-side nginx log confirmed the real cause rather than a generic failure:

```
open() "/usr/share/nginx/html/healthz" failed (2: No such file or directory)
"GET /healthz HTTP/1.1" 404
```

State afterwards: the test container was running the **good** image on 8081
(`200`), the live container was untouched (`Up 2 hours`), and both the test
container and the test image were removed.

Then run #11 deployed the change itself through the pipeline: `2134e71`,
container replaced at 08:26:37Z, public `/healthz` returning `ok`.

### Cost of the mistake that proved it

The `broken-test` tag remains in ECR because the CI user deliberately has no
delete permission. It has to be removed in the console. That restriction is
working as intended — the identity that deploys cannot destroy evidence.

---

## 4.2 Deploy through Systems Manager instead of SSH

**Commits:** `f584873` (migration) → `cd65b74` → `cecccea` (fixes) · **Run:** #18, all four jobs green

### The gap it closes

Port 22 was open to `0.0.0.0/0`. GitHub publishes 5,622 IPv4 runner ranges and
a security group allows 60 rules, so whitelisting was never an option - the
deploy path itself had to stop needing SSH.

### What changed

| Before | After |
|---|---|
| SSH key written to the runner's disk | No key exists; deleted from GitHub secrets |
| `ssh -o StrictHostKeyChecking=yes` | `aws ssm send-command` |
| Ran as `ubuntu` | Runs as **root**, via the agent |
| Port 22 open to the world | No inbound port needed |
| Connection is the only evidence | Every command and its output is stored in AWS command history |

The deploy script is unchanged. Only the transport moved, which is why the
rollback logic needed no rework: `scripts/deploy-remote.sh` still decides what
happens, and `ssm:SendCommand` is merely how it gets there.

The CI user's permissions were extended with a **separate policy**,
`ssm-deploy-devops-cicd-demo`, pinned to one instance ARN plus the
`AWS-RunShellScript` document. Push rights and shell rights stay in different
documents so either can be revoked alone.

### The four failed attempts, and what they actually were

This took four red runs. The cause was not what any of them appeared to say.

| Run | Change tried | Real cause |
|---|---|---|
| #14 | inline JSON parameter | `--comment` was 105 characters; SSM allows 100 |
| #15 | `file://` parameter file | same comment rejection |
| #16 | chunked commands | same comment rejection |
| #17 | root-owned staging dir | same comment rejection |

The error was always:

```
ValidationException: Value 'deploy 576329196399.dkr.ecr...' at 'comment'
failed to satisfy constraint: Member must have length less than or equal to 100
```

Four characters. `--comment` is a cosmetic label, and it rejected every request
before it reached the machine.

**Why it stayed invisible for four runs:** the first attempt used `set -e`, which
killed the step the moment the CLI failed and discarded its message. The fix was
to capture stderr with `2>&1` and echo it. That should have ended it. It did not,
because the diagnostic annotation was built from the first line of the AWS error
- and the AWS CLI prefixes its error with a blank line. GitHub silently discards
an annotation with an empty message, so the instrument built to reveal the error
was itself invisible.

Two mistakes stacked, each hiding the other. The lesson is not "read the docs",
it is: **when a diagnostic shows nothing, suspect the diagnostic.**

A secondary finding, unrelated to the pipeline: `fs.protected_regular=2` on
Ubuntu makes even root fail to open a file it does not own inside `/tmp`. A
leftover file from earlier testing caused exactly that, which is why the script
is now staged in `/var/lib/deploy-ci` (mode 700) rather than a predictable path
in a shared directory.

### Verification

Run #18 was the first genuine end-to-end deploy through SSM: build, push, then
`SendCommand` executing the script as root, all four jobs green.

The pipeline was proven twice: once by executing the extracted step locally
(`EXIT=0`, container swapped, `final status: Success, exit code: 0`), and once by
the run itself.

### Closing the port

Both console steps are done. Verified from outside rather than assumed:

```
port 22 : open=False
port 80 : open=True
```

The instance now has exactly one reachable port, and the deploy path does not
use it.

Runs #20 and #21 then deployed through SSM against the new address with all four
jobs green, and the running container was confirmed on the instance:

```
IMAGE=...devops-cicd-demo:70ad8bc...
STATUS=Up 56 seconds
started=2026-11-19T05:58:22Z     (inside run #21's window)
port 80: docker-proxy
```

### One thing this exposed

The instance's public IPv4 changed when it was stopped and started, which broke
the `EC2_HOST` secret and caused a cancelled run before anyone noticed why. A
dynamic address on a public demo is a design smell: an Elastic IP keeps the
address across restarts and costs the same as the attached IPv4 already being
billed.

---

## 4.3 Remaining work

| Item | Why it matters | Approach |
|---|---|---|
| ECR lifecycle policy | Untagged layers accumulate with every build | Expire untagged images after 14 days; keep tagged ones; also delete the `broken-test` tag by hand |
| Failure notification | A red run nobody sees did not happen | Webhook on `failure` and on `rollback occurred` |

### Ordering rationale

SSH first. It is the only open-to-the-world service left, and it removes two
long-lived secrets (the private key and the ability to reach the box at all).
Notifications last, because a pipeline that recovers by itself is less urgent to
be told about than one that leaves the site down.
