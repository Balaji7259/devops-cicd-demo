"""Cover, table of contents, and the orientation page."""
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from pdf_lib import (BLUE, FRAME_W, GREY, LIGHT, NAVY, P, S, H2, bullet, callout,
                     grid_table, _rule)


def cover():
    from reportlab.lib.styles import ParagraphStyle

    kicker = ParagraphStyle("coverKicker", fontName="Helvetica-Bold", fontSize=9, leading=12,
                            textColor=colors.HexColor("#8CC0DC"))
    big = ParagraphStyle("coverTitle", fontName="Helvetica-Bold", fontSize=28, leading=33,
                         textColor=colors.white)
    sub = ParagraphStyle("coverSub", fontName="Helvetica", fontSize=11.5, leading=16,
                         textColor=colors.HexColor("#C9DCEA"))

    title_block = Table(
        [[Paragraph("BUILD LOG  \u00b7  NOVEMBER 2026", kicker)],
         [Paragraph("Automated CI/CD", big)],
         [Paragraph("Deployment Pipeline", big)],
         [Spacer(1, 8)],
         [Paragraph("AWS  \u00b7  Docker  \u00b7  GitHub Actions  \u00b7  nginx", sub)]],
        colWidths=[FRAME_W])
    title_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 26),
        ("RIGHTPADDING", (0, 0), (-1, -1), 26),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (0, 0), 26),
        ("BOTTOMPADDING", (0, -1), (0, -1), 28),
    ]))

    facts = grid_table(
        [["Repository", "github.com/Balaji7259/devops-cicd-demo"],
         ["Live site", "http://13.126.168.131  (health endpoint: /healthz)"],
         ["Cloud", "AWS ap-south-1 (Mumbai) - ECR + EC2 t3.micro"],
         ["Pipeline", "4 gated jobs, 40-55 seconds end to end"],
         ["Rollback", "workflow dispatch with an image tag - same gates"],
         ["Identity", "1 IAM user for CI, 1 IAM role for the server, both repo-scoped"]],
        ["Item", "Value"], widths=[0.26, 0.74])

    return [
        Spacer(1, 1.4 * cm),
        title_block,
        Spacer(1, 1.0 * cm),
        P("Every command in this document was executed against a real AWS account. "
          "Every error quoted here actually happened, and the fix beside it is the fix that worked. "
          "Nothing is illustrative.", "lead"),
        Spacer(1, 6),
        facts,
        Spacer(1, 8),
        callout("This document is written for someone who has never deployed anything. "
                "It explains what each command does before showing it, and says where to run it - "
                "Windows PowerShell, the EC2 terminal, or the AWS console, because mixing those up "
                "is the first way people get stuck.", "note"),
        PageBreak(),
    ]


def contents():
    from reportlab.lib.styles import ParagraphStyle

    lvl0 = ParagraphStyle("TOCLevel0", fontName="Helvetica-Bold", fontSize=10,
                          leading=18, textColor=NAVY, spaceBefore=6)
    lvl1 = ParagraphStyle("TOCLevel1", fontName="Helvetica", fontSize=8.6,
                          leading=12.4, leftIndent=16,
                          textColor=colors.HexColor("#33475B"))

    toc = TableOfContents()
    toc.levelStyles = [lvl0, lvl1]

    out = [
        Paragraph("Contents", S["h1nc"]),
        _rule(BLUE, 2.2),
        Spacer(1, 10),
        toc,
        Spacer(1, 16),
        H2("0.1", "How to read this"),
        P("The project was built in three phases, and the document follows that order. "
          "Each phase ends with a working, verifiable result, which is why the phases were not "
          "merged into one long sequence."),
    ]
    out += [
        bullet("<b>Part 1</b> explains the problem and the vocabulary. Read it even if you know "
               "what Docker is - the terms are used precisely later."),
        bullet("<b>Part 2</b> builds the application and gets it running on your own laptop."),
        bullet("<b>Part 3</b> moves it to a real server in AWS, by hand, so that every step is visible."),
        bullet("<b>Part 4</b> automates all of Part 3, and adds the checks that make automation trustworthy."),
        bullet("<b>Part 5</b> explains how the pieces work together, what the design costs, and what "
               "is deliberately still missing."),
        Spacer(1, 6),
        H2("0.2", "A note on where commands run"),
        P("Commands appear in two very different places, and confusing them is the most common "
          "cause of being stuck:"),
        grid_table(
            [["<b>PowerShell</b> on your laptop",
              "Building images, pushing to ECR, git commands, SSH into the server."],
             ["<b>The EC2 terminal</b>",
              "Installing Docker, pulling images, running containers. The prompt shows "
              "<font face='Courier'>ubuntu@ip-172-31-...</font>"],
             ["<b>AWS console</b>",
              "Creating the repository, security group, instance, IAM roles and policies - "
              "anything that is click-driven rather than a command."]],
            ["Where", "What happens there"], widths=[0.3, 0.7]),
        callout("Wherever a command belongs in a specific place, the caption above it says so. "
                "If a command fails with 'not recognized' or 'command not found', check that "
                "caption first - it is almost always the wrong window.", "warn"),
        PageBreak(),
    ]
    return out
