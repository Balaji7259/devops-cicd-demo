# Phase 2 — AWS Baseline (Manual Deployment)

Status: **complete**. Verified 18 Nov 2026.
Goal: prove the application runs on AWS before any automation exists.

---

## 1. Resources created

| Resource | Name / Identifier | Notes |
|---|---|---|
| AWS account | `576329196399` (`balaji_42`) | Free plan, USD 119.99 credit, ends 23 Apr 2027 |
| Region | `ap-south-1` (Mumbai) | Single region for every resource |
| ECR repository | `devops-cicd-demo` | Immutable tags, scan-on-push, AES-256 |
| ECR URI | `576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo` | |
| EC2 instance | `devops-cicd-server` | `t3.micro`, Ubuntu 24.04.5 LTS, gp3 8 GiB |
| Security group | `devops-cicd-sg` | 22 from My IP, 80 from 0.0.0.0/0 |
| Key pair | `devops-cicd-key` | Local: `C:\Users\BALAJI\.ssh\devops-cicd-key.pem` |
| IAM role (EC2) | `ecr-pull-devops-cicd-demo` | Pull-only, attached via instance profile |
| IAM user (CI) | `devops-cicd-ci` | Programmatic only, no console login |
| IAM managed policies | `ecr-pull-devops-cicd-demo`, `ecr-push-devops-cicd-demo` | Scoped to the single repository ARN |

Access key for `devops-cicd-ci` is stored outside the repo (password manager / GitHub
Secret in Phase 3). `.aws/credentials` lives in the Windows user profile.

---

## 2. Security model

**EC2 authenticates as a role, not a user.**

```
arn:aws:sts::576329196399:assumed-role/ecr-pull-devops-cicd-demo/i-01c13546bb8b4b707
```

Credentials are injected through instance metadata and rotate automatically. Nothing
usable is written to the instance disk, so a stolen snapshot or a shell on the box yields
no long-lived AWS secret.

**Pull policy — EC2 role:**

| Action | Resource |
|---|---|
| `ecr:GetAuthorizationToken` | `*` (AWS does not support scoping this call) |
| `ecr:BatchCheckLayerAvailability` | repo ARN |
| `ecr:BatchGetImage` | repo ARN |
| `ecr:GetDownloadUrlForLayer` | repo ARN |

Proven negative test — listing repositories is refused:

```
AccessDeniedException ... not authorized to perform: ecr:DescribeRepositories
```

**Push policy — CI user:**

`GetAuthorizationToken`, `BatchCheckLayerAvailability`, `InitiateLayerUpload`,
`UploadLayerPart`, `CompleteLayerUpload`, `PutImage`, `BatchGetImage` — all scoped to the
repository ARN. No delete actions anywhere, so a leaked CI key cannot destroy the registry.

**Known limitation — OIDC unavailable.**

GitHub Actions should assume a role via OIDC rather than storing a key. This account
cannot do that: an AWS-managed SCP denies `iam:*Provider*`, so no OIDC provider can be
created. The same denial exists on the Paid plan; only "Activate advanced features"
lifts it, which is irreversible.

Consequence: a scoped IAM user access key is used for CI. Mitigations — actions limited
to image push into one repository, key stored only as a GitHub Secret, rotation trivial
(delete key, create new one).

**Not done, deliberately:** no 0.0.0.0/0 on port 22, no access keys on the instance, no
secrets in the repository, no `AdministratorAccess` on anything.

---

## 3. Manual deployment procedure (verified)

On the instance:

```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin \
    576329196399.dkr.ecr.ap-south-1.amazonaws.com

docker pull 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847

docker run -d --name devops-demo -p 80:80 --restart unless-stopped \
  576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847
```

From Windows (build → tag → push):

```powershell
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 576329196399.dkr.ecr.ap-south-1.amazonaws.com
docker tag devops-cicd-demo:v1 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847
docker push 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847
```

Image tag `2b4b847` = Git commit `2b4b84701a073a7053dc568794f12039bee65bac`.
Manifest digest: `sha256:31e36a6b1b01c78ee6ddeae8245d04d79f8a375352154039c6b6e0650b86e2c3`.

---

## 4. Verification evidence

| Check | Result |
|---|---|
| `docker ps` | `devops-demo` up, `0.0.0.0:80->80/tcp` |
| `curl http://localhost/healthz` | `ok` |
| External `GET /` (from outside AWS network) | `200`, `Server: nginx/1.27.5`, title `DevOps CI/CD Demo` |
| External `GET /healthz` | `200`, body `ok` |
| Reboot test | `uptime` 4 min, container `Up 3 minutes` with no manual action |
| `aws sts get-caller-identity` on EC2 | `assumed-role/...`, not `user/...` |

The reboot test is the one that distinguishes a deployment from a manually started
process: `--restart unless-stopped` brought the container back unaided.

---

## 5. Troubleshooting log (real failures hit during Phase 2)

| Symptom | Root cause | Fix |
|---|---|---|
| `error during connect ... dockerDesktopLinuxEngine` | Docker Desktop engine not running | Start Docker Desktop, wait for "Engine running" |
| `not authorized to perform: ecr:InitiateLayerUpload` | Pull policy attached to the CI user instead of the push policy | Attach `ecr-push-devops-cicd-demo` |
| Push uploads all layers, then `HEAD .../manifests/...: 403 Forbidden` | Push policy lacked read access needed to verify the manifest it wrote | Add `ecr:BatchGetImage` |

Method that resolved both IAM errors: read the operation named in the error, add exactly
that action, retry. Never widen to a managed policy to silence the message.

---

## 6. Cost

| Item | Rate (approx) | Monthly |
|---|---|---|
| `t3.micro` on-demand | ~$0.0112/h | ~$8.18 |
| EBS gp3 8 GiB | ~$0.08/GB-month | ~$0.64 |
| Public IPv4 | $0.005/h | ~$3.65 |
| ECR storage (~74 MB) | ~$0.10/GB-month | ~$0.01 |
| **Running total** | | **~$12.5** |

Stopped (not terminated): ~$0.65/month — compute and public IPv4 stop, the disk remains.
All costs draw from the Free-plan credit; no cash charges are possible on this plan.
The account itself closes on **23 Apr 2027** unless upgraded to the Paid plan.

---

## 7. Screenshots to capture (Phase 5 evidence)

- EC2 instance list showing `devops-cicd-server` — Running, 2/2 checks
- Security group `devops-cicd-sg` inbound rules
- IAM role trust + inline policy JSON
- ECR repository showing image tag `2b4b847` with scan results
- `docker ps` on the instance
- Browser at the public URL, address bar visible

---

## 8. What Phase 3 replaces

Every manual command above becomes pipeline work:

| Manual step | Automation |
|---|---|
| `docker build` | GitHub Actions build job |
| `docker tag` with commit SHA | computed from `$GITHUB_SHA` |
| `docker push` | `aws-actions/configure-aws-credentials` + push |
| `docker pull` + `docker run` on EC2 | deploy job over SSH |

Note on the identity used by CI: `configure-aws-credentials` supports OIDC and static
keys; this account can only use the latter.
