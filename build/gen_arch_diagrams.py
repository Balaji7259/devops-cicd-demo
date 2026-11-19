"""Draws the two architecture diagrams published in docs/diagrams/.

Regenerate with:  python build/gen_arch_diagrams.py
The other diagrams in that folder come from build/gen_diagrams.py.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

NAVY = "#1F3A5F"
BLUE = "#2E86AB"
GREEN = "#2A9D8F"
AMBER = "#B7791F"
RED = "#C14953"
GREY = "#5A6B7B"
INK = "#22313F"


def box(ax, x, y, w, h, title, sub=None, edge=BLUE, fill="#F4F9FC", tsize=11.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.14",
                                linewidth=1.6, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h - (0.22 if sub else h / 2), title, ha="center",
            va="top" if sub else "center", fontsize=tsize, color=NAVY, fontweight="bold")
    if sub:
        ax.text(x + w / 2, y + h - 0.46, sub, ha="center", va="top", fontsize=9.2,
                color=GREY, linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, label=None, color=GREY, style="-|>", ls="-", dx=0, dy=0.16):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                                 linewidth=1.5, color=color, linestyle=ls,
                                 shrinkA=2, shrinkB=2))
    if label:
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, label, ha="center", va="center",
                fontsize=8.8, color=color, style="italic")


def canvas(w=13, h=7):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis("off")
    return fig, ax


def save(fig, path):
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", path)


# ----------------------------------------------------------------- overview
fig, ax = canvas(13.2, 7.4)
ax.text(6.6, 7.12, "The whole system, after Phase 4", ha="center", fontsize=15,
        color=NAVY, fontweight="bold")

box(ax, 0.15, 5.15, 1.95, 1.15, "Developer", "edits a file\ngit push", edge=GREY, fill="#F7F9FB")
box(ax, 0.15, 3.25, 1.95, 1.15, "GitHub", "main branch\ntriggers workflow", edge=GREY, fill="#F7F9FB")
arrow(ax, 1.12, 5.12, 1.12, 4.45, "push", dx=0.42)

box(ax, 2.75, 2.55, 3.6, 3.95, "GitHub Actions runner", "a fresh VM for every run\nnothing persists between runs",
    edge=BLUE, fill="#F4F9FC")
steps = [("1  static checks", "files, HTML, health marker"),
         ("2  build + smoke test", "5 routes before the registry"),
         ("3  push to ECR", "tagged with the commit SHA"),
         ("4  deploy via SSM", "no SSH, no inbound port")]
y = 5.55
for t, s in steps:
    ax.add_patch(FancyBboxPatch((3.0, y - 0.62), 3.1, 0.62,
                                boxstyle="round,pad=0.015,rounding_size=0.09",
                                linewidth=1.1, edgecolor="#BBD3E6", facecolor="white"))
    ax.text(4.55, y - 0.17, t, ha="center", va="center", fontsize=9.6,
            color=NAVY, fontweight="bold")
    ax.text(4.55, y - 0.45, s, ha="center", va="center", fontsize=8.0, color=GREY)
    y -= 0.86
arrow(ax, 2.12, 3.82, 2.72, 3.82, "trigger", dy=0.22)

box(ax, 7.1, 5.35, 2.35, 1.15, "Amazon ECR", "private registry\nimmutable tags", edge=AMBER, fill="#FDF7EA")
box(ax, 7.1, 3.0, 2.35, 1.3, "EC2  t3.micro", "Ubuntu 24.04\nruns the container", edge=RED, fill="#FBEEF0")
box(ax, 7.1, 1.05, 2.35, 1.15, "Visitors", "one open port\n80/tcp", edge=GREY, fill="#F7F9FB")

arrow(ax, 6.35, 5.2, 7.05, 5.85, "docker push", color=AMBER, dx=-0.05, dy=-0.3)
arrow(ax, 6.35, 3.2, 7.05, 3.45, "ssm send-command", color=GREEN, dx=-0.35, dy=-0.34)
arrow(ax, 8.27, 5.3, 8.27, 4.35, "pull", color=AMBER, ls="--", dx=0.34, dy=0)
arrow(ax, 8.27, 2.95, 8.27, 2.25, "HTTP", dy=0)

box(ax, 10.1, 4.55, 2.85, 1.95, "Two identities", "CI user: push, and send\none command\nEC2 role: pull only\nneither can delete",
    edge=GREEN, fill="#EDF7F5", tsize=10.2)
box(ax, 10.1, 1.05, 2.85, 2.1, "What is gone", "no SSH key on disk\nno inbound port 22\nno credential in the image\nevery deploy audited",
    edge=GREY, fill="#F7F9FB", tsize=10.2)

ax.text(6.6, 0.35, "The runner never holds the server's credentials, and the server never holds a registry password.",
        ha="center", fontsize=9.5, color=GREY, style="italic")
save(fig, "docs/diagrams/architecture-overview.png")


# ---------------------------------------------------------------------- iam
fig, ax = canvas(13.2, 7.0)
ax.text(6.6, 6.62, "Who can do what, and why it is this small", ha="center", fontsize=15,
        color=NAVY, fontweight="bold")


def panel(x, title, lines, edge, fill):
    w, top, bottom = 4.0, 6.1, 2.35
    ax.add_patch(FancyBboxPatch((x, bottom), w, top - bottom,
                                boxstyle="round,pad=0.02,rounding_size=0.14",
                                linewidth=1.6, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, top - 0.28, title, ha="center", va="center",
            fontsize=9.7, color=NAVY, fontweight="bold")
    y = top - 0.78
    for kind, text in lines:
        if kind in ("ALLOWED", "DENIED"):
            y -= 0.18
            ax.text(x + 0.3, y, kind, fontsize=9.0, color=GREEN if kind == "ALLOWED" else RED,
                    fontweight="bold")
        else:
            ax.text(x + 0.3, y, text, fontsize=8.7, color=INK)
        y -= 0.34


panel(0.25, "IAM user  devops-cicd-ci", [
    ("ALLOWED", ""),
    ("item", "ecr: push, pull, read one repo"),
    ("item", "ssm: SendCommand, one instance"),
    ("item", "ssm: read that command's output"),
    ("item", "ec2/ssm: read instance state"),
    ("DENIED", ""),
    ("item", "no delete, no new repositories"),
    ("item", "no IAM, no billing, no EC2 writes"),
], BLUE, "#F4F9FC")

panel(4.6, "IAM role  ecr-pull-devops-cicd-demo", [
    ("ALLOWED", ""),
    ("item", "ecr: authorization token"),
    ("item", "ecr: read manifests and layers"),
    ("item", "ssm core (agent registers,"),
    ("item", "   receives commands)"),
    ("DENIED", ""),
    ("item", "cannot push an image"),
    ("item", "cannot list repositories"),
], AMBER, "#FDF7EA")

panel(8.95, "Why it is this small", [
    ("item", "Both point at ONE repository ARN,"),
    ("item", "so neither can touch anything else."),
    ("item", ""),
    ("item", "A leaked CI key: a bad image in"),
    ("item", "one repo, which the health check"),
    ("item", "would refuse to deploy."),
    ("item", ""),
    ("item", "A compromised server: cannot"),
    ("item", "publish an image at all."),
], GREEN, "#EDF7F5")

ax.text(6.6, 1.75, "arn:aws:ecr:ap-south-1:576329196399:repository/devops-cicd-demo",
        ha="center", fontsize=9.6, color=BLUE, family="monospace")
ax.text(6.6, 1.2, "Permissions were added one at a time, each because an error named it - never by attaching a managed policy to silence a message.",
        ha="center", fontsize=8.8, color=GREY, style="italic")
save(fig, "docs/diagrams/iam-model.png")
