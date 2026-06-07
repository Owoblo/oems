"""
Saturn Star Movers — Batch Partnership Letter Generator
Matches the official SSM letter template: logo top-right, address top-left,
navy footer bar, pink/magenta geometric corner accent. ONE page per letter.

Usage:
    python3 generate_letters.py [logo.png]
"""

import csv, os
from pathlib import Path
from datetime import date
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY

# ── BRAND ─────────────────────────────────────────────────────────────────────
NAVY  = HexColor("#1B2A6B")   # footer bar / company name
PINK  = HexColor("#C2185B")   # geometric accent (magenta/pink)
PINK2 = HexColor("#8E0038")   # darker pink for second rectangle
GREY  = HexColor("#444444")
LGREY = HexColor("#777777")

PAGE_W, PAGE_H = letter       # 612 x 792 pts
M_LEFT  = 0.85 * inch
M_RIGHT = 0.85 * inch
M_TOP   = 1.0  * inch
M_BOT   = 0.65 * inch

# ── CONTACT INFO ──────────────────────────────────────────────────────────────
SSM_ADDRESS  = "7021 Wyandotte Street East"
SSM_CITY     = "Windsor, ON  N8S 1R1"
SSM_PHONE    = "(226) 215-9874"
SSM_EMAIL    = "business@starmovers.ca"
SSM_WEBSITE  = "www.starmovers.ca"
SSM_CELL     = "226-724-1730"

# ── KW / CAMBRIDGE / GUELPH CITIES ───────────────────────────────────────────
KW_CITIES = {
    "kitchener","waterloo","cambridge","guelph","woodstock","ayr","breslau",
    "elmira","st. jacobs","st jacobs","st. clements","st clements",
    "new hamburg","baden","paris","brantford",
}

KW_LINE = (
    "We recently supported a large manufacturing and engineering group in the Kitchener "
    "area with a facility/location move — so we understand the coordination and care that "
    "industrial companies expect. We'd love to build more relationships like that across "
    "the Kitchener-Waterloo, Cambridge, and Guelph corridor."
)

# ── TITLE GROUPS ──────────────────────────────────────────────────────────────
OWNER_KW = {"president","owner","ceo","founder","principal","gm","general manager",
            "managing director","vp","vice president","director","partner","proprietor"}
OPS_KW   = {"operations manager","plant manager","facility","production manager",
            "site manager","manufacturing manager","supply chain","logistics",
            "warehouse manager","maintenance manager"}

def classify(title: str) -> str:
    t = title.lower()
    for k in OWNER_KW:
        if k in t: return "owner"
    for k in OPS_KW:
        if k in t: return "ops"
    return "owner"

# ── LETTER CONTENT ────────────────────────────────────────────────────────────
def build_letter_text(row: dict) -> dict:
    first    = row["contact_name"].strip().split()[0]
    last     = row["contact_name"].strip().split()[-1]
    salut    = f"Mr./Ms. {last}" if classify(row["title"]) == "owner" else first
    company  = row["company"].strip()
    city     = row["city"].strip()
    title    = row["title"].strip()
    group    = classify(title)
    is_kw    = city.lower() in KW_CITIES

    zone = row.get("zone","")
    if "Windsor" in zone or "Essex" in zone:       region = "Windsor-Essex"
    elif "Chatham" in zone:                         region = "Chatham-Kent"
    elif "Sarnia" in zone or "Lambton" in zone:    region = "Sarnia-Lambton"
    elif "London" in zone:                          region = "London"
    elif any(x in zone for x in ("Kitchener","Waterloo","Cambridge","Guelph")):
                                                    region = "the Kitchener-Waterloo area"
    elif "Woodstock" in zone or "Brantford" in zone: region = "the Woodstock-Brantford corridor"
    else:                                           region = city

    # Para 1 — hook
    if group == "owner":
        p1 = (
            f"My name is John Owolabi, and I'm the founder of <i>Saturn Star Movers</i> — "
            f"a fast-growing, fully insured moving company serving {region} and surrounding areas. "
            f"I'm reaching out personally because I've been building relationships with established "
            f"companies in the area, and <b>{company}</b> stood out as exactly the kind of operation "
            f"we'd be proud to support."
        )
    else:
        p1 = (
            f"My name is John Owolabi, founder of <i>Saturn Star Movers</i> — a fully insured moving "
            f"company serving {region}. I'm reaching out because operations and facilities teams like "
            f"yours often have moving needs that come up with little notice, and I'd like "
            f"<b>{company}</b> to have a reliable local contact when that happens."
        )

    # Para 2 — the problem/opportunity
    if group == "owner":
        p2 = (
            f"Companies like <b>{company}</b> regularly deal with moving situations that fall outside "
            f"normal operations — a manager relocating, a new hire moving into the area, an office "
            f"being rearranged, or furniture shifted between locations. Right now, someone on your "
            f"team is probably handling that scramble. We'd like to take it off their plate."
        )
    else:
        p2 = (
            f"For operations and plant teams, moving situations come up constantly — internal "
            f"equipment or furniture moves, facility rearrangements, employee relocations, overflow "
            f"labour when your team is stretched, or last-minute support outside normal operations. "
            f"Instead of scrambling, we want to be the number your team already has."
        )

    # KW insert
    p_kw = KW_LINE if is_kw else None

    # Para 3 — the offer
    p3 = (
        f"I'd love to set up a simple preferred-rate partnership with <b>{company}</b> — "
        f"no commitment required. Your employees get a dedicated discount on any local or "
        f"long-distance move, priority scheduling, and a direct line to me personally. "
        f"The company pays nothing. It's purely a benefit for your people."
    )

    # CTA
    cta = (
        "Would you be open to a quick 10-minute call this week or next? "
        f"You can reach me directly at <b>{SSM_CELL}</b> — or simply reply and I'll make "
        "it easy on your end."
    )

    return dict(first=first, salut=salut, p1=p1, p2=p2, p_kw=p_kw, p3=p3, cta=cta,
                company=company, city=city)

