"""Builds Balaji's one-page resume.

The layout is measured, not guessed: after building, the page count and the
lowest y-coordinate carrying text are printed, so "one full page" is verified
rather than assumed. Tune the size constants below if content changes.
"""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, KeepTogether,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

OUT = os.environ.get("RESUME_OUT", "resume/Balaji-S-Resume.pdf")

# One knob scales every type size and leading proportionally. The value is set
# by measurement (see build/sweep_resume.py): the largest scale that still fits
# on a single page wins, so the page is full without spilling over.
SCALE = float(os.environ.get("RESUME_SCALE", "1.07"))

INK = colors.HexColor("#16202a")
MUTED = colors.HexColor("#4a5560")
ACCENT = colors.HexColor("#1f6b4a")
RULE = colors.HexColor("#c2ccd4")

NAME_SIZE = 21 * SCALE
TAG_SIZE = 9.4 * SCALE
CONTACT_SIZE = 8.5 * SCALE
HEAD_SIZE = 9.4 * SCALE
BODY_SIZE = 8.7 * SCALE
LEAD_RATIO = float(os.environ.get("RESUME_LEAD_RATIO", "1.26"))
BODY_LEAD = BODY_SIZE * LEAD_RATIO
META_SIZE = 8.2 * SCALE
GAP_SECTION = float(os.environ.get("RESUME_GAP", "4.5"))

PAGE_W, PAGE_H = A4
SIDE_MM = float(os.environ.get("RESUME_SIDE_MM", "14"))
LM = RM = SIDE_MM * mm
TM = float(os.environ.get("RESUME_TOP_MM", "9")) * mm
BM = float(os.environ.get("RESUME_BOTTOM_MM", "8")) * mm

name = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=NAME_SIZE,
                      leading=NAME_SIZE + 2, textColor=INK, alignment=TA_CENTER,
                      spaceAfter=1)
tag = ParagraphStyle("tag", fontName="Helvetica", fontSize=TAG_SIZE,
                     leading=TAG_SIZE + 2.4, textColor=ACCENT, alignment=TA_CENTER,
                     spaceBefore=1)
contact = ParagraphStyle("contact", fontName="Helvetica", fontSize=CONTACT_SIZE,
                         leading=CONTACT_SIZE + 2.6, textColor=MUTED,
                         alignment=TA_CENTER)
head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=HEAD_SIZE,
                      leading=HEAD_SIZE + 1.5, textColor=INK, spaceBefore=0,
                      spaceAfter=0, alignment=TA_LEFT)
body = ParagraphStyle("body", fontName="Helvetica", fontSize=BODY_SIZE,
                      leading=BODY_LEAD, textColor=INK, alignment=TA_LEFT)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=9.5, bulletIndent=1.5,
                        spaceBefore=0.6, spaceAfter=0)
label = ParagraphStyle("label", parent=body, spaceAfter=0.8)
entry = ParagraphStyle("entry", fontName="Helvetica-Bold", fontSize=BODY_SIZE + 0.5,
                       leading=BODY_LEAD + 0.4, textColor=INK)
date = ParagraphStyle("date", fontName="Helvetica-Oblique", fontSize=META_SIZE,
                      leading=BODY_LEAD + 0.2, textColor=MUTED, alignment=2)
meta = ParagraphStyle("meta", fontName="Helvetica-Oblique", fontSize=META_SIZE,
                      leading=BODY_LEAD, textColor=MUTED, spaceAfter=1.5)


def section(title):
    """Section heading with a hairline rule, matching the site's accent colour."""
    return [Spacer(1, GAP_SECTION),
            Paragraph(title.upper(), head),
            HRFlowable(width="100%", thickness=0.7, color=RULE,
                       spaceBefore=1.5, spaceAfter=3.0)]


