# Automated CI/CD Deployment Pipeline using AWS and Docker

Project plan, architecture and roadmap. Read this once before touching a
terminal — every later decision refers back to it.

---

## 1. What we are building

A repository that deploys itself. You `git push`, and roughly two minutes
later the live site on an AWS EC2 instance is running your new code, with no
SSH, no `scp`, no manual `docker pull`.

The value is not the website. The value is the pipeline, and your ability to
explain why each link in it exists.

---

## 2. Architecture

```
Developer
   |  git push
   v
GitHub Repository (source of truth)
   |  webhook triggers workflow
   v
GitHub Actions runner (temporary Ubuntu VM)
   |-- checkout code
   |-- run tests           <-- fail here and nothing else happens
   |-- docker build
   |-- docker push --------> Amazon ECR (private image registry)
   |
   |  OIDC: assume IAM role, no stored AWS keys
   v
SSH command to EC2 (private key held in GitHub Secrets)
   |
   v
EC2 instance (Ubuntu)
   |-- docker login to ECR  (via its IAM instance role)
   |-- docker pull  :<git-sha>
   |-- docker stop/rm old container
   |-- docker run new container
   v
Nginx container  ->  Security group  ->  Public HTTP  ->  User
```

### The trust chain, in plain words

| Hop | How it is authorised | Why it is safe |
|---|---|---|
| GitHub Actions to AWS | OIDC token exchanged for short-lived STS credentials | No long-lived access key ever exists on GitHub. Trust is scoped to one repo and one branch. |
| Actions to EC2 | SSH key stored as a GitHub encrypted secret, source IP locked to the runner | The runner's IP is dynamic, so the EC2 security group must be opened to the runner — or, better, deployment goes through SSM. We start with SSH and note the trade-off. |
| EC2 to ECR | IAM instance profile attached to the instance | The instance has pull rights only. No keys on disk. |
| User to app | Security group allows 80 from 0.0.0.0/0 | A public website. Port 22 is restricted to your own IP. |

### Core design decisions (and the reasoning)

1. **Immutable tags.** Every image is tagged with the Git commit SHA, plus
   `latest` as a convenience alias. Deploying `:latest` is what makes
   rollbacks guesswork; deploying `:<sha>` means rolling back is "run the
   previous SHA".
2. **Build once, promote.** The image that was tested is the exact image
   that runs. No rebuild on the server.
3. **The server is cattle.** EC2 is provisioned by a script, the container is
   disposable, and state lives in ECR plus Git. Nothing is hand-edited on the
   box that you cannot recreate.
4. **Fail early.** Tests run before the build and before the push. A red
   pipeline never reaches ECR, so a bad image can never reach production.
5. **No secrets in the repo.** OIDC for AWS, GitHub Secrets for SSH, IAM roles
   on the instance. `.gitignore` blocks keys before the first commit.

---

## 3. Prerequisites

### Accounts
- A GitHub account.
- An AWS account with billing alerts configured (do this before creating
  anything that costs money).

### Local machine (Windows 11 assumed)
- Windows 10/11 64-bit with virtualisation enabled in BIOS.
- WSL2 — Docker Desktop needs it as its backend on Windows.
- ~15 GB free disk for images and the WSL2 disk.
- PowerShell 7 (already present in this environment) or Windows PowerShell 5.1.

### Knowledge assumed
- Creating folders, editing files, running commands in PowerShell.
- What a commit and a branch are.
- Nothing about Docker, AWS or CI/CD — those get explained as they appear.

### Not used, deliberately
Kubernetes, Terraform, Jenkins, ArgoCD, Helm, Ansible. They are all correct
tools for larger problems and all of them would hide the mechanics you are
trying to learn here. One box, one container, one pipeline.

---

## 4. Roadmap

| Phase | Days | Focus | Exit criterion |
|---|---|---|---|
| 1. Local environment | 1–2 | Docker, Git, the app, the Dockerfile | `docker run` serves the page from your own image |
| 2. AWS infrastructure | 3–4 | IAM, ECR, EC2, security groups, manual deploy | The same image runs on EC2, deployed by hand |
| 3. CI/CD pipeline | 5–7 | OIDC, build/test/push workflow, automated deploy | A `git push` updates the live site |
| 4. Validation and rollback | 8–9 | Failure injection, rollback, smoke tests | You can break it on purpose and recover |
| 5. Documentation | 10–12 | README, diagrams, screenshots, resume wording | A stranger can reproduce the project from the README |

