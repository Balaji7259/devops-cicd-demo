"""Shared styles and flowable helpers for the CI/CD handbook."""
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Spacer,
                                Table, TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame

NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#2E86AB")
GREEN = colors.HexColor("#2A9D8F")
AMBER = colors.HexColor("#B7791F")
RED = colors.HexColor("#C14953")
GREY = colors.HexColor("#5A6B7B")
LIGHT = colors.HexColor("#F4F7FA")
CODE_BG = colors.HexColor("#F5F7FA")
EDGE = colors.HexColor("#D6DEE7")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
FRAME_W = PAGE_W - 2 * MARGIN

_ss = getSampleStyleSheet()

S = {}
S["body"] = ParagraphStyle("body", parent=_ss["BodyText"], fontName="Helvetica",
                           fontSize=9.6, leading=15.0, textColor=colors.HexColor("#22313F"),
                           alignment=TA_JUSTIFY, spaceAfter=7)
S["lead"] = ParagraphStyle("lead", parent=S["body"], fontSize=10.6, leading=16.5,
                           textColor=GREY, spaceAfter=12)
S["h1"] = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=19, leading=23,
                         textColor=NAVY, spaceBefore=6, spaceAfter=4)
S["h1kicker"] = ParagraphStyle("h1kicker", fontName="Helvetica-Bold", fontSize=8.4,
                               leading=10, textColor=BLUE, spaceAfter=2)
S["h1nc"] = ParagraphStyle("H1nc", parent=S["h1"])   # heading that is not a TOC entry
S["h2"] = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.6, leading=16,
                         textColor=NAVY, spaceBefore=14, spaceAfter=5)
S["h3"] = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.2, leading=13,
                         textColor=BLUE, spaceBefore=10, spaceAfter=3)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=12, bulletIndent=3,
                             spaceAfter=3.5, alignment=TA_LEFT)
S["code"] = ParagraphStyle("code", fontName="Courier", fontSize=7.6, leading=10.6,
                           textColor=colors.HexColor("#13202E"))
S["cell"] = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.3, leading=11.2,
                           textColor=colors.HexColor("#22313F"))
S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="Helvetica-Bold")
S["cmd"] = ParagraphStyle("cmd", fontName="Courier", fontSize=7.2, leading=10.0,
                          textColor=colors.HexColor("#0F2A44"), wordWrap="CJK")
S["codeblock"] = ParagraphStyle("codeblock", fontName="Courier", fontSize=7.6, leading=10.8,
                                textColor=colors.HexColor("#13202E"),
                                backColor=CODE_BG, borderColor=EDGE, borderWidth=0.6,
                                borderPadding=8, spaceBefore=2, spaceAfter=11)
S["caption"] = ParagraphStyle("caption", fontName="Helvetica-Oblique", fontSize=8.0,
                              leading=11, textColor=GREY, alignment=TA_CENTER, spaceBefore=4)
S["callout"] = ParagraphStyle("callout", fontName="Helvetica", fontSize=9.0, leading=13.4,
                              textColor=colors.HexColor("#22313F"))


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullet(text, style="bullet"):
    return Paragraph(text, S[style], bulletText="\u2022")


def H1(number, title, kicker=None):
    out = []
    if kicker:
        out.append(Paragraph(escape(kicker.upper()), S["h1kicker"]))
    out.append(Paragraph(f"{number}&nbsp;&nbsp;{escape(title)}", S["h1"]))
    out.append(_rule(BLUE, 2.2))
    out.append(Spacer(1, 8))
    return out


def H2(number, title):
    return Paragraph(f"{number}&nbsp;&nbsp;{escape(title)}", S["h2"])


def H3(title):
    return Paragraph(escape(title), S["h3"])


def _rule(color, thickness=0.8, space_before=2, space_after=6):
    t = Table([[""]], colWidths=[FRAME_W], rowHeights=[0.5])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), thickness, color),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return KeepTogether([Spacer(1, space_before), t, Spacer(1, space_after)])


def code_block(text, title=None):
    """Monospace block on a tinted background.

    Built as a single Paragraph rather than a Table so that long listings can
    flow across a page break instead of overflowing the frame.
    """
    body = escape(text.strip("\n")).replace(" ", "&nbsp;").replace("\n", "<br/>")
    if title:
        body = (f"<font color='#6B7B8C' size=6.9>{escape(title)}</font>"
                f"<br/><br/>{body}")
    return Paragraph(body, S["codeblock"])


