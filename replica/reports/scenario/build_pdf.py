"""Builds the IntraForge end-to-end test report (PDF) from a scenario run.

python build_pdf.py <run-folder> <control-center-images-folder> <operations.json> <output.pdf>
"""
import datetime
import json
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

RUN, CC, OPS, OUT = sys.argv[1:5]
data = json.load(open(os.path.join(RUN, "results.json"), encoding="utf-8"))
results = data["results"]
ops = json.load(open(OPS, encoding="utf-8"))

NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#2563EB")
GREEN = colors.HexColor("#16A34A")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D97706")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
SOFT = colors.HexColor("#F1F5F9")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=14, textColor=NAVY, spaceBefore=10, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=11.5, textColor=NAVY, spaceBefore=4, spaceAfter=3)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#1E293B"))
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, leading=11, textColor=MUTED)
LABEL = ParagraphStyle("Label", parent=BODY, fontName="Helvetica-Bold", fontSize=8.5, textColor=MUTED)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.5, leading=11)
TITLE = ParagraphStyle("Title", parent=H1, fontSize=26, leading=32, alignment=TA_CENTER, spaceAfter=4)
SUB = ParagraphStyle("Sub", parent=BODY, fontSize=12, alignment=TA_CENTER, textColor=MUTED)


def esc(t):
    return (str(t) if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def badge(status):
    color = GREEN if status == "PASS" else RED if status == "FAIL" else AMBER
    return Paragraph(f'<font color="{color.hexval()}"><b>{status}</b></font>', CELL)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "IntraForge 1.5.0 - end-to-end test report (test copy, test data only)")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def image(path, width):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    return Image(path, width=width, height=width * h / w)


story = []
passed = sum(r["status"] == "PASS" for r in results)
total = len(results)
when = datetime.datetime.now().strftime("%d %B %Y, %H:%M")

# ---------------------------------------------------------------- cover
story += [Spacer(1, 3.5 * cm), Paragraph("IntraForge", TITLE),
          Paragraph("End-to-end test report", ParagraphStyle("t2", parent=TITLE, fontSize=18, textColor=BLUE)),
          Spacer(1, 0.4 * cm), Paragraph(f"Version 1.5.0 &middot; test copy &middot; {when}", SUB), Spacer(1, 1.6 * cm)]
