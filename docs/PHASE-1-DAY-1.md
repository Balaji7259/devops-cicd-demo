# Phase 1 — Day 1: Local development environment

Goal for today: your own Docker image serves your own page at
`http://localhost:8080`, and the code is on GitHub.

Nothing AWS yet. Today is entirely on your machine, and that is deliberate —
if the image is broken here, it will be broken on the server too, and debugging
two layers at once is how beginners lose a weekend.

---

## Step 0 — Understand the three tools you are about to install

**Git** records snapshots of your code. Every commit gets a hash (a
40-character ID). That hash becomes the identity of your Docker image later, so
"which code is running in production" has an exact answer.

**WSL2** (Windows Subsystem for Linux 2) is a real Linux kernel running inside
Windows. Docker containers are Linux processes; on Windows they need a Linux
kernel to run against. Docker Desktop uses WSL2 as that kernel. You will not
interact with it directly.

**Docker** packages an application and its dependencies into an image, and runs
that image as a container. An image is a frozen filesystem plus a start
command. A container is a running instance of it. This distinction matters
more than it looks: an image is portable, a container is disposable.

**Why not just copy files to the server?** Because then the server's exact
Python/Node/library versions are part of your deployment, undocumented. With an
image, the artifact you tested is byte-for-byte the artifact that runs.

---

## Step 1 — Check WSL2

Open **PowerShell as Administrator** (right-click Start, "Terminal (Admin)").

```powershell
wsl --status
```

Expected: something like `Default Version: 2`. If it says WSL is not installed,
run:

```powershell
wsl --install
```

That installs WSL2 plus an Ubuntu distribution and **requires a reboot**.

After rebooting, confirm:

```powershell
wsl --list --verbose
```

Expected: a table with a `VERSION` column showing `2`. If it shows `1`, run
`wsl --set-default-version 2`.

You do not need to use Ubuntu directly in this project; it is installed
because Docker Desktop needs it.

---

## Step 2 — Install and verify Git

Check whether Git is already present:

```powershell
git --version
```

Expected: `git version 2.x.x.windows.x`. If not found, install it:

```powershell
winget install --id Git.Git -e --source winget
```

Close and reopen PowerShell afterwards (PATH changes only apply to new
sessions), then re-check `git --version`.

Configure your identity — this is what appears in every commit:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

`init.defaultBranch main` means new repositories start on `main` instead of
the older `master`, matching GitHub's default.

Confirm:

```powershell
git config --global --list
```

---

## Step 3 — Install Docker Desktop

Download from the official page: <https://www.docker.com/products/docker-desktop/>

During installation, keep **"Use WSL 2 instead of Hyper-V"** checked. Finish
the installer and start Docker Desktop. Wait until the whale icon in the
system tray stops animating and the status says **Engine running**.

The first launch may ask you to accept a service agreement and may prompt for
WSL2 kernel updates — accept both.

### Verify

```powershell
docker version
```

Expected: two sections, `Client:` and `Server:`. The **Server** section is the
important one — it proves the Linux engine is actually up. If you only see
`Client` and then an error like `error during connect`, the engine is not
running; start Docker Desktop and wait.

```powershell
docker run --rm hello-world
```

Expected: `Hello from Docker!` followed by an explanation of what just
happened. This proves the engine can pull and run an image.

What just happened, precisely: Docker checked your local image cache, found
nothing, downloaded `hello-world` from Docker Hub, created a container from it,
ran it, printed to stdout, and `--rm` deleted the container on exit. The image
stays cached.

```powershell
docker info
```

Skim it. Note `Operating System: Docker Desktop`, `Kernel Version`, and
`Storage Driver`. You will refer back to this the first time a build behaves
oddly.

---

## Step 4 — Create the project and get the files

Create a project directory somewhere outside OneDrive (OneDrive sync fights
with Git and with Docker build contexts):

```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\projects\devops-cicd-demo" -Force
Set-Location "$env:USERPROFILE\projects\devops-cicd-demo"
```

This session already prepared the files for you at:

```
C:\Users\BALAJI\AccioWork\2026-11-13-15-13-43-373-ddbac5bd\devops-cicd\
```

Copy them in:

```powershell
Copy-Item -Recurse -Force "C:\Users\BALAJI\AccioWork\2026-11-13-15-13-43-373-ddbac5bd\devops-cicd\*" .
```

Then confirm the layout:

