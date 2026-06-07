"""
Saturn Star Movers — Batch Partnership Letter Generator
Generates one print-ready PDF per contact (confirmed or probable LinkedIn status).
Outputs: letters/  (one PDF each) + letters_merged.pdf (all in one for printer)
"""

import csv, os, textwrap
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

# ── BRAND COLOURS ────────────────────────────────────────────────────────────
GOLD   = HexColor("#C9A84C")
DARK   = HexColor("#1A1A2E")
LIGHT  = HexColor("#F7F4EF")
GREY   = HexColor("#555555")

# ── KW / CAMBRIDGE / GUELPH REGION TRIGGER LIST ──────────────────────────────
KW_CITIES = {
    "kitchener","waterloo","cambridge","guelph","woodstock","ayr","breslau",
    "elmira","st. jacobs","st jacobs","st. clements","st clements",
    "new hamburg","baden","paris","brantford"
}

KW_CREDIBILITY_LONG = (
    "We recently supported a large manufacturing and engineering group in the "
    "Kitchener area with a facility/location move, so we understand the type of "
    "coordination, care, and reliability that industrial and operations-focused "
    "companies expect when moving items between locations. We enjoyed that type of "
    "work and are looking to build more relationships with companies in the "
    "Kitchener-Waterloo, Cambridge, and Guelph corridor that may occasionally need "
    "reliable moving support for facility moves, internal moves, employee relocations, "
    "office moves, or storage-related projects."
)

KW_CREDIBILITY_SHORT = (
    "We recently supported a large manufacturing and engineering group in the Kitchener "
    "area with a facility/location move, and we'd love to build more relationships with "
    "companies in the Kitchener-Waterloo, Cambridge, and Guelph corridor that may need "
    "reliable moving support from time to time."
)

# ── TITLE-BASED GROUP DETECTION ──────────────────────────────────────────────
OWNER_TITLES = {"president","owner","ceo","founder","principal","director","vp","vice president","managing director","partner","gm","general manager","proprietor"}
OPS_TITLES   = {"operations manager","plant manager","facility manager","facilities manager","production manager","site manager","manufacturing manager","supply chain","logistics","warehouse manager","maintenance manager"}
HR_TITLES    = {"hr","human resources","people","talent","recruiter","office manager","admin","administrator","executive assistant"}

def classify_title(title: str) -> str:
    t = title.lower()
    for kw in OWNER_TITLES:
        if kw in t: return "owner"
    for kw in OPS_TITLES:
        if kw in t: return "ops"
    for kw in HR_TITLES:
        if kw in t: return "hr"
    return "owner"  # default to exec-level tone

