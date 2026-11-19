"""Part 3 - moving the application to AWS, by hand."""
import os

from reportlab.platypus import PageBreak, Spacer

from pdf_lib import (P, H1, H2, H3, bullet, callout, cmd_table, code_block,
                     figure, grid_table)

DIAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")


def part3():
    out = []

    out += H1("3", "Phase 2 - A Real Server in AWS", "Part three")
    out += [
        P("Goal: the same container, running on a machine that stays on, reachable from any browser, "
          "with the security model done properly. Every step is performed by hand so that Part 4 can "
          "automate something already known to work.", "lead"),
    ]

    out += [
        H2("3.1", "The mental model, before touching the console"),
        P("Three AWS services do all the work, and each maps onto something ordinary:"),
        grid_table(
            [["Amazon ECR", "A private locker for images.",
              "Your Docker Hub, but only your account can read it."],
             ["Amazon EC2", "A computer you rent by the hour.",
              "A Linux box that is always on and has a public address."],
             ["AWS IAM", "The ID badges.",
              "Who may enter the locker, and who may switch the computer on."]],
            ["Service", "What it is", "What it is in plain terms"], widths=[0.2, 0.34, 0.46]),
        P("Two more pieces are attached to the instance rather than being separate services: a "
          "<b>security group</b> (its firewall) and an <b>IAM role</b> (the badge it wears). "
          "A role is the important idea: it means the server can act in AWS without any password "
          "ever being stored on disk."),

        H2("3.2", "Fixed facts for this build"),
        grid_table(
            [["Region", "ap-south-1 - Asia Pacific (Mumbai)"],
             ["Account", "576329196399 (AWS Free plan; credits expire 23 April 2027)"],
             ["ECR repository", "devops-cicd-demo - immutable tags, scan on push"],
             ["Instance", "devops-cicd-server - t3.micro, Ubuntu Server 24.04.5 LTS, 8 GiB gp3"],
             ["Public IPv4", "13.126.168.131 (changes if the instance is stopped and started)"],
             ["Key pair", "devops-cicd-key.pem - downloaded once, cannot be downloaded again"],
             ["Security group", "devops-cicd-sg - port 22 from your IP, port 80 from anywhere"],
             ["IAM role", "ecr-pull-devops-cicd-demo - pull from one repository"],
             ["IAM user", "devops-cicd-ci - push to one repository"]],
            ["Item", "Value"], widths=[0.26, 0.74]),
        callout("The account is on AWS's Free plan, which denies <i>iam:*Provider*</i> and therefore "
                "blocks creating an OIDC identity provider. That is why the pipeline uses a scoped access "
                "key instead of keyless federation. It is a real limitation, documented rather than "
                "hidden - see section 5.3.", "warn"),
    ]

    out += [
        H2("3.3", "Create the image registry"),
        P("In the console: <b>ECR - Create repository</b>. Name it <i>devops-cicd-demo</i>, keep it "
          "private, and turn on <b>tag immutability</b> with no tag exclusions."),
        P("Tag immutability means an existing tag can never be pointed at different bytes. Combined with "
          "tagging every image by commit hash, a running container is traceable to one commit permanently "
          "- and a rollback cannot be silently overwritten by a later push."),
        P("Enable <b>scan on push</b> as well. It costs nothing for the basic scanner and gives a CVE list "
          "per image."),

        H2("3.4", "The firewall: a security group"),
        P("A security group is a set of rules saying which ports are reachable from which addresses. "
          "Two rules, and the asymmetry between them is deliberate:"),
        grid_table(
            [["22 (SSH)", "your own public IP /32",
              "How you and the pipeline get a terminal. Never opened to the world."],
             ["80 (HTTP)", "0.0.0.0/0",
              "How visitors reach the site. It has to be public - it is a website."]],
            ["Port", "Source", "Why"], widths=[0.16, 0.24, 0.6]),
        callout("Later, the SSH rule was widened to 0.0.0.0/0 because GitHub's runners connect from "
                "addresses that change constantly: 5,622 IPv4 ranges, against a limit of 60 rules per "
                "security group. Whitelisting is impossible. The real fix is to stop using SSH for "
                "deployment at all - see section 5.5.", "danger"),
    ]

    out += [
        H2("3.5", "Launch the instance"),
        P("In the console: <b>EC2 - Launch instance</b>. Three choices matter; the rest are defaults."),
        bullet("<b>Ubuntu Server 24.04 LTS</b>, not Amazon Linux - apt-based, and the Docker instructions "
               "are the well-documented ones."),
        bullet("<b>t3.micro</b> - 2 vCPU, about 900 MiB of RAM. Enough to run nginx; deliberately not used "
               "to build images, because a Docker build on 1 GB of RAM invites the out-of-memory killer."),
        bullet("<b>Attach the IAM role at launch time</b>, so the instance never exists without its badge."),
        P("Also create a key pair and keep the <i>.pem</i> file. It is shown once. If it is lost, the "
          "instance is unreachable and has to be rebuilt."),

        H2("3.6", "Connect over SSH"),
        code_block("ssh -i C:\\Users\\BALAJI\\Downloads\\devops-cicd-key.pem ubuntu@13.126.168.131",
                   "PowerShell on your laptop"),
        cmd_table([
            ("ssh", "The client. Ships with Windows 10 and later; nothing to install."),
            ("-i ...pem", "The private key that proves identity. Windows sometimes insists the file be "
                          "readable only by you; if it complains about permissions, that is why."),
            ("ubuntu@", "The default user on an Ubuntu AMI. 'ec2-user' is for Amazon Linux - a common mix-up."),
            ("13.126.168.131", "The instance's public address. It changes if the instance is stopped and "
                               "started, which also silently breaks the SSH rule on your side."),
        ], ("Flag", "What it does")),
        P("The prompt changing to <i>ubuntu@ip-172-31-5-193:~$</i> is the signal that you are now typing "
          "on the server. Everything in the rest of this part runs there."),
    ]

    out += [
        H2("3.7", "Install Docker on the server, from Docker's own repository"),
        P("Ubuntu ships a <i>docker.io</i> package that is old and packaged differently. The official "
          "repository gives the current engine plus Compose and Buildx, which is what AWS documentation "
          "and most tutorials assume."),
        code_block("""sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \\
     -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \\
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \\
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \\
     docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker""", "Run on EC2 (the ubuntu@ip-... prompt)"),
        cmd_table([
            ("install -d /etc/apt/keyrings", "Create the directory where apt keeps signing keys, with "
                                             "correct permissions."),
            ("curl ... -o docker.asc", "Download Docker's public key. apt uses it to verify that packages "
                                       "really came from Docker."),
            ("echo \"deb [...]\" | tee ...", "Register Docker's repository as an extra source apt may "
                                             "install from."),
            ("docker-ce ...", "The engine, the client, the container runtime, plus the Buildx and Compose "
                              "plugins."),
            ("usermod -aG docker $USER", "Add ubuntu to the docker group so commands work without sudo. "
                                         "Group membership only applies to new sessions, hence the next line."),
            ("newgrp docker", "Start a shell with the new group. Logging out and back in does the same."),
        ], ("Command", "What it does")),
        P("Verify with <b>docker --version</b> and <b>docker run --rm hello-world</b>. The second command "
          "is the real test: it pulls an image, starts a container, prints, and exits. On this instance it "
          "reported Docker 29.10.0, Compose v5.7.2 and Buildx v0.39.0."),
    ]

    out += [
        H2("3.8", "Install the AWS CLI"),
        P("The server needs to talk to ECR. The CLI is how it authenticates, using the role it wears."),
        code_block("""curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
sudo apt-get install -y unzip
unzip -q awscliv2.zip
sudo ./aws/install
aws --version""", "Run on EC2"),
        P("The critical difference from your laptop: <b>no aws configure</b>. No access key is typed, no "
          "file is written. The CLI discovers the instance role through the instance metadata service and "
          "receives temporary credentials that rotate automatically. This is the most important security "
          "property of the whole build."),

        H2("3.9", "Two identities, both deliberately small"),
    ]

    out.append(figure(os.path.join(DIAG, "d5_iam.png"), 16.2,
                      "Neither identity can delete anything, and neither can reach outside its one repository."))

    out += [
        P("The instinct is to use one identity everywhere. Splitting them means the key held by GitHub "
          "cannot do what the server does, and a compromised server cannot push a malicious image that a "
          "later deploy would trust."),

        H2("3.10", "The push policy, action by action"),
        P("Attached to the IAM user <i>devops-cicd-ci</i>. This is the final form - it grew twice, and both "
          "additions were forced by a real failure."),
        code_block("""{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AuthenticateToEcr",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "PushAndPullOneRepo",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:ap-south-1:576329196399:repository/devops-cicd-demo"
    }
  ]
}""", "policy: ecr-push-devops-cicd-demo"),
        grid_table(
            [["GetAuthorizationToken", "Get a temporary password for the registry. Must be Resource \"*\" "
              "- it is not tied to a single repository."],
             ["BatchCheckLayerAvailability, InitiateLayerUpload, UploadLayerPart, CompleteLayerUpload",
              "The four steps of uploading one image layer."],
             ["PutImage", "Write the manifest that ties the layers into a named image."],
             ["BatchGetImage", "Read the manifest back. Docker verifies what it just wrote - without this, "
              "a push uploads every layer and then fails at the very end."],
             ["GetDownloadUrlForLayer", "Download a layer. Needed only for rollback, which pulls an older image."]],
            ["Action", "What it allows"], widths=[0.36, 0.64]),
        P("Notice what is absent: no DeleteRepository, no DeleteImage, no EC2, no IAM, no billing. A stolen "
          "CI key can add images to one repository and read them back. That is all."),
        P("The server's role carries only the four read actions - enough to pull, nothing else. It was "
          "verified by attempting something it should not be able to do:"),
        code_block("""aws sts get-caller-identity
# arn:aws:sts::576329196399:assumed-role/ecr-pull-devops-cicd-demo/i-01c13546bb8b4b707

aws ecr describe-repositories --region ap-south-1
# AccessDeniedException: not authorized to perform: ecr:DescribeRepositories""",
                   "Run on EC2 - the second failure is the proof"),
        P("The word <b>assumed-role</b> in that ARN is the evidence that no static key is in play."),
    ]

    out += [
        H2("3.11", "Push the image from Windows"),
    ]
    out.append(cmd_table([
        ("aws configure set aws_access_key_id \"...\"",
         "One-time setup of the CI user's key on the laptop. Do this in a private terminal; never paste "
         "the key into a chat or a file inside the repository."),
        ("aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "
         "576329196399.dkr.ecr.ap-south-1.amazonaws.com",
         "Ask AWS for a 12-hour registry password and pipe it straight into docker login. Nothing is "
         "echoed and nothing is stored."),
        ("docker tag devops-cicd-demo:v1 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847",
         "Give the local image the registry's name and a tag equal to the commit hash. Docker uploads only "
         "what is filed under that full name."),
        ("docker push 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847",
         "Upload the layers and the manifest. Ends with 'digest: sha256:...' - that digest is the image's "
         "permanent identity."),
    ], ("PowerShell", "What it does")))

    out += [
        callout("The first push failed twice, for two different reasons. First "
                "<i>not authorized to perform: ecr:InitiateLayerUpload</i> - the user had the pull policy "
                "attached by mistake. After that was fixed, every layer uploaded and the push still ended "
                "in a 403 on a HEAD request to the manifest, because <i>docker push</i> reads back what it "
                "wrote and <i>BatchGetImage</i> was missing. The method that solved both: read the exact "
                "action named in the error, add that one action, retry.", "danger"),

        H2("3.12", "Deploy by hand on the server"),
        P("Back on EC2, five commands. These are the five that Part 4 automates."),
    ]
    out.append(cmd_table([
        ("aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "
         "576329196399.dkr.ecr.ap-south-1.amazonaws.com",
         "Authenticate to the registry. The role supplies the credentials; nothing is typed."),
        ("docker pull 576329196399.dkr.ecr.ap-south-1.amazonaws.com/devops-cicd-demo:2b4b847",
         "Download the image. Layered, so a later deploy based on the same image only fetches what changed."),
        ("docker rm -f devops-demo",
         "Remove the old container - it has to go before a new one can bind port 80. The '|| true' in the "
         "pipeline version lets a first-ever deploy succeed."),
        ("docker run -d --name devops-demo -p 80:80 --restart unless-stopped IMAGE",
         "Start the new container. <b>--restart unless-stopped</b> is the line that keeps the site alive "
         "across reboots."),
        ("curl -s http://localhost/healthz", "Ask the container whether it is serving. Expected: ok."),
    ], ("Run on EC2", "What it does")))

    out += [
        P("The port mapping changed from 8080:80 on the laptop to 80:80 here. Port 80 is what the security "
          "group allows and what a browser uses by default; anything else would be unreachable from the "
          "internet."),
    ]
    out.append(figure(os.path.join(DIAG, "d4_ec2.png"), 16.2,
                      "One instance, one container, two open ports: 22 for the pipeline, 80 for visitors."))

    out += [
        H2("3.13", "Verify from outside, not from inside"),
        P("A local curl proves the container is running. It does not prove a visitor can reach it - a wrong "
          "security-group rule looks identical from inside the machine. The real test runs from a different "
          "network:"),
        grid_table(
            [["http://13.126.168.131/", "200 OK", "Title: DevOps CI/CD Demo, Server: nginx/1.27.5"],
             ["http://13.126.168.131/healthz", "200, body ok", "The endpoint the pipeline checks"]],
            ["Request", "Response", "What it proves"], widths=[0.34, 0.18, 0.48]),
        P("The <i>Server</i> header is worth noticing: it reports nginx 1.27.5, the version baked into the "
          "image, which confirms the container answering is the one that was pushed - not a stray system "
          "nginx installed by apt."),

        H2("3.14", "The reboot test"),
        P("Restart policies are easy to set and easy to get wrong, and the failure only shows up days "
          "later. So the instance was rebooted deliberately:"),
        code_block("""uptime
# 04:45:49 up 4 min

docker ps
# 434f09ddf077   ...devops-cicd-demo:2b4b847   Up 3 minutes   0.0.0.0:80->80/tcp   devops-demo

curl -s http://localhost/healthz
# ok""", "Run on EC2 immediately after a reboot"),
        P("Uptime four minutes, container up three, port still published, health endpoint still answering. "
          "Nothing was started by hand - the restart policy did it. Without that flag the site would have "
          "stayed down until someone logged in."),

        H2("3.15", "Checkpoint"),
        bullet("the public URL loads from a phone on mobile data, not just your laptop"),
        bullet("<i>systemctl is-enabled docker</i> reports <b>enabled</b>"),
        bullet("<i>docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' devops-demo</i> reports "
               "<b>unless-stopped</b>"),
        bullet("the ECR repository holds one image, tagged with the commit"),
        bullet("no access key exists anywhere on the instance"),
        Spacer(1, 6),
        callout("Cost while running is roughly $12.50 a month, almost all of it compute and the public IPv4 "
                "address, paid from the account's existing credits. Stopped, it is about $0.65 a month for "
                "the disk. Stop it rather than terminate it - termination destroys the server, while "
                "stopping only pauses compute billing.", "warn"),
        PageBreak(),
    ]
    return out