```powershell
Get-ChildItem -Recurse -File | Select-Object FullName
```

Expected files:

```
Dockerfile
.dockerignore
.gitignore
site\index.html
site\style.css
docs\PROJECT-PLAN.md
docs\PHASE-1-DAY-1.md
```

Read the `Dockerfile` and the two files in `site\` before building. If you
typed them yourself instead of copying, that is better practice — but do not
proceed until you can say what each line does.

### What each Dockerfile instruction means

| Instruction | Meaning |
|---|---|
| `FROM nginx:1.27-alpine` | Start from an existing image that already contains Nginx on a minimal Linux. Your image is a diff on top of it. |
| `LABEL` | Metadata only. Appears in `docker inspect`, useful for auditing. |
| `RUN rm -rf /usr/share/nginx/html/*` | Executes during **build**, creating a new layer. Removes the stock welcome page. |
| `COPY site/ /usr/share/nginx/html/` | Copies files from build context into the image. |
| `RUN printf 'ok\n' > .../healthz` | Creates a static file Nginx will serve at `/healthz`. |
| `EXPOSE 80` | Documentation. Does not publish anything. |
| `CMD ["nginx", "-g", "daemon off;"]` | The start command, used at **runtime**. |

---

## Step 5 — Build the image

```powershell
docker build -t devops-cicd-demo:v1 .
```

- `-t devops-cicd-demo:v1` names the image `devops-cicd-demo` with tag `v1`.
- The `.` is the **build context** — the directory sent to the Docker engine.
  Forget it and the build fails with "requires exactly 1 argument".

Expected output (BuildKit form): a sequence of numbered steps, several `CACHED`
or `DONE 0.0s` lines, and finally:

```
=> => naming to docker.io/library/devops-cicd-demo:v1
```

Confirm:

```powershell
docker images devops-cicd-demo
```

Expected: one row, `v1` in TAG, an IMAGE ID, and a SIZE around 50–60 MB.

If the image is several hundred MB, you are on the Debian-based `nginx:latest`
rather than `-alpine`.

---

## Step 6 — Run the container

```powershell
docker run -d --name devops-demo -p 8080:80 devops-cicd-demo:v1
```

- `-d` detached: run in background, return the terminal.
- `--name devops-demo` a fixed name, so later commands can refer to it
  instead of a random ID.
- `-p 8080:80` maps **host** 8080 to **container** 80. Nginx inside the
  container listens on 80; you reach it on 8080.

Expected: a single 64-character hex string — the container ID — and no other
output. Silence otherwise is success.

```powershell
docker ps
```

Expected: one row with `Up 3 seconds`, `0.0.0.0:8080->80/tcp`, and the name
`devops-demo`.

Open it:

```powershell
Start-Process "http://localhost:8080"
```

You should see the dark/light card page titled **Deployed by GitHub Actions**,
with "Environment: Local Docker".

Verify from the command line too, because this is exactly what CI will do:

```powershell
curl.exe -s -o NUL -w "HTTP %{http_code}" http://localhost:8080/
curl.exe -s http://localhost:8080/healthz
```

Expected: `HTTP 200` and then `ok`.

> Use `curl.exe`, not `curl`. In PowerShell, `curl` is an alias for
> `Invoke-WebRequest` and takes different flags. The `.exe` forces the real
> binary.

---

## Step 7 — Inspect what you built

This is the part most tutorials skip, and it is the part that makes you
employable.

```powershell
docker logs devops-demo
```

Expected: Nginx access-log lines, e.g.
`172.17.0.1 - - [..] "GET / HTTP/1.1" 200 ...`. Container logs are stdout of
the main process — no log files to hunt for.

```powershell
docker exec -it devops-demo sh
```

You are now **inside** the running container. Try:

```sh
ls /usr/share/nginx/html
cat /etc/os-release
nginx -v
exit
```

Expected: your `index.html`, `style.css`, `healthz`; Alpine Linux; the Nginx
version. Note there is no text editor and no `curl` in there — that is the
point of a minimal image.

```powershell
docker inspect devops-demo --format "{{.State.Status}} {{.Config.Image}}"
```

Expected: `running devops-cicd-demo:v1`.

---

## Step 8 — Container lifecycle (do this, do not just read it)

```powershell
docker stop devops-demo
docker ps            # gone from the running list
docker ps -a         # still there, status Exited (0)
docker start devops-demo
docker rm -f devops-demo
docker ps -a         # now truly gone
docker rmi devops-cicd-demo:v1
docker images        # empty for this name
```

The distinction to internalise: `stop` keeps the container (and its writable
layer), `rm` deletes it, `rmi` deletes the image. Files written inside a
container are lost with the container — which is fine here, because the
content comes from the image every time it starts.

Re-create it before moving on:

```powershell
docker run -d --name devops-demo -p 8080:80 devops-cicd-demo:v1
```

---

## Step 9 — Push to GitHub

Create an empty repository on GitHub named `devops-cicd-demo`.
**Do not** initialise it with a README, `.gitignore` or licence — that would
create a commit your local repo does not have and your first push would be
rejected.

Then, in your project directory:

```powershell
git init -b main
git add .
git status
```

Check the `git status` output carefully: you should see only the files listed
in Step 4. If a `.pem`, `.env` or anything with "credential" in the name
appears, stop and fix `.gitignore` before committing.

```powershell
git commit -m "feat: add Nginx app and Dockerfile for local container build"
git remote add origin https://github.com/<your-username>/devops-cicd-demo.git
git push -u origin main
```

On the first push, Git Credential Manager opens a browser window asking you to
authorise GitHub. Approve it; your token is then stored securely by Windows
Credential Manager, not in the repo.

Verify: refresh the GitHub repository page and confirm the files are there.

---

## Troubleshooting — actual error messages, actual causes

| Message | Cause | Fix |
|---|---|---|
| `docker: The term 'docker' is not recognized` | Docker Desktop not installed, or PATH not reloaded | Install it, then open a **new** PowerShell window |
| `error during connect: ... The system cannot find the file specified` | Docker engine not running (Docker Desktop closed or still starting) | Start Docker Desktop, wait for "Engine running" |
| `WSL 2 installation is incomplete` | Missing WSL2 kernel | Run `wsl --update`, restart Docker Desktop |
| `port is already allocated` | Something already listens on 8080 | Use `-p 8081:80` and browse to 8081, or find the other process |
| `Cannot connect to the Docker daemon at npipe://...` | Same as engine-not-running, on older versions | Start Docker Desktop |
| `failed to solve: ... failed to compute cache key: "site" not found` | Running `docker build` from the wrong directory | `Set-Location` into the folder containing `Dockerfile` |
| `docker build` says `requires exactly 1 argument` | Forgot the trailing `.` | Add it |
| Browser shows the default Nginx page | `COPY` did not run, or you are browsing a cached tab | Hard refresh; check `docker exec ... ls /usr/share/nginx/html` |
| `Permission denied (publickey)` on push | Wrong remote URL or unapproved credential | `git remote -v` to inspect; re-run `git push` and approve in browser |
| `Updates were rejected because the remote contains work...` | Repo was created with a README | `git pull --rebase origin main`, then push |

---

## Assignment (do this before Day 2)

Write your answers in `docs/DAY-1-NOTES.md`. Short answers are fine; the
point is that you can articulate them.

1. Change the heading in `site/index.html` to your own name. Rebuild with tag
   `v2`. Run **both** `v1` and `v2` at the same time on ports 8080 and 8081.
   Explain why two containers from two tags can coexist.
2. Rebuild `v1` without changing anything. Is the second build fast? Why?
   Which layer was reused?
3. Delete `site/style.css` from your working tree, rebuild, and observe what
   happens. Does the build fail? What does the running container serve?
   Revert the deletion afterwards.
4. Run `docker history devops-cicd-demo:v1`. Identify which instruction
   produces the largest layer.
5. Answer in two sentences each: what is an image, and what is a container?
6. Why is `EXPOSE` in the Dockerfile not enough to reach the app from your
   browser?

---

## Done when

- `docker ps` shows `devops-demo` publishing `0.0.0.0:8080->80/tcp`.
- `http://localhost:8080` renders your page.
- `curl.exe -s http://localhost:8080/healthz` prints `ok`.
- The GitHub repository contains `Dockerfile`, `site/`, `docs/` and no secrets.
- You can explain, unprompted, why the image is tagged `v1` today and why it
  will be tagged with a commit SHA from Day 6 onward.

Report back with: the `docker images` output, and any error text you hit that
is not in the table above. Then we start Day 2 — layers and caching, so that
your CI builds take seconds instead of minutes.
