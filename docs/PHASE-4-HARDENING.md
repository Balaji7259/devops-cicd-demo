# Phase 4 — Hardening

**Started:** 18 November 2026
**State:** complete. 4.1, 4.2 and 4.3 shipped and verified; notifications are a
recorded decision, not an oversight. See 4.5 for the exit record.

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
the `EC2_HOST` secret and caused a cancelled run before anyone noticed why.

**Fixed afterwards:** an Elastic IP was allocated and associated, so the address
is now static at `15.252.179.238` and survives stop/start. The realistic cost is
unchanged - an attached public IPv4 is billed either way - and one whole class of
silent failure is gone: the stored host no longer goes stale behind a restart.

---

## 4.3 ECR lifecycle policy

**Applied** — verified in the console, two rules active:

| Priority | Tag status | Criteria | Action |
|---|---|---|---|
| 1 | Untagged | 14 days since created | Expire |
| 2 | Tagged (`*`) | more than 50 images | Expire |

The policy file lives at `.aws/ecr-lifecycle-policy.json`, so it is reviewable
and reproducible rather than a console one-off.

**Why these two rules.** Every build leaves an untagged manifest behind when a
tag is superseded - invisible in the UI, still billed. The second rule keeps
rollback history bounded without making it age-based: a rule that expired
*tagged* images by age would eventually delete rollback targets, and the failure
would stay silent until the day someone needed one.

Also deleted the `broken-test` image left over from the rollback test:

```
Successfully deleted image: sha256:e6964a01...f14529
```

Two operational details worth knowing:

- ECR applies lifecycle actions **within 24 hours**, not immediately. "No events
  found" right after saving is expected, not a broken policy.
- Tag immutability does not block deletion. It prevents a tag being *repointed*
  at different bytes; removal is a separate permission, which is why this needed
  a human - the CI user deliberately cannot delete images.

## 4.4 Remaining work

| Item | Why it matters | Approach |
|---|---|---|
| Failure notification | A red run nobody sees did not happen | Webhook on `failure` **and** on rollback; a run that recovered still needs to be seen |
| Elastic IP (optional) | The dynamic public IPv4 invalidated a stored secret once already | Allocate and associate; same cost as the attached IPv4 |

### Ordering rationale

The security work came first because SSH was the only service open to the
world. Notifications come last because a pipeline that now recovers by itself
and fails loudly is less urgent to be told about than one that leaves the site
down.

---

## 4.5 Phase 4 exit

**Closed:** 19 November 2026

### What shipped, and how each claim was checked

| Change | Verified by |
|---|---|
| Automatic rollback | Deployed a deliberately unhealthy image on the real instance; site stayed up, previous version restored, run exited 1 |
| SSM deploy replaces SSH | Runs #18, #20, #21 green; container image on the instance matched `git HEAD` |
| Port 22 closed | External TCP probe to the public address: `22 open=false`, `80 open=true` |
| No credentials on the runner | The deploy job configures AWS credentials only for `ssm:SendCommand`; no key is written to disk |
| Command audit | Every deploy appears in AWS command history with stdout and stderr |
| ECR lifecycle | Two rules visible in the console after saving |

Every row was checked against the running system, not inferred from a green
badge. Where a check was impossible - the CI user cannot read ECR policy - it is
stated as unverified in the section above rather than assumed.

### Deliberately not done

| Omission | Reason |
|---|---|
| Failure notifications | One consumer, and the pipeline now recovers by itself and fails loudly. Worth adding the moment a second person depends on it - and when it is added, it must fire on rollback too, because a recovered run still means a defect shipped |
| Elastic IP | **Done** - allocated and associated; the address is now `15.252.179.238` and stable across restarts |
| Unit tests | The application is static; the artefact is tested instead. The workflow has the slot |
| Zero-downtime deploy | Requires a load balancer and a second instance - more cost than this project justifies |

### The lesson this phase produced

Not the Systems Manager migration itself. The four red runs that preceded it were
all caused by a cosmetic `--comment` argument exceeding a 100-character limit,
and they stayed invisible because the diagnostic built to expose the error
produced an annotation with an empty message, which GitHub silently discards.

Two mistakes stacked, each hiding the other. **When a diagnostic shows nothing,
suspect the diagnostic** - and prefer state that can be queried over state that
must be reported by a human.

### Final state of the system

```
push to main
   -> static checks (~5s)
   -> build + smoke test (~15s)
   -> push to ECR, tagged by commit SHA
   -> ssm:SendCommand to one instance
   -> pull, swap, health check
        healthy  -> exit 0, run green
        unhealthy -> restore previous image, exit 1, run red
   -> verify from the public internet
   -> guard: fail the run if the deploy did not happen
```

One reachable port. No key on disk. Every command recorded. A bad deploy costs
disruption, not an outage.
