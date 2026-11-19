# Security policy

## Reporting a vulnerability

This is a personal portfolio project, but it runs on a real AWS account, so a
real vulnerability is still worth reporting.

**Please do not open a public issue for a security problem.** Use GitHub's
private reporting instead: **Security → Report a vulnerability** on the
repository page. If that is unavailable, contact the maintainer directly through
the address on the GitHub profile linked from this repository.

Expect an acknowledgement within a few days. This is maintained by one person,
voluntarily.

## What is in scope

- The pipeline definition (`.github/workflows/`)
- The deploy logic (`scripts/deploy-remote.sh`) and its delivery mechanism
- IAM scoping and any path by which credentials could be obtained or widened
- The live host at the address in the README

## What is deliberately out of scope

These are known and documented, not vulnerabilities to be reported:

| Observation | Status |
|---|---|
| No HTTPS — the site is served over plain HTTP on port 80 | Known gap, prioritised as the next improvement |
| A long-lived IAM access key exists for CI | Documented compromise; OIDC is blocked by the account plan ([details](docs/PHASE-3-GITHUB-ACTIONS.md)) |
| The site is a static page with no authentication | By design — there is nothing to log in to |
| No WAF, rate limiting or DDoS protection | Out of scope for a demo on a free plan |

## How this repository handles secrets

- No credential is ever committed. `.gitignore` covers `.env`, `*.pem` and `*.key`.
- CI credentials live only in GitHub encrypted secrets, which are write-only.
- The EC2 instance holds **no** credential: it assumes a role and receives
  short-lived credentials through instance metadata.
- If a secret is ever committed by accident, the response is: rotate the
  credential first, then rewrite history. Rotating is cheap here precisely
  because the permission set is small.

## The security posture in one sentence

Two identities exist, and neither can delete anything: the CI user can push and
read images in one repository and send one command to one instance, and the
server can only pull from that same repository.
