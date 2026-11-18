# Phase 3 — GitHub Actions Automation

**Status:** complete. A push to `main` reaches the public site with no manual step.
**Date:** 18 November 2026
**Repository:** https://github.com/Balaji7259/devops-cicd-demo

---

## Objective

Phase 2 proved the deployment *can* work when a human performs eleven commands.
Phase 3 removes the human. The success criterion was not "a workflow exists" but:
edit a file, push, observe the change on the public IP without touching a
terminal, Docker, or AWS.

That criterion was met on run #2 and re-proven on every run since.

---

## Pipeline structure

`.github/workflows/deploy.yml` — four jobs, sequential, one owner each.

| Job | Runtime | Purpose | Can use AWS credentials |
|---|---|---|---|
| `Static checks` | ~5s | Files exist, HTML balanced, `/healthz` contract intact | No |
| `Build, smoke test and push` | ~15s | Build locally → start → probe routes → push | Only after the probe passes |
| `Deploy to EC2` | ~14s | Pull, replace container, verify locally | No — uses the instance role |
| `Deployment guard` | ~3s | Fail the run if the deploy job didn't succeed | No |

Total wall clock: 40–55s.

### Design decisions and their reasons

**Image tag = full commit SHA, never `latest`.**
`latest` makes "what is deployed?" unanswerable and lets a cached image mask a
failed build. A SHA tag survives as long as the image does; rollback becomes a
lookup rather than a rebuild.

**ECR tag immutability, no exclusions.**
A tag can never point at different bytes. Combined with SHA tagging, a running
container is traceable to one commit forever.

**Build happens on the runner, never on EC2.**
`t3.micro` has ~909 MiB of RAM. Building there invites the OOM killer and mixes
build and runtime concerns on the box that serves traffic.

**No AWS credentials in the deploy job.**
The deploy step authenticates to ECR with the *instance's* role. CI can push
images but cannot act on the AWS account, so a compromised workflow has one
blast radius: one registry repository.

**`concurrency: deploy-production`, `cancel-in-progress: false`.**
Rapid pushes queue instead of racing for the same container name. Cancelling a
deploy mid-flight can leave the host without a container; queuing cannot.

**Health check before reporting success.**
The deploy step polls `/healthz` ten times, then dumps the last 50 log lines and
fails. Without it, a pipeline can be green while the site is down — the failure
mode that erodes trust in CI more than any other.

**Verification from the public internet, not just `localhost`.**
A local health check passes even when the security group blocks port 80. The
final step fetches the site over the public IP, which is the only check that
matches what a user experiences.

---

## Secrets

Four repository secrets, names case-sensitive, values write-only after saving.

