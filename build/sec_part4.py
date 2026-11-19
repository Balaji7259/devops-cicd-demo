"""Part 4 - the automation itself."""
import os

from reportlab.platypus import PageBreak

from pdf_lib import (P, H1, H2, H3, bullet, callout, cmd_table, code_block,
                     figure, grid_table)

DIAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")


def part4():
    out = []
    out += H1("4", "Phase 3 - Making It Automatic", "Part four")
    out += [
        P("Goal: replace the eleven manual steps with a push. The pipeline must also refuse to ship a "
          "broken image, prove the deploy actually happened, and allow going back to an older image "
          "without rebuilding anything.", "lead"),

        H2("4.1", "Six words that make GitHub Actions readable"),
        grid_table(
            [["Workflow", "One YAML file in .github/workflows/. Here: deploy.yml."],
             ["Event", "What starts it. Here: a push to main, and a manual trigger."],
             ["Runner", "A fresh Ubuntu virtual machine that GitHub provides for the job, then deletes."],
             ["Job", "A group of steps that run on one runner. Jobs run in parallel unless wired together."],
             ["Step", "One command or one prebuilt action. Steps in a job run in order and share a filesystem."],
             ["Secret", "An encrypted value injected as an environment variable. Readable by the workflow, "
                        "never viewable again in the UI."]],
            ["Term", "Meaning"], widths=[0.18, 0.82]),
        P("Two mechanics matter more than they look. <b>needs:</b> makes one job wait for another, which is "
          "how the pipeline becomes a sequence. <b>concurrency:</b> prevents two pushes from deploying at the "
          "same time - here it queues rather than cancels, because cancelling a deploy halfway can leave the "
          "server with no container at all."),

        H2("4.2", "The four secrets"),
        P("Repository settings - Secrets and variables - Actions - New repository secret. Names are "
          "case-sensitive and must match the workflow exactly."),
        grid_table(
            [["AWS_ACCESS_KEY_ID", "The CI user's key id"],
             ["AWS_SECRET_ACCESS_KEY", "The CI user's secret"],
             ["EC2_HOST", "13.126.168.131"],
             ["EC2_SSH_KEY", "The entire .pem file, including the BEGIN and END lines"]],
            ["Secret", "Value"], widths=[0.28, 0.72]),
        callout("A pasted SSH key that is missing its BEGIN/END lines fails with a bare 'invalid format' error "
                "and no further explanation. Copy the whole file with "
                "<i>Get-Content key.pem -Raw | Set-Clipboard</i> rather than selecting it by hand.", "warn"),

        H2("4.3", "The pipeline at a glance"),
        grid_table(
            [["1  Static checks", "~5 s", "Files present, HTML balanced, health contract intact", "No"],
             ["2  Build + smoke test", "~15 s", "Build locally, start it, fetch five routes, then push", "Only after the test"],
             ["3  Deploy to EC2", "~14 s", "SSH, pull, replace container, health check", "No - uses the instance role"],
             ["4  Deployment guard", "~3 s", "Fail the run if the deploy did not actually happen", "No"]],
            ["Job", "Time", "What it proves", "AWS credentials"],
            widths=[0.24, 0.1, 0.44, 0.22]),

        H2("4.4", "Job 1 - the cheap checks"),
        code_block("""  test:
    name: Static checks
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify required files exist
        run: |
          for f in Dockerfile site/index.html site/about.html \\
                   site/style.css site/assets/logo.svg scripts/smoke-test.sh; do
            [ -f "$f" ] || { echo "::error::Required file missing: $f"; exit 1; }
          done

      - name: Validate HTML structure
        run: python3 - <<'PY'
          ... an HTMLParser that checks every tag closes ...
          PY""", "job 1, abbreviated"),
        P("This job deliberately costs almost nothing and runs before any credential is used. A missing file "
          "or an unclosed tag fails in five seconds instead of after a two-minute build."),
        callout("The first version of this check rejected the site's own HTML - it reported "
                "<i>&lt;/meta&gt; closes &lt;head&gt;</i> for perfectly valid markup, because "
                "<i>&lt;meta /&gt;</i> arrives at the parser as a self-closing event rather than as a start tag. "
                "The fix was to handle that event explicitly. Found by running the check locally before pushing it, "
                "which is cheaper than debugging a red run.", "danger"),

        H2("4.5", "Job 2 - build, test, then publish"),
        code_block("""      - name: Build image
        id: build
        run: |
          LOCAL_TAG="devops-cicd-demo:${GITHUB_SHA}"
          docker build --tag "${LOCAL_TAG}" .

      - name: Smoke test the built image
        run: bash scripts/smoke-test.sh "${LOCAL_TAG}" 8080

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          ...

      - name: Push image
        run: |
          PUSH_URI="${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}"
          docker tag "${LOCAL_TAG}" "${PUSH_URI}"
          docker push "${PUSH_URI}"
""", "job 2, abbreviated"),
        P("The order is the whole point. The image is built under a <b>local</b> name, started, and probed. "
          "AWS credentials are configured <i>after</i> that passes, so a broken image never reaches the "
          "registry and can never replace the running site."),
        P("<i>scripts/smoke-test.sh</i> starts the container, waits for the health endpoint, then fetches five "
          "routes and asserts that the body of <i>/healthz</i> is exactly <b>ok</b>. The same script is reused "
          "for rollback, so an old image cannot bypass a check a new one must pass."),

        H2("4.6", "Job 3 - deploy, with no AWS credentials at all"),
        code_block("""          ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=yes \\
              "ubuntu@${EC2_HOST}" \\
              "IMAGE_URI='${IMAGE_URI}' CONTAINER='devops-demo' REGION='ap-south-1' bash -s" <<'REMOTE'
          set -euo pipefail
          REGISTRY="${IMAGE_URI%%/*}"
          aws ecr get-login-password --region "$REGION" \\
            | docker login --username AWS --password-stdin "$REGISTRY"
          docker pull "$IMAGE_URI"
          docker rm -f "$CONTAINER" 2>/dev/null || true
          docker run -d --name "$CONTAINER" -p 80:80 --restart unless-stopped "$IMAGE_URI"

          for attempt in $(seq 1 10); do
            curl -fsS http://localhost/healthz && exit 0
            sleep 2
          done
          docker logs "$CONTAINER" --tail 50 >&2
          exit 1
          REMOTE""", "job 3, the remote script"),
        cmd_table([
            ("-o StrictHostKeyChecking=yes", "Refuse to connect if the server's host key is not already known. "
                                             "Combined with ssh-keyscan in the previous step, this pins the server "
                                             "instead of trusting whatever answers that IP."),
            ("<<'REMOTE' ... REMOTE", "Send a multi-line script to the remote bash. Quoting the marker keeps the "
                                      "local shell from expanding variables that must be expanded remotely."),
            ("${IMAGE_URI%%/*}", "Cut the registry host off the front of the image name - the form docker login needs."),
            ("docker rm -f ... || true", "Remove the old container. '|| true' stops the first-ever deploy from "
                                         "failing because there was nothing to remove."),
            ("for attempt in $(seq 1 10)", "Poll the health endpoint for up to twenty seconds. If it never answers, "
                                           "dump the last fifty log lines and fail the job."),
        ], ("Piece", "Why it is there")),
        callout("Notice what is missing from this job: no AWS keys. The runner logs in over SSH, and the "
                "<i>server's own role</i> obtains the registry password. The blast radius of a stolen workflow "
                "is therefore limited to the container repository, not the AWS account.", "good"),

        H2("4.7", "Job 4 - the guard, and the worst bug in the project"),
        P("GitHub reports a run as <b>green</b> when a job is skipped, not only when it succeeds. That produced "
          "a run which showed success while deploying absolutely nothing."),
        code_block("""  deploy:
    needs: build-and-push
    # NOT the default success(): a rollback run skips the `test` job, and a
    # skipped ancestor makes success() false - so this job was silently skipped.
    if: always() && needs.build-and-push.result == 'success'

  guard:
    needs: [build-and-push, deploy]
    if: always()
    steps:
      - name: Fail unless the deploy job actually ran
        if: needs.deploy.result != 'success'
        run: |
          echo "::error::Deployment did not happen"
          exit 1""", "the fix and the guard"),
        P("Two separate lessons. First, a job's default condition considers its <b>entire ancestor chain</b> - "
          "so a skipped job early in the graph quietly disables everything downstream. Second, a pipeline that "
          "can report success without doing anything is worse than one that crashes, because nobody investigates "
          "a green run. The guard job exists to make that impossible."),

        H2("4.8", "The gates, and what each one stops"),
    ]
    out.append(figure(os.path.join(DIAG, "d6_gates.png"), 16.2,
                      "Gates are ordered cheapest first, so the expensive failures are rare."))
    out += [
        H2("4.9", "What actually happened, run by run"),
        grid_table(
            [["1", "push 3d1eb6d", "success 38s", "First automated deploy; replaced the manual container"],
             ["2", "push 75d484f", "success 50s", "A visible text change reached the public site"],
             ["3", "push ad9a1a2", "success 41s", "Three gates added; jobs 5s / 15s / 14s"],
             ["4", "push 5a219bd", "success 53s", "Rollback mode added"],
             ["5", "dispatch 2b4b847", "FAILURE", "CI user could not download image layers"],
             ["6", "dispatch", "false green", "Deploy job skipped; run still reported success"],
             ["7", "push 193bd00", "success 53s", "Guard active"],
             ["8", "dispatch 2b4b847", "success 44s", "Rollback verified on the live site"],
             ["10", "push 273f415", "success 51s", "Documentation shipped through the pipeline it documents"]],
            ["#", "Trigger", "Result", "What it established"],
            widths=[0.06, 0.2, 0.17, 0.57]),
        P("Runs 5 and 6 are the two most valuable runs in the list. Everything else confirms that the happy path "
          "works; those two found bugs that would otherwise have appeared during an incident."),

        H2("4.10", "Rollback without rebuilding"),
        P("Rolling back means deploying an image that already exists in the registry. The workflow accepts an "
          "optional <i>image_tag</i>; when it is supplied, the build and push are skipped, the image is pulled, "
          "smoke tested with the same script, and deployed by the same step."),
    ]
    out.append(figure(os.path.join(DIAG, "d7_rollback.png"), 15.8,
                      "Forward is automatic; backward is one dropdown and a commit hash."))
    out += [
        cmd_table([
            ("Actions ... Build, Test and Deploy", "Open the workflow in GitHub."),
            ("Run workflow", "Manual trigger. Branch main, image_tag left empty builds from source as usual."),
            ("image_tag = 2b4b847", "Deploy that exact image instead. Seven to forty hex characters, because the "
                                    "oldest images were tagged by hand with a short SHA."),
        ], ("Step", "What it does")),
        P("The drill was verified with four independent signals rather than the green badge:"),
        grid_table(
            [["Image tag", "193bd00...", "2b4b847"],
             ["Container started", "06:42:00Z", "06:44:06Z"],
             ["Response size", "1336 bytes", "1281 bytes"],
             ["Deploy stamp in page", "present", "absent"]],
            ["Signal", "Before", "After"], widths=[0.36, 0.3, 0.34]),
        P("All four had to move for the rollback to be genuine. A pipeline that reports success while the "
          "container is untouched moves none of them - which is exactly what run 6 did."),

        H2("4.11", "The four failures worth remembering"),
        grid_table(
            [["Push authenticated but 401 on upload", "The CI user had pull permissions", "Added the four upload actions and PutImage"],
             ["All layers uploaded, then 403", "docker push verifies what it wrote", "Added ecr:BatchGetImage"],
             ["Rollback run green, nothing deployed", "Default success() is poisoned by a skipped ancestor", "Explicit result check plus a guard job"],
             ["Rollback failed on docker pull", "CI user could push but not read layers", "Added ecr:GetDownloadUrlForLayer"]],
            ["Symptom", "Cause", "Fix"], widths=[0.34, 0.34, 0.32]),
        P("Three of the four are the same shape: a permission that only a <b>new code path</b> needs. Pushing "
          "never pulls, so the gap was invisible to every green run. That is the argument for adding the "
          "rollback drill to a project like this instead of assuming it works."),

        H2("4.12", "Checkpoint"),
        bullet("a push to main deploys without any manual step"),
        bullet("the image in ECR is tagged with the commit that produced it"),
        bullet("the workflow fails loudly if the site does not answer over the internet"),
        bullet("a rollback to an older image works and is visible on the public URL"),
        bullet("no credential appears anywhere in the repository"),
        PageBreak(),
    ]
    return out
