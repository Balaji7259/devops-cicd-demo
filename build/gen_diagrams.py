"""Generate architecture diagrams for the CI/CD handbook."""
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")
os.makedirs(OUT, exist_ok=True)

NAVY = "#1F3A5F"
BLUE = "#2E86AB"
GREEN = "#2A9D8F"
AMBER = "#E9A23B"
RED = "#C14953"
GREY = "#64748B"
LIGHT = "#F1F5F9"
EDGE = "#CBD5E1"

plt.rcParams["font.family"] = "DejaVu Sans"


def canvas(w=11, h=6.2):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
    return fig, ax


def box(ax, x, y, w, h, title, body=None, fc="white", ec=NAVY, tc=NAVY,
        fs=9.5, body_fs=7.8, bold=True, radius=1.2, lw=1.4, body_color=None):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.35,rounding_size={radius}",
                       fc=fc, ec=ec, lw=lw, zorder=2)
    ax.add_patch(p)
    if body:
        ax.text(x + w / 2, y + h - 2.0, title, ha="center", va="top",
                fontsize=fs, color=tc, fontweight="bold" if bold else "normal", zorder=3)
        ax.text(x + w / 2, y + h - 4.6, body, ha="center", va="top", fontsize=body_fs,
                color=body_color or tc, linespacing=1.45, zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs,
                color=tc, fontweight="bold" if bold else "normal", linespacing=1.35, zorder=3)


def arrow(ax, p1, p2, label=None, color=GREY, style="-|>", ls="-", lw=1.6,
          rad=0.0, lx=0, ly=0, fs=7.4):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                        color=color, lw=lw, linestyle=ls, zorder=1,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs, color=color,
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="none", alpha=0.95), zorder=4)


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------- 1. overview
fig, ax = canvas(11.4, 6.6)
ax.text(50, 59.0, "How the whole system fits together", ha="center", va="top",
        fontsize=13.5, color=NAVY, fontweight="bold")

# left: where change starts
box(ax, 2, 44, 16, 7.6, "Developer", "edits a file", fc=LIGHT, ec=GREY, tc=NAVY, fs=9.2, body_fs=7.4)
box(ax, 2, 31, 16, 7.6, "GitHub", "main branch", fc=LIGHT, ec=GREY, tc=NAVY, fs=9.2, body_fs=7.4)
arrow(ax, (10, 43.6), (10, 38.9), "git push", lx=5.6, ly=0.3, fs=7.2)

# middle: the pipeline
ax.add_patch(FancyBboxPatch((24, 6), 46, 48, boxstyle="round,pad=0.5,rounding_size=1.4",
                            fc="#FAFCFE", ec=BLUE, lw=1.6, zorder=0))
ax.text(47, 52.0, "GitHub Actions", ha="center", fontsize=9.6, color=BLUE, fontweight="bold")
ax.text(47, 49.3, "cloud runner, no server needed", ha="center", fontsize=7.2, color=GREY, style="italic")

steps = [("1. Static checks", "files + HTML balance", 40.4),
         ("2. Build + smoke test", "container starts, routes answer", 32.7),
         ("3. Push image", "tagged with the commit SHA", 25.0),
         ("4. Deploy", "ssm send-command, runs as root", 17.3),
         ("5. Verify", "fetch the public URL", 9.6)]
for title, body, y in steps:
    fill = "#EAF4F8" if y >= 25 else "#E3F2EF"
    edge = BLUE if y >= 25 else GREEN
    box(ax, 26, y, 42, 6.6, title, body, fc=fill, ec=edge, fs=8.4, body_fs=7.0)
for i in range(len(steps) - 1):
    y1 = steps[i][2]
    arrow(ax, (47, y1 - 0.2), (47, y1 - 2.0), color=GREY, lw=1.2)

arrow(ax, (18.4, 34.8), (23.4, 34.8), "trigger", ly=1.6, fs=7.2)

# right: infrastructure
box(ax, 77, 37, 20, 9, "Amazon ECR", "private image registry\nimmutable tags",
    fc="#FFF6E6", ec=AMBER, fs=9.6, body_fs=7.2)
box(ax, 77, 19, 20, 10, "EC2 instance", "t3.micro, Ubuntu 24.04\nruns the container",
    fc="#FDECEE", ec=RED, fs=9.6, body_fs=7.2)
box(ax, 77, 5, 20, 8, "Visitors", "http://13.126.168.131",
    fc=LIGHT, ec=GREY, fs=9.2, body_fs=6.8)