| Secret | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` | CI user, push scope |
| `AWS_SECRET_ACCESS_KEY` | same |
| `EC2_HOST` | public IPv4 of the instance |
| `EC2_SSH_KEY` | full PEM contents, including BEGIN/END lines |

No secret is printed by any step, and none is passed to the deploy job's AWS
calls. `permissions: contents: read` keeps `GITHUB_TOKEN` from doing anything
beyond reading the repo.

---

## Rollback

Manual run with an `image_tag` input. The workflow then:

1. skips source validation (the source was validated when that image was built),
2. pulls the requested image from ECR,
3. runs the **same** `scripts/smoke-test.sh` a normal deploy must pass,
4. deploys it through the identical deploy step.

Sharing the smoke script matters: a rollback path that skips checks accumulates
bit-rot and fails when it is needed.

Validation accepts 7–40 hex characters because the earliest image in the
registry, `2b4b847`, was tagged by hand with a short SHA.

### Drill result — run #8

| Signal | Before | After |
|---|---|---|
| Image tag | `193bd00…` | `2b4b847` |
| Container started | 06:42:00Z | 06:44:06Z |
| Response size | 1336 bytes | 1281 bytes |
| Deploy stamp on page | present | absent |

Four independent signals moved together. A pipeline reporting success while the
container was untouched would have moved none of them.

---

## Run history

| # | Trigger | Commit / tag | Result | Note |
|---|---|---|---|---|
| 1 | push | `3d1eb6d` | success, 38s | first automated deploy, replaced the manual container |
| 2 | push | `75d484f` | success, 50s | deploy stamp visible on the public site |
| 3 | push | `ad9a1a2` | success, 41s | gates added: 5s / 15s / 14s |
| 4 | push | `5a219bd` | success, 53s | rollback mode added |
| 5 | dispatch `2b4b847` | — | **failure** | CI user lacked `ecr:GetDownloadUrlForLayer` |
| 6 | dispatch | — | **false green** | run succeeded; `Deploy to EC2` was silently skipped |
| 7 | push | `193bd00` | success, 53s | guard job active |
| 8 | dispatch `2b4b847` | — | success, 44s | rollback verified on the live site |

---

## Incidents

### 1. HTML validator rejected valid markup

The first version of the static check reported `site/index.html` as unbalanced:
`</meta> closes <head>`, `stray </link>`, `</img> closes <a>`.

The site was fine. Python's `HTMLParser` reports `<meta />` as a *self-closing*
event, which by default fires both a start and an end handler; the end handler
then saw a closer for a tag it never pushed.

Fixed by implementing `handle_startendtag` as a no-op and ignoring end events for
void elements. Caught by running the extracted step locally before pushing — the
alternative was a red run blaming the user's HTML.

### 2. Rollback could not pull — `ecr:GetDownloadUrlForLayer`

Run #5 failed at `Verify rollback image still serves the site`. Reproduced
directly against the API:

```
An error occurred (AccessDeniedException) when calling the GetDownloadUrlForLayer
operation: User: arn:aws:iam::576329196399:user/devops-cicd-ci is not authorized
to perform: ecr:GetDownloadUrlForLayer
```

The CI user had been scoped for pushing only. `BatchGetImage` let it read the
manifest; nothing let it read the layers. One read action added, still pinned to
the single repository ARN.

Worth noting: a normal push never pulls, so this gap was invisible to every
green run and would have surfaced during the first real incident.

### 3. Green run, nothing deployed

Run #6 reported **success** in 22s while EC2 kept running the old container for
another nine minutes. `Deploy to EC2` had been skipped.

Cause: `deploy` had no `if`, so it inherited the default `success()`, which
evaluates the **entire ancestor chain**. Rollback runs skip the `test` job, and a
skipped ancestor makes `success()` false. GitHub skips the job and reports the
run as green, because a skipped job is not a failure.

Fix: `if: always() && needs.build-and-push.result == 'success'`, plus a `guard`
job that fails the run whenever `deploy` did not succeed. The guard exists
because the underlying GitHub behaviour will not change and this class of bug is
invisible by construction.

### 4. PowerShell → SSH stdin corruption

During local validation, piping a script into `ssh ... bash -s` from PowerShell
prepended a UTF-8 BOM, producing `bash: line 1: set: command not found`. Not a
pipeline bug — the runner is bash end-to-end — but the fix for future local tests
is `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` before piping.

---

## Exit checklist

- [x] Push to `main` builds, tests and deploys without human action
- [x] Image tagged by commit SHA, immutable in ECR
- [x] Four secrets stored in GitHub, none in the repository
- [x] Deployment verified from the public internet, not only locally
- [x] Failed health check fails the run and dumps container logs
- [x] Rollback to a published image without rebuilding or reverting source
- [x] Rollback drill verified by image tag, container start time and page content
- [x] Every job that can fail, fails loudly
- [x] Documented: README, this record, Phase 1 and Phase 2 records

---

## Remaining risks

| Risk | Severity | Mitigation path |
|---|---|---|
| SSH open to `0.0.0.0/0` | Medium | Systems Manager `Send-Command`; removes port 22 entirely. 5,622 runner CIDRs vs a 60-rule limit makes whitelisting impossible |
| Access key instead of OIDC | Medium | Blocked by Free plan guardrails; revisit on account upgrade |
| No automatic rollback on failed health check | Medium | Capture the previous tag before replacement and redeploy it on failure |
| Downtime during replacement | Low | Second instance behind a load balancer |
| Unbounded ECR growth | Low | Lifecycle policy: expire untagged images after N days |
