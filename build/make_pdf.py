"""Assemble the CI/CD handbook PDF."""
import os

from reportlab.platypus import NextPageTemplate, PageBreak

from pdf_lib import Handbook
from sec_front import contents, cover
from sec_part1 import part1, part2
from sec_part3 import part3
from sec_part4 import part4
from sec_part5 import appendices, part5
from sec_part6 import part6

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "CI-CD-Pipeline-Build-Log.pdf")


def main():
    story = []

    front = cover()
    story += front[:-1]              # everything except the trailing PageBreak
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())

    story += contents()
    story += part1()
    story += part2()
    story += part3()
    story += part4()
    story += part5()
    story += part6()
    story += appendices()

    doc = Handbook(OUT)
    doc.multiBuild(story)
    print("wrote", OUT)
    print("pages:", doc.page)


if __name__ == "__main__":
    main()