ops_passed = sum(o["status"] == "PASS" for o in ops["checks"])
summary = Table([
    [Paragraph("<b>Browser scenario</b>", BODY), Paragraph(f'<font color="{(GREEN if passed == total else RED).hexval()}"><b>{passed} of {total} steps passed</b></font>', BODY)],
    [Paragraph("<b>Operations (backup, restore test, Control Center)</b>", BODY), Paragraph(f'<font color="{(GREEN if ops_passed == len(ops["checks"]) else RED).hexval()}"><b>{ops_passed} of {len(ops["checks"])} checks passed</b></font>', BODY)],
    [Paragraph("<b>Automated test suites</b>", BODY), Paragraph(esc(ops["suites"]), BODY)],
    [Paragraph("<b>Bugs found by this scenario</b>", BODY), Paragraph("1 (bucket page title) - fixed, retested", BODY)],
], colWidths=[8.5 * cm, 8 * cm])
summary.setStyle(TableStyle([
    ("BOX", (0, 0), (-1, -1), 0.8, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
    ("BACKGROUND", (0, 0), (0, -1), SOFT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10),
]))
story += [summary, Spacer(1, 1.2 * cm), Paragraph(
    "This report walks through IntraForge the way a shop uses it - signing in, organizing work, storing files, building a "
    "database, selling with Spare Parts and IntraForge Pay, hosting a website and publishing it on the internet - and "
    "shows, for every step, what was done, why, what should happen, what actually happened, and a screenshot of the "
    "screen at that moment.", BODY), PageBreak()]

# ---------------------------------------------------------------- how
story += [Paragraph("1. How this test was run", H1)]
for title, text in [
    ("Where", "On the IntraForge 1.5.0 <b>test copy</b> on the shop PC (https://127.0.0.1:9543), with test accounts and test data only. "
              "Your real shop (port 8443) was not touched by any step."),
    ("How", "A browser robot (Playwright, driving Google Chrome) signed in and used IntraForge like a person: it typed into the "
            "sign-in form, pressed buttons, opened pages and waited for what should appear. Where a step creates something "
            "(a bucket, a table, a website), it used IntraForge's own interface calls from inside the signed-in browser - the "
            "same calls the buttons make - and then opened the page to check the result is shown. Every step ends with a "
            "screenshot."),
    ("Real servers", "Nothing is simulated: real databases (PostgreSQL), real file storage (MinIO), the real Pay ledger, and - for "
                     "the internet steps - the real Cloudflare tunnel and your domain harmongt.uk."),
    ("Accounts", "owner@test.local (shop owner, two-step sign-in on), superadmin@test.local (Super Administrator, two-step sign-in "
                 "on), customer1 (an IntraForge Pay customer). Passwords are not printed in this report."),
    ("PASS / FAIL", "PASS: what should happen happened. FAIL: it did not - the reason is written next to the step."),
]:
    story += [Paragraph(title, H3), Paragraph(text, BODY)]

# ---------------------------------------------------------------- overview table
story += [Spacer(1, 0.5 * cm), Paragraph("2. Results at a glance", H1)]
rows = [[Paragraph("<b>#</b>", CELL), Paragraph("<b>Area</b>", CELL), Paragraph("<b>Step</b>", CELL), Paragraph("<b>Result</b>", CELL), Paragraph("<b>Time</b>", CELL)]]
for r in results:
    rows.append([Paragraph(str(r["n"]), CELL), Paragraph(esc(r["section"]), CELL), Paragraph(esc(r["title"]), CELL), badge(r["status"]), Paragraph(f'{r["seconds"]} s', CELL)])
t = Table(rows, colWidths=[0.9 * cm, 2.6 * cm, 10 * cm, 1.6 * cm, 1.5 * cm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story += [t, PageBreak()]

# ---------------------------------------------------------------- steps
story += [Paragraph("3. The scenario, step by step", H1)]
section = None
for r in results:
    block = []
    if r["section"] != section:
        section = r["section"]
        block.append(Paragraph(esc(section), H2))
    head = Table([[Paragraph(f'<b>Step {r["n"]}. {esc(r["title"])}</b>', ParagraphStyle("sh", parent=BODY, fontSize=11)), badge(r["status"])]],
                 colWidths=[15 * cm, 1.6 * cm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    block.append(head)
    detail = Table([
        [Paragraph("Why", LABEL), Paragraph(esc(r["why"]), BODY)],
        [Paragraph("What should happen", LABEL), Paragraph(esc(r["expected"]), BODY)],
        [Paragraph("What happened", LABEL), Paragraph(esc(r["actual"]), BODY)],
    ], colWidths=[3.4 * cm, 13.2 * cm])
    detail.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    block.append(detail)
    if r.get("shot") and os.path.exists(os.path.join(RUN, r["shot"])):
        block += [Spacer(1, 0.15 * cm), image(os.path.join(RUN, r["shot"]), 15.5 * cm),
                  Paragraph(f'Screenshot after step {r["n"]}.', SMALL)]
    block.append(Spacer(1, 0.5 * cm))
    story.append(KeepTogether(block))

# ---------------------------------------------------------------- operations
story += [PageBreak(), Paragraph("4. Operations: backup, restore and the Control Center", H1),
          Paragraph("These run on the shop PC rather than in the browser. They were run against the same test copy.", BODY)]
for c in ops["checks"]:
    story.append(KeepTogether([
        Table([[Paragraph(f"<b>{esc(c['title'])}</b>", BODY), badge(c["status"])]], colWidths=[15 * cm, 1.6 * cm],
              style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])),
        Paragraph(esc(c["why"]), BODY), Paragraph("<b>Result:</b> " + esc(c["actual"]), BODY), Spacer(1, 0.35 * cm)]))

story += [Paragraph("The new Control Center (rendered at the shop PC's 150 % display scaling)", H2),
          Paragraph("The redesigned Control Center (not yet installed in the shop; it ships with 1.5.1). Every window was drawn by the "
                    "real program with sample data; nothing was started or changed.", BODY)]
for name, caption in [("1-main.png", "Main window: actions on the left, the shop's state on the right."),
                      ("2-settings.png", "Settings."), ("3-shop-network.png", "Allow other PCs in this shop."),
                      ("4-restore.png", "Restore a backup (three checked steps)."), ("5-uninstall.png", "Uninstall (data choices)."),
                      ("6-output.png", "The result of an action.")]:
    p = os.path.join(CC, name)
    if os.path.exists(p):
        story.append(KeepTogether([image(p, 15.5 * cm if name == "1-main.png" else 11 * cm), Paragraph(caption, SMALL), Spacer(1, 0.4 * cm)]))

# ---------------------------------------------------------------- findings
story += [PageBreak(), Paragraph("5. What the test found", H1),
          Paragraph("Bug found and fixed", H2),
          Paragraph("<b>A bucket opened from its address showed \"Bucket\" instead of its name.</b> The bucket page only knew its "
                    "name when opened from the project page's link. A bookmark, a refresh or a typed address lost it, together with "
                    "the breadcrumb trail. Fixed: IntraForge now answers the bucket's name and project itself (with the same "
                    "permission checks as its file list, and a test that another organization cannot read it). Step 5 above is the "
                    "retest.", BODY),
          Paragraph("First run, and what was corrected in the test itself", H2),
          Paragraph(esc(ops["first_run"]), BODY),
          Paragraph("New in this version and confirmed by the scenario", H2)]
for line in ops["confirmed"]:
    story.append(Paragraph("&bull; " + esc(line), BODY))
story += [Paragraph("Not covered by this test, and why", H2)]
for line in ops["not_covered"]:
    story.append(Paragraph("&bull; " + esc(line), BODY))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                        title="IntraForge end-to-end test report", author="IntraForge")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("written", OUT)
