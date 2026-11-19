"""Part 5 - understanding, cost, limits, and appendices."""
import os
import textwrap

from reportlab.platypus import PageBreak, Spacer

from pdf_lib import (P, H1, H2, H3, bullet, callout, cmd_table, code_block,
                     grid_table)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def part5():
    out = []
    out += H1("5", "Understanding What Was Built", "Part five")
    out += [
        H2("5.1", "So how is continuous integration actually achieved?"),
        P("Not by writing a clever script. By arranging four things so that none of them can lie to you:"),
        bullet("<b>A single trigger.</b> A push to <i>main</i> is the only way production changes. No human has "
               "a deploy button that bypasses the checks; the manual trigger runs the same checks."),
        bullet("<b>Checks that inspect the artefact, not the source.</b> The HTML validator reads the files, but "
               "the smoke test starts the actual container and fetches the actual routes. That is what catches a "
               "broken COPY, a wrong path, or a missing asset - things a source-level check cannot see."),
        bullet("<b>A build that cannot skip ahead.</b> The image is built under a local name and only receives the "
               "registry name after it has served traffic successfully. There is no code path where a failing "
               "image is published."),
        bullet("<b>Verification after the fact.</b> After deploying, the pipeline fetches the site over the public "
               "internet. This is the step that catches a mistake the earlier gates cannot - a security group that "
               "blocks visitors while the server itself is perfectly healthy."),
        Spacer(1, 4),
        P("The word <i>continuous</i> is then a property of the trigger, not of the code: because every push runs "
          "the same pipeline, integration is continuous by construction. The pipeline is the only path to "
          "production, so there is nothing to forget."),
        callout("The pipeline is not trusted because it is green. It is trusted because each gate checks something "
                "different, and because a run that skips work is made to fail. Those two properties took four "
                "attempts and two real bugs to get right - which is the normal amount.", "good"),

        H2("5.2", "How EC2 is used, precisely"),
        P("The instance is not a build machine, a database host, or a general-purpose server. It has exactly one "
          "job: run one container and keep it running."),
        grid_table(
            [["What runs on it", "Docker Engine, one container (nginx serving static files), the AWS CLI, and nothing else of consequence."],
             ["How it gets code", "It never sees the source. It receives an image from ECR, by tag."],
             ["How it authenticates", "An IAM role attached to the instance. No key file, no aws configure, credentials rotate automatically."],
             ["What reaches it", "Port 22 from the internet (for deploys) and port 80 from anywhere (for visitors)."],
             ["What survives a reboot", "The container restarts because of --restart unless-stopped; Docker itself starts at boot because it is a systemd service."],
             ["What it costs", "About $12.50 a month running; about $0.65 stopped, for the disk alone."]],
            ["Aspect", "Detail"], widths=[0.24, 0.76]),
        H3("Why the instance does not build the image"),
        P("A t3.micro has roughly 900 MiB of usable RAM. A Docker build is memory-hungry - layer extraction, "
          "compression, parallel stages - and the out-of-memory killer does not ask politely. Beyond memory, "
          "building on the server couples two concerns: a build failure would take down the machine that serves "
          "traffic. The runner is disposable and has 7 GB; the server is permanent and has 1 GB. Use each for "
          "what it is good at."),
        H3("Why the container is replaced rather than updated"),
        P("Containers are immutable by design. There is no 'upgrade in place' - the old container is removed and a "
          "new one starts from the new image. That is a feature: the running state is always exactly the image, "
          "never a mixture of old and new files. The cost is a second or two of downtime between the two "
          "commands, which is why this is described as continuous deployment, not zero-downtime deployment."),

        H2("5.3", "The security decisions, including the compromise"),
        grid_table(
            [["Server credentials", "IAM role, never a key file", "Nothing to leak from the disk; rotation is automatic"],
             ["CI credentials", "Access key scoped to one repository", "Only possible option under the Free plan"],
             ["Blast radius", "Push and pull only, one repo, no deletes", "A stolen key adds images; it cannot destroy anything"],
             ["SSH", "Key-only, no passwords", "No brute-force surface, but currently reachable from any address"],
             ["Image integrity", "Immutable tags, scan on push", "A tag can never point at different bytes"],
             ["Repository hygiene", "Secrets in GitHub, .gitignore for keys", "No credential has ever been committed"]],
            ["Control", "Implementation", "What it buys"], widths=[0.22, 0.34, 0.44]),
        H3("The OIDC compromise, stated plainly"),
        P("The correct way for GitHub to authenticate to AWS is OIDC: AWS trusts GitHub's identity provider, and "
          "each workflow run receives short-lived credentials. No secret exists to steal."),
        P("This account is on AWS's Free plan, whose guardrails deny <i>iam:*Provider*</i>. The OIDC provider "
          "cannot be created, so the project uses a scoped IAM access key stored in GitHub secrets instead. "
          "It is the weaker option, and the mitigation is tight scoping: one repository, no deletes, no EC2, "
          "no IAM. The path forward is a single change in <i>configure-aws-credentials</i> once the provider "
          "exists - <i>role-to-assume</i> instead of two keys."),
        callout("Say this out loud in an interview rather than hoping nobody asks. Choosing a documented, scoped "
                "workaround because the platform blocks the ideal solution is senior behaviour; pretending the "
                "workaround is ideal is not.", "good"),

        H2("5.4", "What it costs, and what would cost more"),
        grid_table(
            [["EC2 t3.micro, running", "~$7.50 / month", "Compute while the instance is on"],
             ["Public IPv4", "~$3.60 / month", "Charged whenever an address is attached"],
             ["EBS 8 GiB gp3", "~$0.65 / month", "Charged whether running or stopped"],
             ["ECR storage", "cents", "A handful of ~20 MB images"],
             ["GitHub Actions", "$0", "Free minutes cover this by a wide margin"],
             ["Total running / stopped", "~$12.50 / ~$0.65", "Paid from existing AWS credits"]],
            ["Item", "Approximate", "Notes"], widths=[0.32, 0.24, 0.44]),
        P("Two things would change the bill materially: a second instance behind a load balancer (for "
          "zero-downtime), and a NAT gateway if the instance were ever moved into a private subnet - the latter "
          "costs more per month than this entire project does."),

        H2("5.5", "What is deliberately missing"),
        grid_table(
            [["Automatic rollback", "Medium", "Capture the running tag before replacing; on a failed health check, restart it. "
              "Turns 'the pipeline tells you' into 'the pipeline recovers'."],
             ["SSH exposed to the internet", "Medium", "Replace SSH with SSM Send-Command: no port 22, no key in GitHub."],
             ["No unit tests", "Low here", "A static site has nothing to unit test; a real app would add them before the build step."],
             ["Single instance, brief downtime", "Low", "Two instances behind a load balancer, or a blue/green swap."],
             ["Unbounded ECR growth", "Low", "A lifecycle policy expiring untagged images after 14 days."],
             ["No failure notification", "Low", "A webhook on failure - a red run nobody sees did not happen."]],
            ["Gap", "Severity", "What fixing it would involve"], widths=[0.22, 0.12, 0.66]),

        H2("5.6", "Answers for an interview"),
        H3("\u201cWalk me through what happens when you push.\u201d"),
        P("A push to main starts one workflow with four jobs. Static checks validate files and HTML. Then the image "
          "is built locally, started, and probed on five routes; only then are AWS credentials used, to push it to "
          "ECR tagged with the commit SHA. The deploy job logs into EC2 over SSH and the instance's own IAM role "
          "pulls the image - the runner holds no AWS credentials. The old container is replaced, the health endpoint "
          "is polled, and finally the site is fetched from the public internet. Total about fifty seconds."),
        H3("\u201cWhy tag images by commit instead of latest?\u201d"),
        P("Because 'latest' makes two questions unanswerable: what is running, and what was running before. With a "
          "SHA tag the running container maps to one commit, rollback is a lookup rather than a rebuild, and ECR "
          "tag immutability guarantees the tag can never be repointed."),
        H3("\u201cWhat was the hardest bug?\u201d"),
        P("A rollback run that reported success while deploying nothing. The deploy job used the default "
          "<i>success()</i> condition, which evaluates the whole ancestor chain - and rollback runs skip the "
          "static-checks job, so a skipped ancestor made it false. GitHub then skipped the deploy and still showed "
          "the run green. The fix was an explicit result check, plus a guard job that fails any run where the "
          "deploy did not succeed."),
        H3("\u201cHow do you know a deploy actually worked?\u201d"),
        P("Three independent checks: the container's health endpoint from inside the instance, the same endpoint "
          "over the public IP, and - during the rollback drill - the image tag, the container's start timestamp and "
          "the byte size of the page. Any single green check can be wrong; three that agree are hard to fake."),
        H3("\u201cWhat would you do differently?\u201d"),
        P("OIDC instead of an access key, and SSM instead of SSH, so that no long-lived credential and no open port "
          "22 exist. Both were blocked or impractical here - the first by the account plan, the second by GitHub's "
          "5,622 rotating runner ranges against a 60-rule limit - and both are documented rather than ignored."),

        H2("5.7", "Glossary"),
        grid_table(
            [["Artefact", "The thing that gets deployed: here, a Docker image."],
             ["Build context", "The folder sent to the Docker daemon during a build - the final dot in docker build."],
             ["Digest", "A sha256 hash identifying an image independently of any tag."],
             ["ECR", "Elastic Container Registry - AWS's private image store."],
             ["EC2", "Elastic Compute Cloud - rented virtual machines."],
             ["IAP", "Not used here. If someone says 'jump box', they mean a bastion host - also not used."],
             ["Idempotent", "Running it twice gives the same result as once. docker rm -f is idempotent via || true."],
             ["Immutable tag", "A tag that can never be reassigned to different content."],
             ["Layer", "One filesystem diff inside an image. Shared layers are cached and reused."],
             ["Runner", "The throwaway machine GitHub provides for a job."],
             ["Smoke test", "A shallow test proving the artefact starts and serves, not that it is correct in detail."],
             ["SSH key pair", "A private key on your machine and a public key on the server; possession replaces a password."]],
            ["Term", "Meaning"], widths=[0.22, 0.78]),
        PageBreak(),
    ]
    return out


