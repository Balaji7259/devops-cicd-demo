"""Part 1 - the big picture, and Part 2 - the application in Docker."""
import os

from reportlab.platypus import PageBreak, Spacer

from pdf_lib import (P, H1, H2, H3, bullet, callout, cmd_table, code_block,
                     figure, grid_table)

DIAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")


def part1():
    out = []
    out += H1("1", "The Big Picture", "Part one")
    out += [
        H2("1.1", "The problem this project solves"),
        P("Before any automation existed, shipping a one-line change to the website meant doing this "
          "by hand, in order, without a mistake:"),
        bullet("build the Docker image on the laptop"),
        bullet("log in to Amazon's image registry"),
        bullet("tag the image correctly, then push it - twelve layers, about a minute"),
        bullet("open a second terminal and SSH into the server"),
        bullet("make the server log in to the registry as well"),
        bullet("pull the image down"),
        bullet("stop and delete the running container"),
        bullet("start a new container with the same ports and the same restart policy"),
        bullet("curl the health endpoint to prove it came back"),
        bullet("check the public URL from a different network, because a local check proves nothing"),
        Spacer(1, 4),
        P("Eleven steps. Each one is easy; the sequence is not. Miss the restart policy and the site "
          "dies at the next reboot. Forget the <i>docker rm</i> and the new container cannot take "
          "port 80. Push the wrong tag and the server pulls the previous image, silently. "
          "The failure that matters most is the quiet one: the deploy appears to work and serves "
          "stale content."),
        P("Automation is not about saving four minutes. It is about making those eleven steps happen "
          "identically every time, and making a failure loud instead of silent."),
        callout("This is the reason the project was built in phases. Phase 2 performs every step by hand. "
                "When Phase 3 fails, the question is only 'what did the automation get wrong?', never "
                "'does Docker work here?'. Debugging five systems at once is how people give up on CI/CD.", "good"),

        H2("1.2", "What 'CI' and 'CD' actually mean"),
        P("<b>Continuous Integration</b> means every push is automatically built and checked, so broken "
          "work is discovered in minutes rather than at release time. <b>Continuous Deployment</b> means "
          "a commit that passes those checks reaches production without a human deciding to release it."),
    ]
    out.append(figure(os.path.join(DIAG, "d2_ci_cd.png"), 16.2,
                      "The pipeline is two halves. A red check in the upper lane stops the lower lane entirely."))
    out += [
        P("The two halves are not equally strong in this project, and it is worth being precise about it:"),
        grid_table(
            [["<b>Continuous Integration</b>", "Real, but light. There is no unit-test suite, because a "
              "static Nginx site has no logic to unit-test. What is verified is the <i>artefact</i>: the image "
              "builds, the container starts, and every route answers 200."],
             ["<b>Continuous Deployment</b>", "Complete. A push to main reaches the public site in about "
              "50 seconds with no human step, including a rollback path."]],
            ["Half", "How it stands here"], widths=[0.26, 0.74]),
        P("Saying that honestly is more useful than claiming full test coverage. On a real application "
          "you would insert <i>pytest</i> or <i>npm test</i> before the build step; the workflow already "
          "has a slot for it."),

        H2("1.3", "The finished system"),
        P("Five moving parts. The picture below is the one to keep in your head for the rest of the document."),
    ]
    out.append(figure(os.path.join(DIAG, "d1_overview.png"), 16.4,
                      "Developer to public site, with the two AWS services and the two identities that connect them."))
    out += [
        P("Two details in that diagram are easy to miss and matter a great deal:"),
        bullet("<b>The deploy step carries no AWS credentials.</b> It logs in over SSH, and the server's own "
               "IAM role fetches the image. A compromised workflow can push images; it cannot act on the account."),
        bullet("<b>The image is tagged with the commit hash.</b> Whatever is running can be traced back to the "
               "exact commit that produced it, which is what makes rollback a lookup instead of a rebuild."),

        H2("1.4", "The cast of characters"),
        P("Nine terms, defined once, used precisely from here on."),
        grid_table(
            [["Git", "Version control on your laptop. Records what changed and when."],
             ["GitHub", "The remote copy of that history. The source of truth the pipeline reads."],
             ["GitHub Actions", "GitHub's build service. Runs a script on a fresh Linux machine whenever you push."],
             ["Docker", "Packages an application and its dependencies into one file that runs identically anywhere."],
             ["Image", "That package. Read-only, versioned, about 20 MB here."],
             ["Container", "A running instance of an image. Stop it and the image is untouched."],
             ["Amazon ECR", "A private registry that stores images. The locker the images live in."],
             ["Amazon EC2", "A rented computer in AWS that runs 24/7. This project uses the smallest size."],
             ["IAM", "AWS's identity system. Decides which human or machine may do what, to which resource."],
             ["Security group", "A firewall attached to the instance: which ports are reachable, from where."],
             ["Secret (GitHub)", "An encrypted value the workflow can read but nobody can view after saving."]],
            ["Term", "Plain meaning"], widths=[0.22, 0.78]),

        H2("1.5", "What must be installed on your own machine"),
        P("Only two things, and both are one-time:"),
        cmd_table([
            ("docker --version", "Docker Desktop. Provides the engine, the CLI and Compose. Must be running - "
                                 "a closed Docker Desktop is the most common first error."),
            ("git --version", "Git for Windows, which also installs the credential manager used to authenticate to GitHub."),
        ]),
        P("AWS work happens in the browser console, except for the commands that run on the server itself, "
          "which arrive over SSH using a built-in Windows client."),
        PageBreak(),
    ]
    return out