# ── LETTER BODY BUILDER ───────────────────────────────────────────────────────
def build_body(row: dict) -> list[str]:
    first_name   = row["contact_name"].strip().split()[0]
    company      = row["company"].strip()
    city         = row["city"].strip()
    title        = row["title"].strip()
    zone         = row["zone"].strip()
    group        = classify_title(title)
    is_kw        = city.lower() in KW_CITIES

    # Derive a friendly region label from zone string
    if "Windsor" in zone or "Essex" in zone:
        region = "Windsor-Essex"
    elif "Chatham" in zone:
        region = "Chatham-Kent"
    elif "Sarnia" in zone or "Lambton" in zone:
        region = "Sarnia-Lambton"
    elif "London" in zone:
        region = "London"
    elif "Kitchener" in zone or "Waterloo" in zone or "Cambridge" in zone or "Guelph" in zone:
        region = "Kitchener-Waterloo and surrounding area"
    elif "Woodstock" in zone or "Brantford" in zone:
        region = "Woodstock-Brantford corridor"
    else:
        region = city

    # Opening paragraph — varies by group
    if group == "owner":
        opening = (
            f"My name is John, owner of Saturn Star Movers. We're a fully insured local "
            f"moving company serving {region}, and I wanted to personally reach out to "
            f"introduce our company to {company}."
        )
    elif group == "ops":
        opening = (
            f"My name is John, from Saturn Star Movers — a fully insured local moving "
            f"company serving {region}. I wanted to reach out because we work closely with "
            f"operations and facilities teams at manufacturing and industrial companies in the area."
        )
    else:  # hr
        opening = (
            f"My name is John, from Saturn Star Movers — a fully insured local moving "
            f"company serving {region}. I'm reaching out because we've built a simple "
            f"employee moving benefit program that HR and people teams at local companies "
            f"have found genuinely useful."
        )

    # Core value paragraph — varies by group
    if group == "owner":
        value_para = (
            f"We're looking to build long-term relationships with established companies "
            f"in the area that may occasionally need reliable moving support — whether for "
            f"staff relocations, office moves, internal facility moves, storage moves, or "
            f"employee discount programs. For a company like {company}, moving needs usually "
            f"show up in different ways: a manager relocates, a new hire moves into the area, "
            f"an office gets rearranged, or a last-minute move comes up and someone needs a "
            f"reliable local contact."
        )
    elif group == "ops":
        value_para = (
            f"For operations teams at manufacturing and industrial companies, moving needs "
            f"tend to come up more often than expected — internal furniture or equipment moves, "
            f"facility rearrangements, overflow labour when your team is stretched, storage "
            f"moves, or last-minute support outside normal operations. Instead of scrambling "
            f"to find reliable help, we'd like to be the local contact {company} can call "
            f"when any of those situations arise."
        )
    else:
        value_para = (
            f"We offer a preferred-rate moving program for employees at no cost to the "
            f"company. Anyone connected to {company} gets a discounted moving rate, priority "
            f"scheduling when available, and a dedicated contact — making it an easy benefit "
            f"to offer your team without any budget commitment."
        )

    # KW credibility insert
    kw_para = None
    if is_kw:
        kw_para = KW_CREDIBILITY_LONG if len(KW_CREDIBILITY_LONG) < 400 else KW_CREDIBILITY_SHORT

    # Closing paragraph
    closing = (
        f"There's no commitment required from your end. We'd simply like to become a trusted "
        f"local moving contact for {company} whenever a need comes up. We can also set up a "
        f"preferred-rate program for your employees as an added benefit — at no cost to the company."
    )

    cta = "Would you be open to a quick 10-minute introduction call this week or next?"

    paragraphs = [opening, value_para]
    if kw_para:
        paragraphs.append(kw_para)
    paragraphs.append(closing)
    paragraphs.append(cta)

    return first_name, paragraphs

# ── BULLET SERVICES LIST ──────────────────────────────────────────────────────
SERVICES = [
    "Employee relocations",
    "Office and facility moves",
    "Internal furniture or equipment moves",
    "Storage-related moves",
    "Last-minute moving labour",
    "Preferred moving discounts for staff",
]

# ── PDF PAGE BUILDER ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter   # 612 x 792 pts
MARGIN = 0.85 * inch

def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["header_company"] = ParagraphStyle(
        "header_company", fontName="Helvetica-Bold",
        fontSize=18, textColor=white, leading=22,
        spaceAfter=2
    )
    styles["header_tagline"] = ParagraphStyle(
        "header_tagline", fontName="Helvetica",
        fontSize=9, textColor=HexColor("#E8D5A3"), leading=12
    )
    styles["date_line"] = ParagraphStyle(
        "date_line", fontName="Helvetica",
        fontSize=10, textColor=GREY, leading=14, spaceAfter=6
    )
    styles["recipient"] = ParagraphStyle(
        "recipient", fontName="Helvetica-Bold",
        fontSize=11, textColor=DARK, leading=16, spaceAfter=2
    )
    styles["recipient_detail"] = ParagraphStyle(
        "recipient_detail", fontName="Helvetica",
        fontSize=10, textColor=GREY, leading=14, spaceAfter=2
    )
    styles["subject"] = ParagraphStyle(
        "subject", fontName="Helvetica-Bold",
        fontSize=11, textColor=DARK, leading=16,
        spaceBefore=10, spaceAfter=8
    )
    styles["salutation"] = ParagraphStyle(
        "salutation", fontName="Helvetica-Bold",
        fontSize=11, textColor=DARK, leading=16, spaceAfter=8
    )
    styles["body"] = ParagraphStyle(
        "body", fontName="Helvetica",
        fontSize=10.5, textColor=DARK, leading=17,
        alignment=TA_JUSTIFY, spaceAfter=10
    )
    styles["bullet_header"] = ParagraphStyle(
        "bullet_header", fontName="Helvetica-Bold",
        fontSize=10.5, textColor=DARK, leading=16, spaceAfter=4
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontName="Helvetica",
        fontSize=10.5, textColor=DARK, leading=16,
        leftIndent=16, spaceAfter=3
    )
    styles["sign_name"] = ParagraphStyle(
        "sign_name", fontName="Helvetica-Bold",
        fontSize=11, textColor=DARK, leading=16, spaceBefore=4
    )
    styles["sign_detail"] = ParagraphStyle(
        "sign_detail", fontName="Helvetica",
        fontSize=10, textColor=GREY, leading=14
    )
    styles["footer"] = ParagraphStyle(
        "footer", fontName="Helvetica",
        fontSize=8, textColor=HexColor("#999999"),
        alignment=TA_CENTER, leading=11
    )
    return styles