arrow(ax, (68.4, 27.6), (76.6, 39.5), "docker push", rad=-0.12, lx=1.5, ly=1.2, fs=7.2, color=GREEN)
arrow(ax, (68.4, 20.2), (76.6, 22.8), "ssm send-command", ly=1.6, fs=6.8)
arrow(ax, (91, 28.4), (91, 36.6), "pull", lx=4.2, ly=0, fs=7.2, ls="--", color=AMBER)
arrow(ax, (87, 18.6), (87, 13.4), "HTTP 80", lx=5.0, ly=0, fs=7.2)

ax.text(50, 1.6,
        "The runner never stores the server's credentials: it logs in over SSH, and the instance's own IAM role fetches the image.",
        ha="center", fontsize=8.0, color=GREY, style="italic")
save(fig, "d1_overview.png")

# ---------------------------------------------------------------- 2. CI vs CD
fig, ax = canvas(11.4, 5.4)
ax.text(50, 58.5, "Continuous Integration vs Continuous Deployment", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

lanes = [
    ("CI - every push is checked", BLUE, 40, ["commit\npushed", "static\nchecks", "image\nbuilt", "smoke\ntest"]),
    ("CD - every good commit ships", GREEN, 18, ["image\npushed", "container\nreplaced", "health\ncheck", "live on\nthe web"]),
]
for label, color, y, steps in lanes:
    ax.add_patch(Rectangle((4, y - 3.2), 92, 15.4, fc=color, alpha=0.06, ec="none", zorder=0))
    ax.text(5.4, y + 10.2, label, ha="left", va="center", fontsize=9.4,
            color=color, fontweight="bold")
    x = 7
    for i, s in enumerate(steps):
        box(ax, x, y, 17, 7.6, s, None, fc="white", ec=color, fs=8.4)
        if i < len(steps) - 1:
            arrow(ax, (x + 17.3, y + 3.8), (x + 21.8, y + 3.8), color=color, lw=1.4)
        x += 22.6

ax.annotate("", xy=(96, 33.2), xytext=(96, 22.4),
            arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.4, ls=":"))
ax.text(94.6, 27.8, "automatically,\nno human step", ha="right", va="center",
        fontsize=7.6, color=GREY, style="italic")

ax.text(50, 7,
        "A red CI result stops the pipeline. Nothing is pushed and nothing is deployed.",
        ha="center", fontsize=8.6, color=GREY, style="italic")
save(fig, "d2_ci_cd.png")

