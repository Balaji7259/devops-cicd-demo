# Contributing

This is a solo portfolio project, so it is not looking for feature contributions.
Corrections, questions and bug reports are genuinely welcome — particularly if
something here contradicts what the pipeline actually does.

## Before you open an issue

1. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — most "why is it done this
   way" questions are answered there.
2. Check the failure log in the [README](README.md#failure-log). Several
   non-obvious behaviours exist because of a specific incident, and the reason is
   recorded.
3. Check the known gaps section. A missing HTTPS setup is a decision, not a bug.

## One rule that matters more than the others

**A change to behaviour must come with a change to the documentation in the same
commit.** This repository's value is that the writing matches the system. A stale
comment is worse than no comment, because it is read as current — the deploy
script carried an "over SSH" comment for a phase after SSH was removed.

## Running the project locally

```bash
docker build -t devops-cicd-demo:local .
docker run -d --name devops-demo -p 8080:80 devops-cicd-demo:local
bash scripts/smoke-test.sh devops-cicd-demo:local 8080
```

The smoke test is the same script CI uses. If it passes locally and fails in CI,
the difference is the environment, not the code.

## Pull requests

- Keep the change narrow; one concern per pull request.
- Describe **what breaks if this is wrong**, not just what the change does.
- If you touch the workflow, say which job you ran to verify it.

## What would be accepted

- Typo and clarity fixes in documentation
- A failing test for a real bug
- Documentation of a failure mode not yet recorded
- Accessibility fixes in `site/`

## What would be declined

- Adding a framework to the static site
- Replacing Systems Manager with SSH
- Broadening an IAM policy to make an error go away
- Committing any credential, even a "temporary" one
