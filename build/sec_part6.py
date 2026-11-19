"""Part 6 - Phase 4: hardening what Phase 3 automated."""
import os

from reportlab.platypus import PageBreak, Spacer

from pdf_lib import (P, H1, H2, H3, bullet, callout, cmd_table, code_block,
                     figure, grid_table)

DIAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")


def part6():
    out = []
    out += H1("6", "Phase 4 - Making It Survivable", "Part six")
    out += [
        P("Phases 1 to 3 answered one question: can a push reach the website without a human? "
          "The answer was yes, in about fifty seconds. Phase 4 asks the harder question: what "
          "happens when the thing being pushed is wrong?", "lead"),

        H2("6.1", "Two weaknesses worth fixing first"),
        P("Looking at the finished Phase 3 pipeline honestly, two things stood out."),
        P("<b>A failed deploy took the site down.</b> The old container was removed before the new one "
          "started, and the health check ran afterwards. So a bad image was caught, reported - and by "
          "then the working container was already gone. The pipeline told you the site was broken; it "
          "did not stop the site breaking."),
        P("<b>The deploy needed port 22 open to the world.</b> GitHub publishes its runner address "
          "ranges, but there are 5,622 of them and a security group accepts 60 rules. Whitelisting was "
          "mathematically impossible, so SSH was open to everything and protected by a key alone."),
        P("Neither is dramatic. Both are the difference between a demonstration and something you "
          "would leave running."),
    ]

    out += [
        H2("6.2", "Automatic rollback"),
        P("The deploy logic moved out of the workflow into <i>scripts/deploy-remote.sh</i>, so it could "
          "be reviewed as one unit, linted with <b>bash -n</b>, and above all run against the real "
          "server before the pipeline depended on it."),
    ]
    out.append(figure(os.path.join(DIAG, "d9_rollback_flow.png"), 15.6,
                      "The recovery path: a failed health check restores the previous image, then fails the run anyway."))
    out += [
        P("Three decisions in that shape are worth defending:"),
        bullet("<b>The pull happens before the swap.</b> A registry outage, an expired token or a "
               "missing tag leaves the running site untouched. The failure costs nothing."),
        bullet("<b>A successful rollback still exits 1.</b> The site is up, but the deployment did not "
               "succeed. Returning zero would produce a green run that hides a real defect."),
        bullet("<b>A separate file, not an inline heredoc.</b> It can be tested directly, which is how "
               "the behaviour below was proven rather than assumed."),
        H3("How it was proven"),
        P("A deliberately unhealthy image was built - bare <b>nginx:alpine</b> with no site files, so "
          "<i>/healthz</i> returns 404 - and pushed to ECR. Two runs against a throwaway container on "
          "port 8081, leaving the live site alone:"),
        code_block("""currently running: ...:273f415d3a44...
pulling ...:broken-test
health check failed for ...:broken-test
ROLLING BACK to ...:273f415d3a44...
healthy after 2 attempt(s)
ROLLED BACK to ...:273f415d3a44... - the previous version is serving again

exit code 1""", "the failure path, executed on the real instance"),
        P("Server-side nginx confirmed the actual cause rather than a generic failure:"),
        code_block("""open() "/usr/share/nginx/html/healthz" failed (2: No such file or directory)
"GET /healthz HTTP/1.1" 404"""),
        P("Afterwards the test container was running the good image, your live container was untouched, "
          "and the run had failed as designed. All four edge cases are handled explicitly: first deploy "
          "(nothing to roll back to), redeploying the same tag (restart instead of switch), a failed "
          "pull (old container never removed), and a rollback that itself fails to become healthy "
          "(the log says so, loudly)."),
    ]

    out += [
        H2("6.3", "Deploying without SSH"),
        P("The answer to the 5,622-range problem was not a better firewall rule. It was to stop "
          "needing an inbound connection at all."),
    ]
    out.append(figure(os.path.join(DIAG, "d8_ssm.png"), 16.2,
                      "The command travels through AWS, not to the machine. Nothing listens on port 22."))
    out += [
        grid_table(
            [["How it reaches the server", "An SSH session to port 22", "ssm:SendCommand through the AWS control plane"],
             ["Who it runs as", "the <i>ubuntu</i> user", "<b>root</b>, via the SSM agent"],
             ["What must be open", "port 22 to the world", "nothing - outbound only"],
             ["What must be stored", "a private key, on the runner and in GitHub", "nothing"],
             ["Evidence afterwards", "whatever you remember", "every command and its output, retained by AWS"]],
            ["", "Phase 3", "Phase 4"], widths=[0.26, 0.34, 0.4]),
        P("The deploy script itself is unchanged. Only the transport moved, which is why the rollback "
          "logic needed no rework: the script still decides what happens, and Systems Manager is merely "
          "how it gets there."),
        H3("The permissions, again kept small"),
        P("The CI user gained a <b>separate policy</b> rather than a wider existing one:"),
        code_block("""{
  "Statement": [
    {
      "Sid": "SendOnlyToThisInstance",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:ap-south-1:576329196399:instance/i-01c13546bb8b4b707",
        "arn:aws:ssm:ap-south-1::document/AWS-RunShellScript"
      ]
    },
    {
      "Sid": "ReadCommandResult",
      "Effect": "Allow",
      "Action": ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
      "Resource": "*"
    }
  ]
}""", "policy: ssm-deploy-devops-cicd-demo"),
        P("SendCommand is pinned to one instance ARN, so even with another instance ID the CI user "
          "cannot command a second box. Push rights and shell rights live in different documents so "
          "either can be revoked without touching the other. GetCommandInvocation sits on <b>*</b> "
          "because AWS does not support scoping it - and it only reads the status of a command whose "
          "ID you already hold."),
        P("The instance gained <b>AmazonSSMManagedInstanceCore</b>, which lets the agent open its "
          "control channel. Nothing in that policy grants access to your data."),
        H3("Getting the script to the machine"),
        P("A shell script cannot simply be pasted into a command parameter: it contains quotes, "
          "dollar signs and newlines, and each of those is a way to corrupt it. The script is gzipped, "
          "base64-encoded, split into chunks of 800 characters, and reassembled on the instance:"),
        code_block("""install -d -m 700 /var/lib/deploy-ci
rm -f /var/lib/deploy-ci/payload.b64
printf '%s' '<chunk 1>' >> /var/lib/deploy-ci/payload.b64
...
base64 -d /var/lib/deploy-ci/payload.b64 | gzip -dc > /var/lib/deploy-ci/deploy.sh
IMAGE_URI='...' bash /var/lib/deploy-ci/deploy.sh; rc=$?; ...; exit $rc""",
                   "six commands, longest 833 characters"),
        P("Base64 output contains no quotes, no backslashes and no spaces, so nothing can be "
          "misinterpreted on the way. A 3.4 KB script becomes about 2.2 KB of text, and the whole "
          "payload is verified locally by decompressing it and comparing bytes with the original."),
    ]

    out += [
        H2("6.4", "Four failed runs, and what they actually were"),
        P("The migration took four red runs. The cause was not what any of them appeared to say, and "
          "the reason it took four is worth more than the fix."),
        grid_table(
            [["#14", "inline JSON parameter", "rejected before reaching the machine"],
             ["#15", "parameter passed as a file", "same rejection"],
             ["#16", "payload split into chunks", "same rejection"],
             ["#17", "root-owned staging directory", "same rejection"]],
            ["Run", "What was changed", "Outcome"], widths=[0.12, 0.38, 0.5]),
        P("The error, once it was finally visible, had nothing to do with any of that:"),
        code_block("""ValidationException: Value 'deploy 576329196399.dkr.ecr.ap-south-1.amazonaws.com/...
at 'comment' failed to satisfy constraint: Member must have length less than or equal to 100"""),
        P("The <b>--comment</b> argument. A full ECR URI is 108 characters and SSM allows 100. Four "
          "characters, on a cosmetic label, rejected every request before it reached the instance."),
        callout("The first attempt used <b>set -e</b>, which killed the step the moment the CLI failed "
                "and discarded its message. The fix was to capture stderr and echo it. That should have "
                "ended it - and did not, because the diagnostic annotation was built from the first line "
                "of the AWS error, and the CLI prefixes its error with a blank line. GitHub silently "
                "drops an annotation with an empty message, so the instrument built to reveal the error "
                "was itself invisible.", "danger"),
        P("Two mistakes stacked, each hiding the other. The lesson is not \"read the API documentation\" "
          "- it is that <b>when a diagnostic shows nothing, suspect the diagnostic.</b>"),
        H3("A second finding, from the same afternoon"),
        P("While testing locally, a command failed with <i>cannot create /tmp/deploy-remote.sh: "
          "Permission denied</i> - as root. The cause was a leftover file owned by another user in "
          "<b>/tmp</b>, combined with Ubuntu's <b>fs.protected_regular=2</b>, which makes the kernel "
          "refuse to open a file you do not own inside a world-writable sticky directory, even as root. "
          "The staging directory is now <b>/var/lib/deploy-ci</b>, created mode 700, where nothing else "
          "can collide."),
    ]

    out += [
        H2("6.5", "The final posture"),
        grid_table(
            [["Trigger", "Push to main, or a manual run with an image tag"],
             ["CI checks", "Files present, HTML balanced, image built and smoke tested before publishing"],
             ["Deploy", "<b>ssm:SendCommand</b> to one instance, running the same script as before"],
             ["Recovery", "Unhealthy container is replaced by the previous image, then the run fails"],
             ["Rollback", "Manual dispatch with any published image tag, through the same gates"],
             ["Guard", "A run where the deploy did not happen cannot be green"],
             ["Credentials on disk", "None - neither on the runner nor on the server"],
             ["Reachable ports", "80 only. Verified from outside: 22 closed, 80 open"],
             ["Audit", "Every server command and its output retained in AWS command history"]],
            ["Concern", "How it is handled"], widths=[0.26, 0.74]),
        H3("What is still missing, deliberately"),
        bullet("<b>No unit tests.</b> The application is static; the artefact is tested instead. A real "
               "service would add them before the build step - the slot exists."),
        bullet("<b>Not zero-downtime.</b> The container is replaced, not overlapped, so there is a "
               "second or two where nothing answers. A load balancer and two instances would fix it."),
        bullet("<b>No failure notification.</b> A red run is only seen by whoever looks at the Actions "
               "tab. Worth adding when more than one person depends on this."),
        bullet("<b>Was a dynamic public address - since fixed.</b> The instance's IPv4 changed on "
               "every stop/start and silently invalidated one stored secret. An Elastic IP is now "
               "attached (<i>15.252.179.238</i>), so the address is static and the secret cannot go "
               "stale behind a restart."),
        Spacer(1, 4),
        callout("None of these are accidents. Each is a documented trade-off with a known fix, which is "
                "a different thing from a gap nobody noticed.", "good"),
        PageBreak(),
    ]
    return out