def draw_header_bg(c, doc):
    """Dark header band with gold accent stripe."""
    c.saveState()
    header_h = 1.15 * inch
    c.setFillColor(DARK)
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=1, stroke=0)
    # gold accent stripe
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - header_h - 4, PAGE_W, 4, fill=1, stroke=0)
    c.restoreState()

def draw_footer(c, doc):
    c.saveState()
    c.setFillColor(DARK)
    c.rect(0, 0, PAGE_W, 0.45 * inch, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, 0.45 * inch, PAGE_W, 2, fill=1, stroke=0)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#AAAAAA"))
    c.drawCentredString(PAGE_W / 2, 0.17 * inch,
        "Saturn Star Movers  |  Fully Insured  |  Serving Windsor-Essex, Chatham-Kent, Sarnia, London, Kitchener-Waterloo & Surrounding Areas")
    c.restoreState()

def on_page(c, doc):
    draw_header_bg(c, doc)
    draw_footer(c, doc)

def generate_letter_pdf(row: dict, out_path: str, logo_path: str = None):
    first_name, paragraphs = build_body(row)
    styles = make_styles()

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.45 * inch,   # space for header band
        bottomMargin=0.7 * inch,
    )

    story = []

    # ── HEADER CONTENT (drawn over the dark bg by on_page) ───────────────────
    # We put the company name text as a floating element via the canvas callback.
    # Here we just reserve vertical space — actual text is in on_page via a second pass.
    # Instead, embed header text into the story at the very top with a negative spacer trick.
    # Simpler: use a Table flush to the page top.

    # Header text block (sits inside the dark band via topMargin alignment)
    # We achieve this by adding a small block that lives inside topMargin area —
    # handled by drawing directly in on_page below.

    # ── DATE ─────────────────────────────────────────────────────────────────
    from datetime import date
    story.append(Paragraph(date.today().strftime("%B %d, %Y"), styles["date_line"]))
    story.append(Spacer(1, 0.08 * inch))

    # ── RECIPIENT BLOCK ──────────────────────────────────────────────────────
    story.append(Paragraph(row["contact_name"].strip(), styles["recipient"]))
    story.append(Paragraph(row["title"].strip(), styles["recipient_detail"]))
    story.append(Paragraph(row["company"].strip(), styles["recipient_detail"]))
    story.append(Paragraph(row["city"].strip(), styles["recipient_detail"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=10))

    # ── SUBJECT LINE ─────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Re: Preferred Moving Support for {row['company'].strip()} — Staff & Facility Moves",
        styles["subject"]
    ))

    # ── SALUTATION ───────────────────────────────────────────────────────────
    story.append(Paragraph(f"Hi {first_name},", styles["salutation"]))

    # ── BODY PARAGRAPHS ──────────────────────────────────────────────────────
    for i, para in enumerate(paragraphs):
        # Insert services bullet list after 2nd paragraph
        if i == 2:
            story.append(Paragraph("We can help your company and team with:", styles["bullet_header"]))
            for svc in SERVICES:
                story.append(Paragraph(f"• {svc}", styles["bullet"]))
            story.append(Spacer(1, 0.06 * inch))
        story.append(Paragraph(para, styles["body"]))

    # ── SIGNATURE ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Warm regards,", styles["body"]))
    story.append(Spacer(1, 0.35 * inch))  # signature space
    story.append(HRFlowable(width=2 * inch, thickness=1, color=GOLD, spaceAfter=4))
    story.append(Paragraph("John Owolabi", styles["sign_name"]))
    story.append(Paragraph("Owner, Saturn Star Movers", styles["sign_detail"]))
    story.append(Paragraph("Phone: [Your Phone Number]", styles["sign_detail"]))
    story.append(Paragraph("Email: [Your Email]", styles["sign_detail"]))
    story.append(Paragraph("Website: [Your Website]", styles["sign_detail"]))

    # ── CUSTOM ON_PAGE that also writes header text ───────────────────────────
    def on_page_with_header(c, doc):
        on_page(c, doc)
        # Header text
        c.saveState()
        if logo_path and os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, MARGIN, PAGE_H - 1.05 * inch,
                            width=1.1 * inch, height=0.75 * inch,
                            preserveAspectRatio=True, mask="auto")
                text_x = MARGIN + 1.25 * inch
            except Exception:
                text_x = MARGIN
        else:
            text_x = MARGIN
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(white)
        c.drawString(text_x, PAGE_H - 0.60 * inch, "Saturn Star Movers")
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#E8D5A3"))
        c.drawString(text_x, PAGE_H - 0.80 * inch,
                     "Local · Insured · Reliable  |  Residential & Commercial Moving")
        c.restoreState()

    doc.build(story, onFirstPage=on_page_with_header, onLaterPages=on_page_with_header)