def titled(left, right, min_rows=None):
    """Title on the left, date on the right, aligned to the same baseline."""
    t = Table([[Paragraph(left, entry), Paragraph(right, date)]],
              colWidths=[PAGE_W - LM - RM - 42 * mm, 42 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
    ]))
    return t


def b(text):
    return Paragraph(text, bullet, bulletText="\u2022")


story = []
A = story.append

# ------------------------------------------------------------------ header
A(Paragraph("BALAJI S", name))
A(Paragraph("Infrastructure &amp; Cloud Engineering &nbsp;|&nbsp; AWS &nbsp;|&nbsp; CI/CD &nbsp;|&nbsp; Systems Administration", tag))
A(Spacer(1, 2.5))
A(Paragraph("Bengaluru, India &nbsp;&middot;&nbsp; +91 7259742213 &nbsp;&middot;&nbsp; balaji.techy22@gmail.com &nbsp;&middot;&nbsp; s.balaji@cmr.edu.in", contact))
A(Paragraph("linkedin.com/in/balaji-s-4688692ba &nbsp;&middot;&nbsp; github.com/Balaji7259 &nbsp;&middot;&nbsp; Live demo: 15.252.179.238", contact))

# ----------------------------------------------------------------- summary
for f in section("Professional Summary"):
    A(f)
A(Paragraph(
    "Computer Science Engineering graduate (2026 batch) with hands-on experience building and operating cloud "
    "infrastructure on AWS. Designed and shipped an end-to-end CI/CD pipeline that takes a <i>git push</i> to a "
    "running container in under a minute &mdash; Docker, GitHub Actions, Amazon ECR and EC2 &mdash; with keyless "
    "deployment through AWS Systems Manager and automatic rollback when a health check fails. Strong in systems "
    "administration, VPC and security-group fundamentals, and IAM least privilege; comfortable in Python, Java, "
    "SQL and JavaScript.", body))

# ------------------------------------------------------------ competencies
for f in section("Core Competencies"):
    A(f)
for line in [
    ("Cloud &amp; Infrastructure", "AWS (EC2, ECR, IAM, VPC, Security Groups, S3, DynamoDB), Systems Manager, Elastic IP"),
    ("CI/CD &amp; Containers", "Docker, GitHub Actions, Amazon ECR, immutable image tagging, automated rollback, Git/GitHub"),
    ("Systems Administration", "Linux (Ubuntu, Amazon Linux 2023), Bash, Nginx, PM2, Windows OS fundamentals"),
    ("Diagnostics &amp; Automation", "Root-cause analysis, process automation, IAM role configuration, deployment troubleshooting"),
    ("Integration &amp; Development", "REST APIs, Node.js, Express.js, Flask, React.js, JWT authentication"),
    ("Data &amp; Languages", "MySQL, DynamoDB (GSI/Boto3), relational database concepts, Java, Python, SQL, JavaScript"),
]:
    A(Paragraph(f"<b>{line[0]}:</b> {line[1]}", label))

# --------------------------------------------------------------- education
for f in section("Education"):
    A(f)
A(titled("B.Tech in Computer Science Engineering &mdash; CMR University, Bengaluru", "Dec 2022 &ndash; May 2026"))
A(Paragraph("CGPA: 8.54", meta))
A(Spacer(1, 2.6))
A(titled("Pre-University (PCMC) &mdash; Govt Pre-University College, Yelahanka", "Jun 2020 &ndash; Jun 2022"))
A(Paragraph("Percentage: 81%", meta))

# -------------------------------------------------------------- internship
for f in section("Internship Experience"):
    A(f)
A(titled("Data Visualization Intern &mdash; Virtual Internship Program", ""))
A(b("Diagnosed data quality issues in raw datasets and applied cleaning, preprocessing and validation to improve the "
    "reliability of reporting outputs."))
A(b("Built interactive dashboards and charts to support data-driven decisions, collaborating cross-functionally on "
    "analytics workflows and documentation."))