def appendices():
    out = []
    out += H1("A", "Appendix - The Complete Workflow File", "Reference")
    out += [
        P("The file below is the real <i>.github/workflows/deploy.yml</i> at the end of Phase 3. Long lines are "
          "wrapped so they fit the page; nothing else is altered."),
        Spacer(1, 4),
    ]
    path = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
    raw = open(path, encoding="utf-8").read()
    wrapped = []
    for line in raw.rstrip("\n").split("\n"):
        if len(line) <= 98:
            wrapped.append(line)
        else:
            wrapped.extend(textwrap.wrap(line, width=98, subsequent_indent="    ",
                                         break_long_words=False, break_on_hyphens=False))
    out.append(code_block("\n".join(wrapped), ".github/workflows/deploy.yml"))
    out.append(PageBreak())

    out += H1("B", "Appendix - Command Cheat Sheet", "Reference")
    out += [
        H2("B.1", "On your laptop (PowerShell)"),
        cmd_table([
            ("docker build -t NAME:TAG .", "Build an image from the Dockerfile in this folder."),
            ("docker run -d --name C -p 8080:80 NAME:TAG", "Start a container in the background, mapping port 8080 to 80."),
            ("docker ps", "What is running, with ports and uptime."),
            ("docker logs C", "The container's output."),
            ("docker tag LOCAL ECR_URI:TAG", "Give a local image a registry name so it can be pushed."),
            ("docker push ECR_URI:TAG", "Upload it. Requires an ECR login in the same shell."),
            ("aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.ap-south-1.amazonaws.com",
             "Authenticate Docker to ECR for twelve hours."),
            ("ssh -i key.pem ubuntu@IP", "Open a shell on the instance."),
            ("git status", "What has changed and what is staged."),
        ]),
        H2("B.2", "On the EC2 instance"),
        cmd_table([
            ("sudo systemctl is-enabled docker", "Is Docker set to start at boot? Expect: enabled."),
            ("docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' devops-demo", "Expect: unless-stopped."),
            ("docker pull IMAGE", "Fetch an image from the registry."),
            ("docker rm -f devops-demo", "Delete the running container (force)."),
            ("docker run -d --name devops-demo -p 80:80 --restart unless-stopped IMAGE", "Start it again from a new image."),
            ("curl -s http://localhost/healthz", "Ask the container if it is serving. Expect: ok."),
            ("aws sts get-caller-identity", "Which identity is this? Expect an assumed-role ARN, not a user."),
            ("sudo reboot", "Restart the machine - the restart policy should bring the container back."),
        ]),
        H2("B.3", "Recovery sequences"),
        grid_table(
            [["Site is down after a deploy", "Check the failed job's log, then re-run the last known good SHA through "
              "Run workflow with image_tag."],
             ["Site is down after a reboot", "docker ps -a, then read the container's restart policy and systemd status for docker."],
             ["SSH refuses to connect", "The instance IP changed, or your IP changed and the security-group rule no longer matches."],
             ["Push fails with 403 on a HEAD", "A missing ECR read permission - add exactly the action named in the error."]],
            ["Situation", "First move"], widths=[0.32, 0.68]),
    ]
    return out