def part2():
    out = []
    out += H1("2", "Phase 1 - A Container That Runs Locally", "Part two")
    out += [
        P("Goal: the website running in a container on your laptop, reachable at "
          "<i>http://localhost:8080</i>, and the source pushed to GitHub. Nothing AWS yet.", "lead"),

        H2("2.1", "Why Docker is the unit of deployment"),
        P("The pipeline does not ship HTML files. It ships an image. That choice decides almost everything "
          "downstream: the image is what gets tested, what gets tagged, what gets pushed to ECR, and what the "
          "server runs. Files on a server drift; an image cannot."),
        P("The image also carries the web server itself. The instance does not need nginx installed - "
          "the container brings its own, at a fixed version, which is why the response header can be predicted "
          "before the deploy happens."),

        H2("2.2", "The files that make up the application"),
        code_block("""PIPELINE-PROJECT/
  site/
    index.html          the page visitors see
    about.html          a second page, to prove routing works
    style.css           styling
    assets/logo.svg     a static asset, to prove asset paths work
  Dockerfile            how to package the site
  .dockerignore         what must not be sent to the build
  .gitignore            what must never be committed""", "repository layout"),
        P("Two of those pages exist for a testing reason rather than a design one: the smoke test checks that "
          "<i>/about.html</i>, <i>/style.css</i> and <i>/assets/logo.svg</i> all return 200. A single-page site "
          "would let a broken COPY instruction pass unnoticed until a visitor found it."),

        H2("2.3", "The Dockerfile, line by line"),
        code_block("""FROM nginx:1.27-alpine
COPY site/ /usr/share/nginx/html/
RUN printf 'ok' > /usr/share/nginx/html/healthz
EXPOSE 80""", "Dockerfile"),
        cmd_table([
            ("FROM nginx:1.27-alpine", "Start from an official image that already contains nginx and a minimal "
                                       "Linux. Alpine keeps it near 20 MB. Pinning 1.27 rather than 'latest' means "
                                       "a rebuild next year produces the same server."),
            ("COPY site/ ...", "Copy the local site folder into the directory nginx serves by default. "
                               "This is the only layer that changes when you edit HTML, which is why rebuilds are fast."),
            ("RUN printf 'ok' ...", "Create a tiny file the pipeline can curl. This is the health endpoint: one word, "
                                    "no dependency on the application itself."),
            ("EXPOSE 80", "Documentation, not a firewall. It states that the process listens on 80; the actual "
                          "port mapping happens in docker run."),
        ]),

        H2("2.4", "Build the image"),
        cmd_table([
            ("docker build -t devops-cicd-demo:v1 .", "Build an image from the Dockerfile in the current folder "
                                                      "and give it a name and a version. The final dot is the build "
                                                      "context - forget it and Docker errors immediately."),
            ("docker images", "List local images. Confirms the build produced something, with its size and ID."),
        ], ("PowerShell, in the project folder", "What it does")),
        callout("If the build fails with 'error during connect' or a named-pipe error, Docker Desktop is not "
                "running. Start it, wait for the whale icon to stop animating, and retry. Nothing about the "
                "project is wrong.", "warn"),

        H2("2.5", "Run it"),
        cmd_table([
            ("docker run -d --name devops-demo -p 8080:80 devops-cicd-demo:v1",
             "<b>-d</b> detach (run in background), <b>--name</b> give the container a stable name so later "
             "commands can refer to it, <b>-p 8080:80</b> map port 8080 on the laptop to port 80 inside the "
             "container, then the image to run."),
            ("docker ps", "List running containers: name, image, status, and the port mapping. The place to look "
                          "first when something is not reachable."),
            ("docker logs devops-demo", "nginx's request log. Proof that traffic is arriving, and the first thing "
                                        "to read when it is not."),
            ("docker stop devops-demo", "Stop the process. The image stays; the container is now stopped, not gone."),
        ], ("PowerShell", "What it does")),
        P("The port mapping deserves one sentence of explanation, because it is where beginners lose an hour. "
          "Inside the container nginx listens on 80 and knows nothing about 8080. The mapping is a rule on the "
          "host: connections to laptop port 8080 are forwarded into container port 80. On the server the mapping "
          "is 80:80 instead, because there the port must be the public one."),

        H2("2.6", "Prove it works - and how to prove it properly"),
        cmd_table([
            ("start http://localhost:8080", "Open the site in a browser (Command Prompt). In PowerShell the "
                                            "equivalent is a plain URL, or Start-Process."),
            ("curl http://localhost:8080/healthz", "Fetch the health endpoint. Expected output: ok. This single "
                                                   "word is what the pipeline will check after every deploy."),
        ], ("PowerShell or Command Prompt", "What it does")),
    ]
    out.append(figure(os.path.join(DIAG, "d3_docker.png"), 15.6,
                      "The Dockerfile produces an image; the image produces containers. Layers are cached, which is why pipeline builds take seconds."))
    out += [
        H2("2.7", "Put the code on GitHub"),
        P("GitHub is the trigger for everything in Phase 3, so the repository has to exist before any "
          "automation is possible."),
        cmd_table([
            ("git init", "Turn the folder into a Git repository. Creates the hidden .git folder that holds history."),
            ("git config --global init.defaultBranch main", "Make 'main' the default branch name for new repositories. "
                                                            "Run once per machine."),
            ("git add .", "Stage every file that is not excluded by .gitignore."),
            ("git commit -m \"...\"", "Record the staged files as one snapshot, with a message explaining why."),
            ("git remote add origin https://github.com/USER/REPO.git", "Point the local repository at the GitHub one."),
            ("git push -u origin main", "Upload the history and set the upstream, so later pushes are just 'git push'."),
        ], ("PowerShell, in the project folder", "What it does")),
        callout("The first push in this project failed with <i>Permission to Balaji7259/... denied to "
                "Nagaraju-shetty</i>. A different GitHub account was cached in Windows Credential Manager. "
                "The fix was to re-authenticate in the browser as the correct account. If you ever see "
                "'denied to' a name you do not recognise, that is exactly what happened.", "danger"),

        H2("2.8", "Checkpoint"),
        P("Stop here until all four are true. Phase 3 cannot work if any of them is not:"),
        bullet("the site loads at <i>http://localhost:8080</i>"),
        bullet("<i>curl http://localhost:8080/healthz</i> prints <b>ok</b>"),
        bullet("the repository on GitHub shows the site folder and the Dockerfile"),
        bullet("the working tree is clean - <i>git status</i> reports nothing to commit"),
        PageBreak(),
    ]
    return out