# ---------------------------------------------------------------- projects
for f in section("Infrastructure &amp; Cloud Projects"):
    A(f)

A(KeepTogether([
    titled("Automated CI/CD Deployment Pipeline", "2026"),
    Paragraph("AWS &middot; Docker &middot; GitHub Actions &middot; Amazon ECR &middot; EC2 &middot; Systems Manager &middot; IAM", meta),
    b("Built a push-to-production pipeline: GitHub Actions builds the image, smoke-tests the routes the site serves, "
      "and publishes it to Amazon ECR under an immutable commit-SHA tag, so every deployed artefact maps to a commit "
      "and any earlier version can be redeployed."),
    b("Replaced SSH with AWS Systems Manager RunCommand: no key, no inbound SSH rule, one public port, and every "
      "production command recorded with its output."),
    b("Implemented automatic rollback &mdash; the deploy script polls <i>/healthz</i> and restores the previous image if the "
      "new container stays unhealthy, then still exits non-zero so the failure stays visible; proven against a broken "
      "image on the live instance."),
    b("Scoped two least-privilege identities (CI: push/pull on one repository plus SendCommand on one instance; "
      "instance role: pull-only) and cut commit-to-live to 40&ndash;55 seconds."),
]))

A(Spacer(1, 3.2))
A(KeepTogether([
    titled("CloudDrive &mdash; Cloud Storage Web Application", "2026"),
    Paragraph("React &middot; Node.js &middot; Express &middot; MySQL &middot; AWS S3 &middot; EC2 &middot; Nginx &middot; PM2", meta),
    b("Provisioned and deployed a full-stack application on AWS EC2 (Ubuntu), with PM2 for process management and "
      "Nginx as a reverse proxy for frontend and backend traffic."),
    b("Integrated Amazon S3 for secure file storage, built REST APIs for file operations, and implemented JWT-based "
      "authentication."),
    b("Modelled user and file-metadata records in MySQL and consumed the REST endpoints from a React.js frontend, "
      "keeping authentication state client-side through JWT."),
]))

A(Spacer(1, 3.2))
A(KeepTogether([
    titled("Cloud-Deployed Tic-Tac-Toe Application", "2026"),
    Paragraph("AWS &middot; Python &middot; Flask &middot; DynamoDB &middot; IAM &middot; Security Groups", meta),
    b("Deployed a Flask application on Amazon EC2 with scoped security groups, integrating DynamoDB via Boto3 for "
      "persistent state and Global Secondary Index querying."),
    b("Configured IAM roles for least-privilege EC2-to-DynamoDB access and modernised the app from Python 2/Boto to "
      "Python 3/Boto3 on Amazon Linux 2023."),
]))

# ----------------------------------------------------------- certifications
for f in section("Certifications"):
    A(f)
A(b("Database Management Systems &mdash; Infosys Springboard (2025)"))
A(b("Python for Data Science &mdash; IBM Cognitive Classes (2023)"))
A(b("React JS &mdash; GeeksforGeeks (2025)"))


def build():
    doc = BaseDocTemplate(OUT, pagesize=A4,
                          leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM,
                          title="Balaji S - Resume", author="Balaji S",
                          subject="Infrastructure and Cloud Engineering resume")
    frame = Frame(LM, BM, PAGE_W - LM - RM, PAGE_H - TM - BM, id="page",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="one", frames=[frame])])
    doc.build(story)


def report():
    import pymupdf
    d = pymupdf.open(OUT)
    print(f"pages: {d.page_count}")
    low = 0.0
    for page in d:
        for block in page.get_text("blocks"):
            low = max(low, block[3])
        usable_bottom = page.rect.height - BM
        print(f"  page bottom edge: {page.rect.height:.1f}pt, last text y: {low:.1f}pt, "
              f"remaining space: {usable_bottom - low:.1f}pt")
    d.close()


if __name__ == "__main__":
    build()
    report()




