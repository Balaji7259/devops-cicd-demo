"""Finds the largest type scale that still keeps the resume on one page.

Builds the resume at a range of scales into a temp file, measures each result
with PyMuPDF, and reports pages and the lowest text position. Nothing is left
to judgement: the winner is the biggest scale whose page count is still 1 and
whose last line sits inside the frame.
"""

import os
import subprocess
import sys
import tempfile

import pymupdf

FRAME_BOTTOM = None  # resolved per run


def build_at(scale, out):
    env = dict(os.environ, RESUME_SCALE=str(scale), RESUME_OUT=out)
    r = subprocess.run([sys.executable, "build/make_resume.py"], env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()[-300:]

    d = pymupdf.open(out)
    pages = d.page_count
    last = max((blk[3] for p in d for blk in p.get_text("blocks")), default=0.0)
    bm_mm = float(os.environ.get("RESUME_BOTTOM_MM", "10"))
    bottom_edge = d[0].rect.height - bm_mm * 2.8346
    d.close()
    return {"pages": pages, "last": last, "bottom_edge": bottom_edge}, None


def main():
    results = []
    scales = [1.06, 1.065, 1.07, 1.075, 1.08]
    tmp = tempfile.gettempdir()
    for s in scales:
        out = os.path.join(tmp, f"resume_scale_{s}.pdf")
        data, err = build_at(s, out)
        if err:
            print(f"{s:.2f}  BUILD ERROR {err}")
            continue
        room = data["bottom_edge"] - data["last"]
        ok = data["pages"] == 1 and room > -0.5
        results.append((s, data["pages"], room, ok))
        print(f"{s:.2f}  pages={data['pages']}  last={data['last']:6.1f}pt  "
              f"room={room:+6.1f}pt  {'FIT' if ok else 'overflows'}")
        if data["pages"] > 1:
            break

    fits = [r for r in results if r[3]]
    if not fits:
        print("no scale fits")
        return
    best = max(fits, key=lambda r: r[0])
    print(f"\nlargest fitting scale: {best[0]:.2f} (room {best[2]:+.1f}pt)")


if __name__ == "__main__":
    main()