# ── ENVELOPE PDF BUILDER ──────────────────────────────────────────────────────
ENV_W = 9.5 * inch   # #10 envelope
ENV_H = 4.125 * inch

def generate_envelope_pdf(rows: list[dict], out_path: str, logo_path: str = None):
    """Single PDF with one page per envelope (print-and-fold ready)."""
    from reportlab.pdfgen import canvas as cv_mod
    c = cv_mod.Canvas(out_path, pagesize=(ENV_W, ENV_H))

    return_name  = "John Owolabi"
    return_co    = "Saturn Star Movers"
    return_addr  = "[Your Return Address]"
    return_city  = "[City, Province  Postal Code]"

    for row in rows:
        if not row.get("contact_name","").strip():
            continue
        c.setFillColor(LIGHT)
        c.rect(0, 0, ENV_W, ENV_H, fill=1, stroke=0)

        # Gold accent left stripe
        c.setFillColor(GOLD)
        c.rect(0, 0, 3, ENV_H, fill=1, stroke=0)

        # Return address — top left
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(DARK)
        c.drawString(0.3 * inch, ENV_H - 0.45 * inch, return_co)
        c.setFont("Helvetica", 7.5)
        c.drawString(0.3 * inch, ENV_H - 0.60 * inch, return_name)
        c.drawString(0.3 * inch, ENV_H - 0.74 * inch, return_addr)
        c.drawString(0.3 * inch, ENV_H - 0.88 * inch, return_city)

        # Recipient — centred/right
        rx = ENV_W * 0.42
        ry = ENV_H * 0.55
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(DARK)
        c.drawString(rx, ry,       row["contact_name"].strip())
        c.setFont("Helvetica", 10)
        c.drawString(rx, ry - 0.22*inch, row["title"].strip())
        c.drawString(rx, ry - 0.42*inch, row["company"].strip())
        c.drawString(rx, ry - 0.62*inch, row["city"].strip() + ", Ontario")

        # Stamp box placeholder
        c.setStrokeColor(GREY)
        c.setFillColor(white)
        c.rect(ENV_W - 1.1*inch, ENV_H - 1.0*inch, 0.85*inch, 0.70*inch, fill=1, stroke=1)
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        c.drawCentredString(ENV_W - 0.675*inch, ENV_H - 0.65*inch, "STAMP")

        c.showPage()

    c.save()