### Phase 1 detail
- **Day 1** — Install and verify Git, Docker Desktop, WSL2. Create the repo
  and the Nginx app. Write the Dockerfile. Build and run locally.
- **Day 2** — Understand what you just built: image layers, caching,
  `docker ps` vs `docker images`, container lifecycle, `.dockerignore`,
  tagging strategy, pushing to GitHub.

### Phase 2 detail
- **Day 3** — AWS account hygiene (MFA, budget alarm), IAM user for the
  console only, ECR repository, first manual `docker push` from your laptop.
- **Day 4** — Launch Ubuntu 24.04 EC2, security groups, SSH from Windows,
  install Docker, pull from ECR using the instance role, run the container.

### Phase 3 detail
- **Day 5** — GitHub OIDC provider, IAM role with a trust policy scoped to
  your repo, least-privilege ECR permissions, secrets and variables.
- **Day 6** — Workflow that lints, tests, builds, tags with the SHA, pushes
  to ECR, and reports the digest.
- **Day 7** — Deploy job: SSH to EC2, pull the exact SHA, replace the
  container, health check, fail the workflow if the check fails.

### Phase 4 detail
- **Day 8** — Validation: change content, push, watch the pipeline, confirm
  ECR digest and live version match. Screenshot everything for the README.
- **Day 9** — Failure handling: break a test, confirm the pipeline blocks.
  Roll back by redeploying the previous SHA. Discuss `latest` drift.

### Phase 5 detail
- **Day 10** — Architecture diagrams (draw them yourself; a diagram you
  cannot draw from memory is a diagram you do not understand).
- **Day 11** — README: prerequisites, setup, secrets table, troubleshooting
  table, screenshots.
- **Day 12** — Resume bullets, interview answers, "what I would improve next".

---

## 5. Cost control

Everything here fits inside a small budget, but only if you are deliberate.

- Use one region for everything (Mumbai / `ap-south-1` if you are in India).
  Cross-region data transfer costs money for no benefit.
- `t3.micro` (or `t2.micro` where available) is enough. **Stop the instance**
  when you are not working; a stopped instance does not bill compute.
- ECR stores images by the gigabyte-month. Add a lifecycle policy that
  expires untagged images after 7 days — this is also a real production
  practice, not just a cost trick.
- Do not create a NAT Gateway. It is the single most common surprise charge
  in beginner AWS projects.
- Set a billing alarm at a low threshold on day one.

---

## 6. Security checklist

Tick these off as you go; they are what an interviewer will probe.

- [ ] No AWS access key anywhere in the repository, ever.
- [ ] GitHub Actions authenticates to AWS via OIDC, not static keys.
- [ ] The OIDC trust policy is scoped to `repo:<owner>/<repo>:ref:refs/heads/main`.
- [ ] IAM policy for CI grants only `ecr:GetAuthorizationToken` plus
      push actions on the one repository.
- [ ] EC2 instance role grants only ECR pull, not push.
- [ ] SSH (port 22) restricted to your IP, not `0.0.0.0/0`.
- [ ] Only ports 80 (and later 443) open to the internet.
- [ ] EC2 root volume encrypted; IMDSv2 required.
- [ ] Private key in GitHub Secrets; never committed, never pasted in chat.
- [ ] Billing alarm configured.

---

## 7. Definition of done

The project is finished when all of these are true:

1. `git push origin main` triggers a green workflow with no manual input.
2. The live page shows the new content within a couple of minutes.
3. `aws ecr describe-images` shows an image tagged with that commit SHA.
4. A deliberately broken test turns the workflow red and the live site is
   untouched.
5. Redeploying an older SHA restores the older page.
6. The README lets someone else rebuild the whole thing from scratch.
7. You can draw the architecture on a whiteboard and defend each arrow.

---

## 8. Ground rules for this project

- One phase at a time. Do not read ahead and start typing.
- Every command gets pasted only after you understand what it does.
- When something fails, we debug the actual error text — never "just retry".
- If a step's expected output differs from what you see, stop and say so.
  Silent divergence becomes a mystery three days later.
