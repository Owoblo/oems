"""
Saturn Star Movers — Batch Partnership Letter Generator
Clean one-page letter: plain white, branch-specific address, logo top-right,
thin margins, bold phone, personal founder tone.

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
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

NAVY  = HexColor("#1B2A6B")
GOLD  = HexColor("#F5A800")
GREY  = HexColor("#333333")
LGREY = HexColor("#666666")

PAGE_W, PAGE_H = letter
ML = 0.65 * inch
MR = 0.65 * inch
MT = 0.70 * inch
MB = 0.55 * inch

SSM_CELL = "226-724-1730"

BRANCHES = {
    "windsor": {
        "address1": "3608 Seminole Street, Unit 3",
        "city":     "Windsor, ON  N8Y 1Y4",
        "phone":    "(226) 773-2993",
        "email":    "windsor@starmovers.ca",
        "website":  "starmovers.ca/windsor-movers/",
    },
    "chatham": {
        "address1": "220 St Clair Street",
        "city":     "Chatham, ON  N7L 3J8",
        "phone":    "226-605-5767",
        "email":    "chatham@starmovers.ca",
        "website":  "starmovers.ca/chatham-movers/",
    },
    "london": {
        "address1": "390 Saskatoon St, Unit 207D",
        "city":     "London, ON  N5W 4R3",
        "phone":    "(548) 488-3245",
        "email":    "london@starmovers.ca",
        "website":  "starmovers.ca/london-movers/",
    },
    "kitchener": {
        "address1": "Kitchener, ON",
        "city":     "",
        "phone":    "226-780-6649",
        "email":    "kitchener@starmovers.ca",
        "website":  "starmovers.ca/kitchener-movers/",
    },
    "waterloo": {
        "address1": "550 Parkside Drive, Unit B13",
        "city":     "Waterloo, ON  N2L 5V4",
        "phone":    "226-780-7014",
        "email":    "waterloo@starmovers.ca",
        "website":  "starmovers.ca/waterloo-movers/",
    },
    "guelph": {
        "address1": "55 Cedar Drive",
        "city":     "Guelph, ON  N1G 1C4",
        "phone":    "226-780-3158",
        "email":    "guelph@starmovers.ca",
        "website":  "starmovers.ca/guelph-movers/",
    },
}

def branch_for_zone(zone, city):
    z = zone.lower()
    c = city.lower()
    if "zone 2" in z or "chatham" in z or "chatham" in c:
        return BRANCHES["chatham"]
    if "zone 4" in z or "london" in z or "london" in c:
        return BRANCHES["london"]
    if "zone 5" in z or "woodstock" in z or "woodstock" in c or "brantford" in c:
        return BRANCHES["guelph"]
    if "zone 6" in z or "kitchener" in z or "kitchener" in c or "cambridge" in c:
        return BRANCHES["kitchener"]
    if "waterloo" in z or "waterloo" in c:
        return BRANCHES["waterloo"]
    if "guelph" in z or "guelph" in c:
        return BRANCHES["guelph"]
    return BRANCHES["windsor"]

KW_CITIES = {
    "kitchener","waterloo","cambridge","guelph","woodstock","ayr","breslau",
    "elmira","st. jacobs","st jacobs","st. clements","st clements",
    "new hamburg","baden","paris","brantford",
}

OWNER_KW = {"president","owner","ceo","founder","principal","gm","general manager",
            "managing director","vp","vice president","director","partner","proprietor"}
OPS_KW   = {"operations manager","plant manager","facility","production manager",
            "site manager","manufacturing manager","supply chain","logistics",
            "warehouse manager","maintenance manager"}

def classify(title):
    t = title.lower()
    for k in OWNER_KW:
        if k in t: return "owner"
    for k in OPS_KW:
        if k in t: return "ops"
    return "owner"

def region_label(zone, city):
    z = zone.lower()
    if "zone 1" in z or "windsor" in z or "essex" in z: return "Windsor-Essex"
    if "zone 2" in z or "chatham" in z:                 return "Chatham-Kent"
    if "zone 3" in z or "sarnia" in z or "lambton" in z: return "Sarnia-Lambton"
    if "zone 4" in z or "london" in z:                  return "London"
    if "zone 5" in z or "woodstock" in z:               return "Woodstock-Oxford"
    if "zone 6" in z:                                    return "Kitchener-Waterloo"
    return city

def build_content(row):
    first   = row["contact_name"].strip().split()[0]
    company = row["company"].strip()
    city    = row["city"].strip()
    title   = row["title"].strip()
    zone    = row.get("zone", "")
    group   = classify(title)
    is_kw   = city.lower() in KW_CITIES or "zone 6" in zone.lower()
    region  = region_label(zone, city)
    branch  = branch_for_zone(zone, city)

    if group == "owner":
        p1 = (
            f"My name is John Owolabi, and I am the founder of <i>Saturn Star Movers</i>, "
            f"a fast-growing, fully insured moving company serving the "
            f"<b>{region}</b> area. {first}, I am reaching out to you personally because "
            f"<b>{company}</b> is exactly the kind of company we would be proud to build "
            f"a long-term relationship with."
        )
        p2 = (
            f"Companies like <b>{company}</b> deal with moving situations throughout the year: "
            f"a manager relocates, a new hire moves into the area, an office gets rearranged, "
            f"or furniture needs to shift between locations. Right now, someone on your team "
            f"is handling that scramble. I want to take it off their plate, and off yours."
        )
    else:
        p1 = (
            f"My name is John Owolabi, founder of <i>Saturn Star Movers</i>, "
            f"a fully insured moving company serving the <b>{region}</b> area. "
            f"{first}, I am reaching out because operations teams at companies like "
            f"<b>{company}</b> are often the first to feel the pain when a moving "
            f"need comes up with no reliable contact in place."
        )
        p2 = (
            f"For plant and operations teams at <b>{company}</b>, it comes up more than "
            f"you would expect: internal equipment moves, facility rearrangements, employee "
            f"relocations, overflow labour when the team is stretched, or last-minute "
            f"support that falls outside normal operations. Instead of scrambling, "
            f"I want your team to already have a number to call."
        )

    kw_line = None
    if is_kw:
        kw_line = (
            f"We recently supported a large manufacturing and engineering group in the "
            f"<b>Kitchener</b> area with a full facility move, so we understand the level "
            f"of coordination and care that industrial companies expect. "
            f"We are actively building more partnerships like that across "
            f"<b>Kitchener-Waterloo, Cambridge, and Guelph</b>."
        )

    p3 = (
        f"Here is what I am proposing for <b>{company}</b>, at no cost to the company: "
        f"a preferred-rate partnership where your employees receive a dedicated discount "
        f"on any local or long-distance move, priority scheduling, and a direct line to "
        f"me personally. Your team pays less. Your company pays nothing. "
        f"And {first}, you get to offer your people something genuinely useful."
    )

    cta = (
        f"I would love a quick 10-minute call with you, {first}. "
        f"Call or text me directly at <b>{SSM_CELL}</b> and I will make it easy on your end."
    )

    return dict(first=first, company=company, city=city, region=region,
                p1=p1, p2=p2, kw_line=kw_line, p3=p3, cta=cta, branch=branch)


def draw_letterhead(c, branch, logo_path):
    logo_w, logo_h = 1.3*inch, 1.0*inch
    logo_x = PAGE_W - MR - logo_w
    logo_y = PAGE_H - MT - logo_h + 0.1*inch
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, logo_x, logo_y,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(NAVY)
    c.drawString(ML, PAGE_H - MT - 0.14*inch, "Saturn Star Movers")

    c.setFont("Helvetica", 8.5)
    c.setFillColor(LGREY)
    ay = PAGE_H - MT - 0.32*inch
    addr_lines = [branch["address1"]]
    if branch["city"]:
        addr_lines.append(branch["city"])
    addr_lines += [branch["phone"], branch["email"]]
    for line in addr_lines:
        c.drawString(ML, ay, line)
        ay -= 0.135*inch

    rule_y = PAGE_H - MT - 0.95*inch
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(ML, rule_y, PAGE_W - MR, rule_y)


def generate_letter(row, out_path, logo_path=None):
    data   = build_content(row)
    branch = data["branch"]
    today  = date.today().strftime("%B %d, %Y")

    c = pdfcanvas.Canvas(out_path, pagesize=letter)
    draw_letterhead(c, branch, logo_path)

    text_w = PAGE_W - ML - MR
    x = ML
    y = PAGE_H - MT - 1.12*inch

    body_s = ParagraphStyle("b", fontName="Helvetica", fontSize=10.2,
                             leading=15.8, textColor=GREY, alignment=4)
    bul_s  = ParagraphStyle("bl", fontName="Helvetica", fontSize=10.0,
                             leading=14.8, textColor=GREY, leftIndent=12)

    def write(text, style, gap=0.13):
        p = Paragraph(text, style)
        _, h = p.wrap(text_w, 999)
        p.drawOn(c, x, y - h)
        return y - h - gap * inch

    c.setFont("Helvetica", 9.5)
    c.setFillColor(LGREY)
    c.drawString(x, y, today)
    y -= 0.26*inch

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(GREY)
    c.drawString(x, y, f"Hi {data['first']},")
    y -= 0.28*inch

    for para in [data["p1"], data["p2"]]:
        y = write(para, body_s, 0.12)

    y -= 0.04*inch
    y = write(f"Here is what the partnership includes for <b>{data['company']}</b>:", body_s, 0.08)
    for b in [
        "A <b>dedicated staff discount</b> on all local and long-distance moves",
        "<b>Full-service support</b>: packing, transport, unloading, and everything between",
        "A <b>Personal Moving Concierge</b>: one dedicated contact from start to finish",
        "<b>Priority scheduling</b> and on-time pickup and delivery, guaranteed",
        "<b>Licensed and fully insured</b>: your people and their belongings are protected",
    ]:
        y = write(f"  &#8226;  {b}", bul_s, 0.06)
    y -= 0.06*inch

    if data["kw_line"]:
        y = write(data["kw_line"], body_s, 0.12)

    y = write(data["p3"], body_s, 0.12)
    y = write(data["cta"], body_s, 0.18)

    c.setFont("Helvetica", 10)
    c.setFillColor(GREY)
    c.drawString(x, y, "Warm regards,")
    y -= 0.38*inch

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(black)
    c.drawString(x, y, "John Owolabi")
    y -= 0.17*inch

    c.setFont("Helvetica", 10)
    c.setFillColor(LGREY)
    c.drawString(x, y, "Founder, Saturn Star Movers")
    y -= 0.17*inch

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(NAVY)
    c.drawString(x, y, SSM_CELL + "  (Direct)")
    y -= 0.17*inch

    c.setFont("Helvetica", 9.5)
    c.setFillColor(LGREY)
    c.drawString(x, y, f"{branch['phone']}   |   {branch['email']}")
    y -= 0.17*inch
    c.drawString(x, y, branch["website"])

    c.save()


ENV_W, ENV_H = 9.5*inch, 4.125*inch

def generate_envelopes(rows, out_path, logo_path=None):
    c = pdfcanvas.Canvas(out_path, pagesize=(ENV_W, ENV_H))
    for row in rows:
        if not row.get("contact_name", "").strip():
            continue
        br = branch_for_zone(row.get("zone", ""), row.get("city", ""))
        c.setFillColor(white)
        c.rect(0, 0, ENV_W, ENV_H, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.rect(0, 0, 3, ENV_H, fill=1, stroke=0)
        c.rect(0, 0, ENV_W, 0.20*inch, fill=1, stroke=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.line(3, 0.20*inch, ENV_W, 0.20*inch)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(NAVY)
        c.drawString(0.28*inch, ENV_H - 0.35*inch, "Saturn Star Movers")
        c.setFont("Helvetica", 7.5)
        c.setFillColor(LGREY)
        ret_lines = [br["address1"]]
        if br["city"]:
            ret_lines.append(br["city"])
        ret_lines.append(br["phone"])
        for i, line in enumerate(ret_lines):
            c.drawString(0.28*inch, ENV_H - 0.50*inch - i*0.13*inch, line)

        rx, ry = ENV_W * 0.38, ENV_H * 0.58
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(black)
        c.drawString(rx, ry, row["contact_name"].strip())
        c.setFont("Helvetica", 10)
        c.setFillColor(LGREY)
        c.drawString(rx, ry - 0.20*inch, row["title"].strip())
        c.drawString(rx, ry - 0.38*inch, row["company"].strip())
        c.drawString(rx, ry - 0.56*inch, row["city"].strip() + ", Ontario")

        c.setStrokeColor(LGREY)
        c.setFillColor(white)
        c.rect(ENV_W - 1.0*inch, ENV_H - 0.92*inch, 0.78*inch, 0.62*inch, fill=1, stroke=1)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(LGREY)
        c.drawCentredString(ENV_W - 0.61*inch, ENV_H - 0.60*inch, "STAMP")

        c.showPage()
    c.save()


def merge_pdfs(paths, out_path):
    try:
        import pikepdf
        out = pikepdf.Pdf.new()
        for p in paths:
            src = pikepdf.open(p)
            out.pages.extend(src.pages)
        out.save(out_path)
    except Exception as e:
        print(f"  Merge skipped ({e}). Use: pdftk letters/*.pdf cat output letters_merged.pdf")


def load_contacts():
    base = Path(__file__).parent
    contacts = []
    for f in ["enrichment_results/results_01_tier1A.csv",
              "enrichment_results/results_02_tier1B.csv",
              "enrichment_results/results_03_tier2.csv"]:
        with open(base / f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                status = row.get("linkedin_status", "").lower()
                name   = row.get("contact_name", "").strip()
                if name and ("confirmed" in status or "probable" in status):
                    contacts.append(row)
    return contacts


def main(logo_path=None):
    base    = Path(__file__).parent
    out_dir = base / "letters"
    out_dir.mkdir(exist_ok=True)

    contacts = load_contacts()
    print(f"Generating {len(contacts)} letters...")

    pdfs, env_rows = [], []
    for i, row in enumerate(contacts, 1):
        slug = (row["contact_name"].strip().replace(" ", "_")[:28] + "_" +
                row["company"].strip().replace(" ", "_")[:22])
        for ch in r'\:*?"<>|,./':
            slug = slug.replace(ch, "")
        path = str(out_dir / f"{i:03d}_{slug}.pdf")
        try:
            generate_letter(row, path, logo_path=logo_path)
            pdfs.append(path)
            env_rows.append(row)
        except Exception as e:
            print(f"  skip {row['contact_name']}: {e}")
        if i % 50 == 0 or i == len(contacts):
            print(f"  {i}/{len(contacts)}...")

    print("Merging...")
    merge_pdfs(pdfs, str(base / "letters_merged.pdf"))
    print("Envelopes...")
    generate_envelopes(env_rows, str(base / "envelopes_all.pdf"), logo_path=logo_path)
    print(f"\n✓  {len(pdfs)} letters  |  letters_merged.pdf  |  envelopes_all.pdf")


if __name__ == "__main__":
    import sys
    main(logo_path=sys.argv[1] if len(sys.argv) > 1 else None)