# ── MERGE PDFS ────────────────────────────────────────────────────────────────
def merge_pdfs(pdf_paths: list[str], out_path: str):
    """Merge PDFs using pdftk (system) or reportlab page-copy fallback."""
    import subprocess, shutil
    if shutil.which("pdftk"):
        result = subprocess.run(["pdftk"] + pdf_paths + ["cat", "output", out_path],
                                capture_output=True)
        if result.returncode == 0:
            return
    # Fallback: copy pages via reportlab's canvas
    try:
        from reportlab.pdfgen import canvas as _cv
        from reportlab.lib.pagesizes import letter as _ltr
        import io
        # Use pikepdf if available, else skip merge
        try:
            import pikepdf
            pdf_out = pikepdf.Pdf.new()
            for p in pdf_paths:
                src = pikepdf.open(p)
                pdf_out.pages.extend(src.pages)
            pdf_out.save(out_path)
            return
        except ImportError:
            pass
    except Exception:
        pass
    print(f"  ⚠  Could not merge PDFs automatically. Individual files are in letters/")
    print(f"     To merge manually: pdftk letters/*.pdf cat output letters_merged.pdf")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def load_contacts() -> list[dict]:
    files = [
        "enrichment_results/results_01_tier1A.csv",
        "enrichment_results/results_02_tier1B.csv",
        "enrichment_results/results_03_tier2.csv",
    ]
    base = Path(__file__).parent
    contacts = []
    for f in files:
        with open(base / f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                status = row.get("linkedin_status","").strip().lower()
                name   = row.get("contact_name","").strip()
                if name and ("confirmed" in status or "probable" in status):
                    contacts.append(row)
    return contacts


def main(logo_path: str = None):
    out_dir  = Path(__file__).parent / "letters"
    env_dir  = Path(__file__).parent / "envelopes"
    out_dir.mkdir(exist_ok=True)
    env_dir.mkdir(exist_ok=True)

    contacts = load_contacts()
    print(f"Generating letters for {len(contacts)} contacts...")

    letter_pdfs   = []
    envelope_rows = []
    skipped       = 0

    for i, row in enumerate(contacts, 1):
        name_slug = (
            row["contact_name"].strip().replace(" ", "_").replace("/","")[:30]
            + "_" +
            row["company"].strip().replace(" ", "_").replace("/","")[:25]
        )
        # sanitise for filesystem
        for ch in r'\:*?"<>|,':
            name_slug = name_slug.replace(ch, "")

        pdf_path = str(out_dir / f"{i:03d}_{name_slug}.pdf")
        try:
            generate_letter_pdf(row, pdf_path, logo_path=logo_path)
            letter_pdfs.append(pdf_path)
            envelope_rows.append(row)
            if i % 25 == 0 or i == len(contacts):
                print(f"  {i}/{len(contacts)} done...")
        except Exception as e:
            print(f"  ⚠  Skipped {row['contact_name']} / {row['company']}: {e}")
            skipped += 1

    # Merged letters PDF
    merged_path = str(Path(__file__).parent / "letters_merged.pdf")
    print(f"\nMerging {len(letter_pdfs)} letters → letters_merged.pdf ...")
    merge_pdfs(letter_pdfs, merged_path)

    # Envelopes PDF
    env_path = str(Path(__file__).parent / "envelopes_all.pdf")
    print(f"Generating envelopes → envelopes_all.pdf ...")
    generate_envelope_pdf(envelope_rows, env_path, logo_path=logo_path)

    print(f"\n✓ Done.")
    print(f"  Letters  : letters/  ({len(letter_pdfs)} individual PDFs)")
    print(f"  Merged   : letters_merged.pdf  (send this to printer)")
    print(f"  Envelopes: envelopes_all.pdf   (#10 envelope layout)")
    if skipped:
        print(f"  Skipped  : {skipped} rows (errors logged above)")


if __name__ == "__main__":
    import sys
    logo = sys.argv[1] if len(sys.argv) > 1 else None
    main(logo_path=logo)