# ── DRAW TEMPLATE CHROME ──────────────────────────────────────────────────────
def draw_chrome(c, logo_path=None):
    """Navy footer bar + pink geometric corner accent + letterhead."""
    # Footer bar
    footer_h = 0.38 * inch
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, footer_h, fill=1, stroke=0)

    # Pink geometric shapes — bottom right corner (two overlapping rectangles)
    # Larger pink block
    c.saveState()
    c.setFillColor(PINK)
    c.transform(1, 0, 0, 1, 0, 0)
    # Rectangle rotated ~15 deg, anchored bottom-right
    c.saveState()
    c.translate(PAGE_W - 0.3*inch, footer_h)
    c.rotate(15)
    c.setFillColor(PINK)
    c.rect(0, 0, 1.8*inch, 2.2*inch, fill=1, stroke=0)
    c.restoreState()
    # Second darker rectangle
    c.saveState()
    c.translate(PAGE_W - 0.05*inch, footer_h)
    c.rotate(15)
    c.setFillColor(PINK2)
    c.rect(0, 0, 1.0*inch, 2.2*inch, fill=1, stroke=0)
    c.restoreState()
    # Clip everything above the bottom 2.5 inches to avoid overlap with text area
    # (just paint over with white above the accent zone)
    c.setFillColor(white)
    c.rect(0, 2.6*inch, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.restoreState()

    # ── LETTERHEAD ────────────────────────────────────────────────────────────
    # Logo — top right
    logo_x = PAGE_W - M_RIGHT - 1.5*inch
    logo_y = PAGE_H - M_TOP - 0.85*inch
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, logo_x, logo_y,
                        width=1.5*inch, height=1.0*inch,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Company name — top left, in navy/blue
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M_LEFT, PAGE_H - M_TOP - 0.18*inch, "Saturn Star Movers")

    # Address block
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GREY)
    addr_y = PAGE_H - M_TOP - 0.38*inch
    for line in [SSM_ADDRESS, SSM_CITY, SSM_PHONE, SSM_EMAIL]:
        c.drawString(M_LEFT, addr_y, line)
        addr_y -= 0.145*inch

    # Thin separator line under letterhead
    sep_y = PAGE_H - M_TOP - 0.92*inch
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.setLineWidth(0.5)
    c.line(M_LEFT, sep_y, PAGE_W - M_RIGHT, sep_y)