# ---------------------------------------------------------------- 3. docker
fig, ax = canvas(10.6, 5.2)
ax.text(50, 58.5, "From Dockerfile to a running container", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

ax.add_patch(FancyBboxPatch((3, 30), 20, 22, boxstyle="round,pad=0.45,rounding_size=1.2",
                            fc=LIGHT, ec=GREY, lw=1.4, zorder=1))
ax.text(13, 49.0, "Dockerfile", ha="center", va="center", fontsize=9.6,
        color=NAVY, fontweight="bold", zorder=3)
ax.text(13, 45.0, "FROM nginx:1.27-alpine\nCOPY site/ .../html/\nEXPOSE 80",
        ha="center", va="top", fontsize=7.2, family="DejaVu Sans Mono",
        color=GREY, linespacing=1.7, zorder=3)

layers = [("base OS layer", 44.0), ("nginx layer", 39.2), ("your site files", 34.4)]
for label, yy in layers:
    ax.add_patch(Rectangle((29, yy), 24, 4.4, fc="#EAF4F8", ec=BLUE, lw=1.2, zorder=2))
    ax.text(41, yy + 2.2, label, ha="center", va="center", fontsize=8.2, color=NAVY, zorder=3)

box(ax, 29, 25, 24, 6.4, "IMAGE (read-only)", "devops-cicd-demo:v1", fc="#E3F2EF", ec=GREEN, fs=8.6)
box(ax, 62, 26, 22, 12, "CONTAINER", "same image, now\nrunning as a process\nport 80", fc="#FDECEE", ec=RED, fs=9.4)

arrow(ax, (23.6, 41.0), (28.5, 41.0), "docker build", ly=1.7, fs=7.6)
arrow(ax, (53.5, 28.2), (61.5, 30.5), "docker run", lx=1, ly=-1.7, fs=7.6)

ax.text(50, 12.5,
        "The image is a package; the container is one running copy of it.\n"
        "Layers are cached, so a rebuild only redoes what changed - which is why\n"
        "pipeline runs take 15 seconds instead of several minutes.",
        ha="center", va="center", fontsize=8.4, color=GREY, style="italic")
save(fig, "d3_docker.png")

# ---------------------------------------------------------------- 4. EC2
fig, ax = canvas(11.2, 5.8)
ax.text(50, 58.6, "What is inside the EC2 instance", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

ax.add_patch(FancyBboxPatch((20, 6), 58, 40, boxstyle="round,pad=0.6,rounding_size=1.6",
                            fc="#FDECEE", ec=RED, lw=1.8, alpha=0.35, zorder=0))
ax.text(49, 44.2, "EC2 instance  -  t3.micro, Ubuntu 24.04.5, 13.126.168.131",
        ha="center", fontsize=9.2, color=RED, fontweight="bold")

ax.add_patch(FancyBboxPatch((25, 11), 48, 22, boxstyle="round,pad=0.4,rounding_size=1.0",
                            fc="white", ec=RED, lw=1.2, zorder=1))
ax.text(49, 30.6, "Docker Engine", ha="center", va="center", fontsize=9.0,
        color=RED, fontweight="bold", zorder=3)
ax.add_patch(FancyBboxPatch((29, 14.5), 40, 13.5, boxstyle="round,pad=0.3,rounding_size=0.8",
                            fc="white", ec=RED, lw=1.1, zorder=2))
ax.text(49, 26.2, "Container: devops-demo", ha="center", fontsize=8.6, color=NAVY,
        fontweight="bold", zorder=3)
ax.text(49, 23.4, "nginx serving /usr/share/nginx/html", ha="center", fontsize=7.6, color=GREY, zorder=3)
ax.text(49, 21.0, "listening on port 80", ha="center", fontsize=7.6, color=GREY, zorder=3)
ax.text(49, 18.2, "restart policy: unless-stopped", ha="center", fontsize=7.6, color=GREEN,
        fontweight="bold", zorder=3)

box(ax, 0.5, 22, 16, 13, "Internet", "browsers\nand GitHub", fc=LIGHT, ec=GREY, fs=8.6, body_fs=7.2)
arrow(ax, (16.5, 28.5), (24.5, 28.5), "port 80", ly=1.5)

box(ax, 83, 24, 15, 11, "IAM role", "ecr-pull-...\nattached to the box", fc="#FFF6E6", ec=AMBER, fs=8.8)
arrow(ax, (82.5, 29.5), (74.2, 29.5), "pull image", ly=1.4, ls="--")

ax.text(49, 2.2,
        "SSH (port 22) is how the pipeline gets in; port 80 is how visitors get the site.\n"
        "No AWS keys live on this machine - the role provides temporary credentials.",
        ha="center", fontsize=8.4, color=GREY, style="italic")
save(fig, "d4_ec2.png")

# ---------------------------------------------------------------- 5. IAM
fig, ax = canvas(11.0, 5.6)
ax.text(50, 57.4, "Two identities, deliberately kept small", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

def panel(x, title, subtitle, allowed, denied, accent):
    ax.add_patch(FancyBboxPatch((x, 19), 44, 35, boxstyle="round,pad=0.45,rounding_size=1.2",
                                fc="white", ec=accent, lw=1.5, zorder=1))
    ax.text(x + 3, 51.2, title, ha="left", va="center", fontsize=9.4,
            color=NAVY, fontweight="bold", zorder=3)
    ax.text(x + 3, 48.3, subtitle, ha="left", va="center", fontsize=7.4,
            color=GREY, style="italic", zorder=3)
    ax.text(x + 3, 44.6, "ALLOWED", ha="left", va="center", fontsize=7.6,
            color=GREEN, fontweight="bold", zorder=3)
    yy = 43.1
    for item in allowed:
        ax.text(x + 3, yy, "- " + item, ha="left", va="center", fontsize=7.6,
                color=NAVY, zorder=3)
        yy -= 3.0
    ax.text(x + 3, yy - 0.2, "DENIED", ha="left", va="center", fontsize=7.6,
            color=RED, fontweight="bold", zorder=3)
    yy -= 3.2
    for item in denied:
        ax.text(x + 3, yy, item, ha="left", va="center", fontsize=7.4, color=RED, zorder=3)
        yy -= 2.6


panel(3, "IAM user  devops-cicd-ci", "used by GitHub Actions - key stored in secrets",
      ["get an authorization token", "upload image layers", "push the image",
       "read manifests and layers"],
      ["no delete, no new repositories,", "no EC2, no IAM, no billing"], BLUE)

panel(53, "IAM role  ecr-pull-devops-cicd-demo", "attached to the EC2 instance - no stored keys",
      ["get an authorization token", "read the image manifest", "download layers"],
      ["cannot push an image", "cannot list repositories", "(verified: DescribeRepositories fails)"], AMBER)

ax.text(50, 14.4, "BOTH ARE PINNED TO ONE RESOURCE",
        ha="center", fontsize=9, color=NAVY, fontweight="bold")
ax.text(50, 10.6,
        "arn:aws:ecr:ap-south-1:576329196399:repository/devops-cicd-demo",
        ha="center", fontsize=8.2, family="DejaVu Sans Mono", color=BLUE)

ax.text(50, 3.4,
        "A stolen CI key can only write images into this one repository.\n"
        "If the server is compromised, the attacker cannot push a malicious image.",
        ha="center", fontsize=8.4, color=GREY, style="italic")
save(fig, "d5_iam.png")

# ---------------------------------------------------------------- 6. gates
fig, ax = canvas(10.8, 6.0)
ax.text(50, 58.8, "Four gates, and what happens when one fails", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

gates = [
    ("Gate 1  Static checks", "required files, balanced HTML", "~5s",
     "nothing is built or spent"),
    ("Gate 2  Build + smoke test", "container starts, 5 routes answer 200", "~15s",
     "a bad image never reaches ECR"),
    ("Gate 3  Deploy + health check", "container healthy on the server", "~14s",
     "logs dumped, run goes red"),
    ("Gate 4  Public verification", "the site answers over the internet", "~3s",
     "a broken security group is caught"),
]
y = 45.5
for i, (t, d, dur, fail_note) in enumerate(gates):
    box(ax, 4, y, 46, 7.4, t, d, fc="#EAF4F8", ec=BLUE, fs=9.0, body_fs=7.6)
    ax.text(51.6, y + 3.7, dur, ha="left", va="center", fontsize=7.4, color=GREY)
    ax.text(58, y + 4.6, "FAILS -> run stops", ha="left", va="center", fontsize=8.2,
            color=RED, fontweight="bold")
    ax.text(58, y + 1.6, fail_note, ha="left", va="center", fontsize=7.6, color=GREY)
    if i < len(gates) - 1:
        arrow(ax, (27, y - 0.3), (27, y - 1.7), color=GREY, lw=1.3)
    y -= 9.4

ax.add_patch(FancyBboxPatch((4, 5.2), 92, 7.6, boxstyle="round,pad=0.4,rounding_size=1.0",
                            fc="#FFF6E6", ec=AMBER, lw=1.3))
ax.text(50, 11.4, "Guard job", ha="center", va="center", fontsize=8.8, color=AMBER, fontweight="bold")
ax.text(50, 7.8, "runs even when a job was skipped, and fails the run if the deploy did not happen",
        ha="center", va="center", fontsize=7.9, color=NAVY)
save(fig, "d6_gates.png")

# ---------------------------------------------------------------- 7. rollback
fig, ax = canvas(11.0, 4.6)
ax.text(50, 58.5, "Rollback: same gates, older image", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

versions = [("2b4b847", "manual deploy", 8), ("75d484f", "stamp added", 30),
            ("ad9a1a2", "gates", 52), ("193bd00", "guard fix", 74)]
for tag, note, x in versions:
    box(ax, x, 28, 18, 11, tag, note, fc="white", ec=BLUE, fs=9.4, body_fs=7.4)
for i in range(len(versions) - 1):
    arrow(ax, (versions[i][2] + 18.4, 33.5), (versions[i + 1][2] - 0.6, 33.5), color=GREY, lw=1.4)

# rollback path: down from the newest, back along the bottom, up into the oldest
ax.plot([92, 92, 12], [27.4, 18.0, 18.0], color=AMBER, ls="--", lw=1.9, zorder=1)
arrow(ax, (12, 18.0), (12, 27.2), color=AMBER, lw=1.9, ls="--")
ax.text(52, 15.0, "workflow_dispatch  with  image_tag = 2b4b847",
        ha="center", va="center", fontsize=8.0, color=AMBER, fontweight="bold")

ax.text(50, 6.5,
        "No rebuild, no source revert: the old image is pulled from ECR, smoke tested,\n"
        "and deployed by the same step a normal deploy uses.",
        ha="center", fontsize=8.4, color=GREY, style="italic")
save(fig, "d7_rollback.png")

# ---------------------------------------------------------------- 8. SSM path
fig, ax = canvas(11.2, 5.2)
ax.text(50, 58.6, "How a deploy reaches the server now", ha="center", va="top",
        fontsize=13, color=NAVY, fontweight="bold")

box(ax, 3, 30, 25, 18, "GitHub runner", "no key on disk\nno inbound port\nholds only ssm:SendCommand",
    fc="#EAF4F8", ec=BLUE, fs=9.2, body_fs=7.4)
box(ax, 34, 30, 28, 18, "AWS Systems Manager",
    "delivers the command\nreturns stdout and stderr\nkeeps a full history",
    fc="#FFF6E6", ec=AMBER, fs=9.2, body_fs=7.4)

ax.add_patch(FancyBboxPatch((68, 10), 29, 40, boxstyle="round,pad=0.5,rounding_size=1.4",
                            fc="#FDECEE", ec=RED, lw=1.6, alpha=0.45, zorder=0))
ax.text(82.5, 47.0, "EC2 instance", ha="center", fontsize=9.2, color=RED, fontweight="bold")

box(ax, 71, 35, 23, 9, "SSM agent", "already on the AMI", fc="white", ec=RED, fs=8.6, body_fs=7.0)
box(ax, 71, 23, 23, 9, "root shell", "runs deploy-remote.sh", fc="white", ec=RED, fs=8.6, body_fs=7.0)
box(ax, 71, 12, 23, 8, "Docker", "pull, swap, health check", fc="white", ec=RED, fs=8.6, body_fs=7.0)

arrow(ax, (28.4, 39), (33.5, 39), "SendCommand", ly=1.8, fs=7.2, color=GREEN)
arrow(ax, (62.4, 39), (70.4, 39.5), "polls for work", ly=1.8, fs=7.2, color=GREY, ls="--")
arrow(ax, (82.5, 34.6), (82.5, 32.4), color=GREY, lw=1.3)
arrow(ax, (82.5, 22.6), (82.5, 20.4), color=GREY, lw=1.3)

ax.text(50, 4.2,
        "Port 22 is gone. Verified from outside: port 22 closed, port 80 open - one reachable port, and the deploy does not use it.",
        ha="center", fontsize=8.0, color=RED, style="italic")
save(fig, "d8_ssm.png")

# ---------------------------------------------------------------- 9. rollback
fig, ax = canvas(10.8, 6.2)
ax.text(50, 58.8, "What happens when the new container is unhealthy", ha="center", va="top",
        fontsize=12.6, color=NAVY, fontweight="bold")

box(ax, 26, 48, 48, 7.4, "1. pull the new image", "the running site is untouched",
    fc="#EAF4F8", ec=BLUE, fs=8.8, body_fs=7.2)
box(ax, 26, 38.5, 48, 7.4, "2. remove the old container, start the new one", None,
    fc="#EAF4F8", ec=BLUE, fs=8.8)
box(ax, 26, 29, 48, 7.4, "3. poll /healthz", "10 attempts, two seconds apart",
    fc="#EAF4F8", ec=BLUE, fs=8.8, body_fs=7.2)
box(ax, 26, 19.5, 48, 7.4, "healthy?", None, fc="white", ec=NAVY, fs=9.2)

arrow(ax, (50, 47.6), (50, 46.3), color=GREY, lw=1.3)
arrow(ax, (50, 38.1), (50, 36.8), color=GREY, lw=1.3)
arrow(ax, (50, 28.6), (50, 27.3), color=GREY, lw=1.3)

box(ax, 2, 6, 25, 9, "exit 0", "run is GREEN", fc="#E3F2EF", ec=GREEN, fs=9.0, body_fs=7.4)
box(ax, 37, 5.5, 26, 10, "restart the previous image", "then poll again",
    fc="#FFF6E6", ec=AMBER, fs=8.2, body_fs=7.2)
box(ax, 73, 6, 25, 9, "exit 1", "site up, run is RED", fc="#FBEEF0", ec=RED, fs=9.0, body_fs=7.4)

arrow(ax, (26, 23.2), (15, 15.6), "yes", lx=-2.0, ly=1.4, color=GREEN, fs=7.6)
arrow(ax, (56, 19.2), (50, 16.0), "no", lx=4.0, ly=0.4, color=RED, fs=7.6)
arrow(ax, (63.4, 10.5), (72.4, 10.5), None, color=RED, lw=1.4)

ax.text(50, 1.4,
        "A rollback is a recovery, not a pass: the run must still fail, or nobody investigates.",
        ha="center", fontsize=8.2, color=GREY, style="italic")
save(fig, "d9_rollback_flow.png")

print("all diagrams done")
