# Phase 4 — Hardening

**Started:** 18 November 2026
**State:** in progress — item 1 shipped and verified, three items remain.

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

## 4.2 Remaining work

| Item | Why it matters | Approach |
|---|---|---|
| Replace SSH with Systems Manager | Port 22 is open to `0.0.0.0/0` because GitHub's 5,622 runner ranges cannot be whitelisted into a 60-rule security group | `ssm:SendCommand` using the instance role; attach `AmazonSSMManagedInstanceCore`; remove the SSH rule and the key from GitHub entirely |
| ECR lifecycle policy | Untagged layers accumulate with every build | Expire untagged images after 14 days; keep tagged ones |
| Failure notification | A red run nobody sees did not happen | Webhook on `failure` and on `rollback occurred` |

### Ordering rationale

SSH first. It is the only open-to-the-world service left, and it removes two
long-lived secrets (the private key and the ability to reach the box at all).
Notifications last, because a pipeline that recovers by itself is less urgent to
be told about than one that leaves the site down.