# ── GENERATE SINGLE LETTER ────────────────────────────────────────────────────
def generate_letter(row: dict, out_path: str, logo_path: str = None):
    data   = build_letter_text(row)
    today  = date.today().strftime("%B %d, %Y")

    c = pdfcanvas.Canvas(out_path, pagesize=letter)
    draw_chrome(c, logo_path)

    # ── TEXT AREA ─────────────────────────────────────────────────────────────
    # Start below letterhead separator
    text_top = PAGE_H - M_TOP - 1.08*inch
    x        = M_LEFT
    text_w   = PAGE_W - M_LEFT - M_RIGHT

    def draw_para(text, y, font="Helvetica", size=10.0, leading=15.5,
                  color=GREY, bold_parts=True, max_width=None):
        """Draw a paragraph using reportlab's textobject with simple bold/italic support."""
        from reportlab.platypus import Paragraph as Pgraph
        from reportlab.lib.styles import ParagraphStyle
        style = ParagraphStyle("tmp", fontName=font, fontSize=size,
                               leading=leading, textColor=color,
                               alignment=4 if bold_parts else 0,  # justify
                               spaceAfter=0)
        p = Pgraph(text, style)
        w, h = p.wrap(max_width or text_w, 999)
        p.drawOn(c, x, y - h)
        return y - h

    # Date
    c.setFont("Helvetica", 10)
    c.setFillColor(GREY)
    c.drawString(x, text_top, today)
    y = text_top - 0.28*inch

    # Recipient block
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(black)
    c.drawString(x, y, f"Hi {data['salut']},")
    y -= 0.32*inch

    # Body paragraphs
    paras = [data["p1"], data["p2"]]

    # Insert bullet offer block after p2
    BULLETS = [
        "A <b>dedicated discount</b> on all local and long-distance moves",
        "<b>Full-service support</b> — packing, transport, unloading, and everything between",
        "A <b>Personal Moving Concierge</b> — one dedicated contact from start to finish",
        "<b>Priority scheduling</b> and on-time pickup & delivery, guaranteed",
        "<b>Licensed & fully insured</b> — your team and belongings are always protected",
    ]

    if data["p_kw"]:
        paras.append(data["p_kw"])
    paras.append(data["p3"])
    paras.append(data["cta"])

    body_style = ParagraphStyle("body", fontName="Helvetica", fontSize=10.0,
                                leading=15.5, textColor=GREY, alignment=4)
    bullet_style = ParagraphStyle("bul", fontName="Helvetica", fontSize=9.8,
                                  leading=14.5, textColor=GREY, leftIndent=14)

    for i, para in enumerate(paras):
        p = Paragraph(para, body_style)
        pw, ph = p.wrap(text_w, 999)
        if y - ph < M_BOT + 0.5*inch:
            break  # safety — shouldn't happen on one page
        p.drawOn(c, x, y - ph)
        y -= ph + 0.16*inch

        # Insert bullets after para index 1 (after p2)
        if i == 1:
            y -= 0.06*inch
            intro = Paragraph("Here's what the partnership includes, at <b>no cost to your company</b>:", body_style)
            iw, ih = intro.wrap(text_w, 999)
            intro.drawOn(c, x, y - ih)
            y -= ih + 0.1*inch
            for b in BULLETS:
                bp = Paragraph(f"• {b}", bullet_style)
                bw, bh = bp.wrap(text_w - 14, 999)
                bp.drawOn(c, x, y - bh)
                y -= bh + 0.07*inch
            y -= 0.1*inch

    # ── SIGNATURE ─────────────────────────────────────────────────────────────
    y -= 0.05*inch
    sig_style = ParagraphStyle("sig", fontName="Helvetica", fontSize=10,
                               leading=14, textColor=GREY)
    c.setFont("Helvetica", 10)
    c.setFillColor(GREY)
    c.drawString(x, y, "Warm regards,")
    y -= 0.42*inch   # space for handwritten signature

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(black)
    c.drawString(x, y, "John Owolabi")
    y -= 0.18*inch
    c.setFont("Helvetica", 10)
    c.setFillColor(GREY)
    for line in [f"Founder, Saturn Star Movers",
                 f"Cell: {SSM_CELL}  |  {SSM_EMAIL}  |  {SSM_WEBSITE}"]:
        c.drawString(x, y, line)
        y -= 0.17*inch

    c.save()


# ── ENVELOPE GENERATOR ────────────────────────────────────────────────────────
ENV_W = 9.5 * inch
ENV_H = 4.125 * inch