def cmd_table(rows, headers=("Command", "What it does"), widths=(0.52, 0.48)):
    data = [[Paragraph(f"<b>{escape(headers[0])}</b>", S["cellb"]),
             Paragraph(f"<b>{escape(headers[1])}</b>", S["cellb"])]]
    for cmd, what in rows:
        data.append([Paragraph(escape(cmd).replace(" ", "&nbsp;"), S["cmd"]),
                     Paragraph(what, S["cell"])])
    w = [FRAME_W * widths[0], FRAME_W * widths[1]]
    t = Table(data, colWidths=w, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, EDGE),
             ("BOX", (0, 0), (-1, -1), 0.6, EDGE),
             ("LEFTPADDING", (0, 0), (-1, -1), 7),
             ("RIGHTPADDING", (0, 0), (-1, -1), 7),
             ("TOPPADDING", (0, 0), (-1, -1), 5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 9)])


def grid_table(rows, headers, widths=None, font_size=8.3):
    data = [[Paragraph(f"<b>{escape(h)}</b>", S["cellb"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(c, S["cell"]) for c in r])
    if widths is None:
        widths = [FRAME_W / len(headers)] * len(headers)
    else:
        widths = [FRAME_W * x for x in widths]
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, EDGE),
             ("BOX", (0, 0), (-1, -1), 0.6, EDGE),
             ("LEFTPADDING", (0, 0), (-1, -1), 6),
             ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 4.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 9)])


def callout(text, kind="note"):
    colors_map = {"note": (BLUE, colors.HexColor("#EFF6FA")),
                  "warn": (AMBER, colors.HexColor("#FDF6E9")),
                  "danger": (RED, colors.HexColor("#FBEEF0")),
                  "good": (GREEN, colors.HexColor("#EDF7F5"))}
    accent, bg = colors_map[kind]
    label = {"note": "NOTE", "warn": "WATCH OUT", "danger": "PITFALL", "good": "WHY THIS MATTERS"}[kind]
    inner = Table([[Paragraph(f"<font color='{accent.hexval()}'><b>{label}</b></font>"
                              f"<br/><br/>{text}", S["callout"])]],
                  colWidths=[FRAME_W - 4])
    inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    t = Table([[inner]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 2.6, accent),
                           ("LEFTPADDING", (0, 0), (-1, -1), 11),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 9),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    return KeepTogether([t, Spacer(1, 10)])


def figure(path, width_cm=16.4, caption=None):
    iw, ih = ImageReader(path).getSize()
    w = width_cm * cm
    h = w * ih / iw
    img = Image(path, width=w, height=h)
    parts = [img]
    if caption:
        parts.append(Paragraph(caption, S["caption"]))
    parts.append(Spacer(1, 10))
    return KeepTogether(parts)


class Handbook(BaseDocTemplate):
    """DocTemplate that records chapter/section entries for the table of contents."""

    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, pagesize=A4,
                                 leftMargin=MARGIN, rightMargin=MARGIN,
                                 topMargin=2.1 * cm, bottomMargin=1.9 * cm,
                                 title="Automated CI/CD Deployment Pipeline - Build Log",
                                 author="Balaji", **kw)
        frame = Frame(MARGIN, 1.9 * cm, FRAME_W, PAGE_H - 4.0 * cm, id="body")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame], onPage=self._cover_deco),
            PageTemplate(id="body", frames=[frame], onPage=self._body_deco),
        ])

    def _cover_deco(self, canv, doc):
        pass

    def _body_deco(self, canv, doc):
        canv.saveState()
        # top rule + running head
        canv.setStrokeColor(EDGE)
        canv.setLineWidth(0.6)
        canv.line(MARGIN, PAGE_H - 1.45 * cm, PAGE_W - MARGIN, PAGE_H - 1.45 * cm)
        canv.setFont("Helvetica", 7.4)
        canv.setFillColor(GREY)
        canv.drawString(MARGIN, PAGE_H - 1.25 * cm,
                        "Automated CI/CD Deployment Pipeline  \u00b7  AWS + Docker + GitHub Actions")
        canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.25 * cm, "Build Log")
        # footer
        canv.line(MARGIN, 1.45 * cm, PAGE_W - MARGIN, 1.45 * cm)
        canv.drawString(MARGIN, 1.05 * cm, "Balaji  \u00b7  November 2026")
        canv.drawRightString(PAGE_W - MARGIN, 1.05 * cm, f"page {doc.page}")
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name in ("H1", "H1nc", "H2"):
                text = flowable.getPlainText()
                level = 0 if name in ("H1", "H1nc") else 1
                key = f"toc-{self.page}-{abs(hash(text)) % 100000}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                # H1nc gives the PDF outline a valid parent without listing
                # itself in the printed contents.
                if name != "H1nc":
                    self.notify("TOCEntry", (level, text, self.page, key))