def generate_envelopes(rows, out_path, logo_path=None):
    c = pdfcanvas.Canvas(out_path, pagesize=(ENV_W, ENV_H))
    for row in rows:
        if not row.get("contact_name","").strip():
            continue
        # White background
        c.setFillColor(white)
        c.rect(0, 0, ENV_W, ENV_H, fill=1, stroke=0)
        # Navy left stripe
        c.setFillColor(NAVY)
        c.rect(0, 0, 4, ENV_H, fill=1, stroke=0)
        # Navy bottom bar
        c.rect(0, 0, ENV_W, 0.22*inch, fill=1, stroke=0)

        # Return address
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(NAVY)
        c.drawString(0.3*inch, ENV_H - 0.38*inch, "Saturn Star Movers")
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GREY)
        for i, line in enumerate([SSM_ADDRESS, SSM_CITY, SSM_PHONE]):
            c.drawString(0.3*inch, ENV_H - 0.55*inch - i*0.13*inch, line)

        # Recipient
        rx, ry = ENV_W * 0.40, ENV_H * 0.60
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(black)
        c.drawString(rx, ry, row["contact_name"].strip())
        c.setFont("Helvetica", 10)
        c.setFillColor(GREY)
        c.drawString(rx, ry - 0.20*inch, row["title"].strip())
        c.drawString(rx, ry - 0.38*inch, row["company"].strip())
        c.drawString(rx, ry - 0.56*inch, row["city"].strip() + ", Ontario")

        # Stamp box
        c.setStrokeColor(GREY)
        c.setFillColor(white)
        c.rect(ENV_W - 1.05*inch, ENV_H - 0.95*inch, 0.8*inch, 0.65*inch, fill=1, stroke=1)
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        c.drawCentredString(ENV_W - 0.65*inch, ENV_H - 0.63*inch, "STAMP")

        c.showPage()
    c.save()


# ── MERGE ─────────────────────────────────────────────────────────────────────
def merge_pdfs(paths, out_path):
    try:
        import pikepdf
        out = pikepdf.Pdf.new()
        for p in paths:
            src = pikepdf.open(p)
            out.pages.extend(src.pages)
        out.save(out_path)
    except Exception as e:
        print(f"  ⚠  Merge skipped ({e}). Individual files are in letters/")
        print(f"     Manual merge: pdftk letters/*.pdf cat output letters_merged.pdf")


# ── LOAD CONTACTS ─────────────────────────────────────────────────────────────
def load_contacts():
    base = Path(__file__).parent
    files = [
        "enrichment_results/results_01_tier1A.csv",
        "enrichment_results/results_02_tier1B.csv",
        "enrichment_results/results_03_tier2.csv",
    ]
    contacts = []
    for f in files:
        with open(base / f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                status = row.get("linkedin_status","").lower()
                name   = row.get("contact_name","").strip()
                if name and ("confirmed" in status or "probable" in status):
                    contacts.append(row)
    return contacts


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main(logo_path=None):
    base     = Path(__file__).parent
    out_dir  = base / "letters"
    out_dir.mkdir(exist_ok=True)

    contacts = load_contacts()
    print(f"Generating {len(contacts)} letters...")

    letter_pdfs   = []
    envelope_rows = []

    for i, row in enumerate(contacts, 1):
        slug = (row["contact_name"].strip().replace(" ","_")[:28] + "_" +
                row["company"].strip().replace(" ","_")[:22])
        for ch in r'\:*?"<>|,./':
            slug = slug.replace(ch, "")
        pdf_path = str(out_dir / f"{i:03d}_{slug}.pdf")
        try:
            generate_letter(row, pdf_path, logo_path=logo_path)
            letter_pdfs.append(pdf_path)
            envelope_rows.append(row)
        except Exception as e:
            print(f"  ⚠  {row['contact_name']} / {row['company']}: {e}")
        if i % 50 == 0 or i == len(contacts):
            print(f"  {i}/{len(contacts)}...")

    merged = str(base / "letters_merged.pdf")
    print(f"Merging → letters_merged.pdf ...")
    merge_pdfs(letter_pdfs, merged)

    env_path = str(base / "envelopes_all.pdf")
    print(f"Envelopes → envelopes_all.pdf ...")
    generate_envelopes(envelope_rows, env_path, logo_path=logo_path)

    print(f"\n✓  {len(letter_pdfs)} letters  |  letters_merged.pdf  |  envelopes_all.pdf")


if __name__ == "__main__":
    import sys
    logo = sys.argv[1] if len(sys.argv) > 1 else None
    main(logo_path=logo)
