"""
Industrial corridor sweeper.
For every proven industrial street (3+ companies already found), geocode
one reference point then do a 1km Nearby Search to catch all businesses
Google didn't surface via keyword queries.
"""

import csv
import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

GEOCODE_URL    = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL     = "https://places.googleapis.com/v1/places:searchNearby"
FIELD_MASK     = "places.id,places.displayName,places.formattedAddress"
NEARBY_RADIUS  = 1000          # metres — covers whole industrial street
MIN_COMPANIES  = 3             # only sweep corridors we already know have this many
REQUEST_DELAY  = 0.4
RETRY_DELAYS   = [2, 4, 8]

RAW_COLS = [
    "place_id", "company_name", "formatted_address",
    "city_searched", "zone", "keyword_searched", "raw_query",
]
LOG_COLS = [
    "timestamp", "street", "sample_address",
    "lat", "lng", "status_code",
    "raw_results", "new_results", "error_message",
]

ONTARIO_PAT   = re.compile(r',\s*ON\b|,\s*Ontario\b', re.IGNORECASE)
ADDR_NAME_PAT = re.compile(
    r'^\d+\s+\w|^unit\s*[#\d]|^lot\s*[#\d]|^suite\s*[#\d]|^bay\s*[#\d]',
    re.IGNORECASE
)

def is_ontario(addr):    return bool(ONTARIO_PAT.search(str(addr)))
def is_addr_name(name):  return bool(ADDR_NAME_PAT.match(str(name).strip()))

def dedup_key(place_id, name, address):
    if place_id:
        return f"id:{place_id}"
    return f"na:{str(name).lower().strip()}|{str(address).lower().strip()}"

def extract_street(addr):
    if not isinstance(addr, str): return None
    addr = re.sub(r'\b(?:unit|suite|ste|bay|lot|bldg)\s*[#]?\s*[\w-]+|#[\w-]+', '', addr, flags=re.IGNORECASE)
    m = re.match(r'^\s*\d+[-\d]*\s+(.+?),', addr.strip())
    return m.group(1).strip() if m else None

# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def geocode(address: str, api_key: str) -> tuple[float, float, str]:
    """Returns (lat, lng, error). Retries on failure."""
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(GEOCODE_URL, params={"address": address, "key": api_key}, timeout=15)
            data = r.json()
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"], ""
            return 0.0, 0.0, data.get("status", "UNKNOWN")
        except requests.RequestException as e:
            if attempt == len(RETRY_DELAYS):
                return 0.0, 0.0, str(e)
    return 0.0, 0.0, "Failed after retries"

# ---------------------------------------------------------------------------
# Nearby Search
# ---------------------------------------------------------------------------

def nearby_search(lat: float, lng: float, api_key: str) -> tuple[int, list, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    payload = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(NEARBY_RADIUS),
            }
        },
        "maxResultCount": 20,
        "rankPreference": "DISTANCE",
    }
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            print(f"    Rate-limited. Retry {attempt}/3 in {delay}s…")
            time.sleep(delay)
        try:
            r = requests.post(NEARBY_URL, json=payload, headers=headers, timeout=30)
        except requests.RequestException as e:
            return 0, [], str(e)
        if r.status_code == 429:
            continue
        if r.status_code != 200:
            return r.status_code, [], r.text[:300]
        results = []
        for p in r.json().get("places", []):
            addr = p.get("formattedAddress", "")
            name = (p.get("displayName") or {}).get("text", "")
            if not is_ontario(addr) or is_addr_name(name):
                continue
            results.append({
                "place_id": p.get("id", ""),
                "company_name": name,
                "formatted_address": addr,
                "city_searched": "",
                "zone": "",
                "keyword_searched": "corridor_nearby_search",
                "raw_query": f"nearby:{lat},{lng}@{NEARBY_RADIUS}m",
            })
        return r.status_code, results, ""
    return 429, [], "Rate-limited after all retries"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(output_dir: str):
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY not set.")
        sys.exit(1)

    dedup_path = os.path.join(output_dir, "deduped_companies.csv")
    raw_path   = os.path.join(output_dir, "raw_results.csv")
    new_path   = os.path.join(output_dir, "corridor_new_companies.csv")
    log_path   = os.path.join(output_dir, "corridor_run_log.csv")

    # Load existing companies
    existing = pd.read_csv(dedup_path)
    seen_keys = set()
    for _, row in existing.iterrows():
        seen_keys.add(dedup_key(row["place_id"], row["company_name"], row["formatted_address"]))
    print(f"Loaded {len(seen_keys)} existing companies")

    # Build corridor list (streets with MIN_COMPANIES+ already found)
    existing["street"] = existing["formatted_address"].apply(extract_street)
    corridors = (
        existing.groupby("street")
        .agg(companies=("company_name", "count"),
             sample_address=("formatted_address", "first"),
             zone=("zone", "first"),
             city=("city_searched", "first"))
        .reset_index()
    )
    corridors = corridors[corridors["companies"] >= MIN_COMPANIES].sort_values("companies", ascending=False)
    print(f"Corridors to sweep (≥{MIN_COMPANIES} companies): {len(corridors)}")
    print(f"Estimated cost: ~${len(corridors) * 0.037:.2f} USD (geocode + nearby per corridor)\n")

    # Write output headers
    with open(new_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=RAW_COLS).writeheader()
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=LOG_COLS).writeheader()

    total_new = 0
    total_raw = 0

    for i, row in enumerate(corridors.itertuples(), 1):
        print(f"[{i}/{len(corridors)}] {row.street}  ({row.companies} known)  →  {row.sample_address}")

        # 1. Geocode
        lat, lng, geo_err = geocode(row.sample_address, api_key)
        if geo_err:
            print(f"    GEOCODE ERROR: {geo_err}")
            _write_log(log_path, row.street, row.sample_address, 0, 0, 0, 0, 0, geo_err)
            time.sleep(REQUEST_DELAY)
            continue

        time.sleep(REQUEST_DELAY)

        # 2. Nearby search
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        status, results, err = nearby_search(lat, lng, api_key)

        new_here = []
        if results:
            total_raw += len(results)
            # Back-fill city/zone from corridor metadata
            for r in results:
                r["city_searched"] = row.city
                r["zone"]          = row.zone

            with open(raw_path, "a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=RAW_COLS, extrasaction="ignore").writerows(results)

            for r in results:
                key = dedup_key(r["place_id"], r["company_name"], r["formatted_address"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    new_here.append(r)

            if new_here:
                total_new += len(new_here)
                with open(dedup_path, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=RAW_COLS, extrasaction="ignore").writerows(new_here)
                with open(new_path, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=RAW_COLS, extrasaction="ignore").writerows(new_here)

        status_str = f"→ {len(results)} nearby, {len(new_here)} new" if not err else f"ERROR: {err}"
        print(f"    {status_str}")

        _write_log(log_path, row.street, row.sample_address, lat, lng, status, len(results), len(new_here), err)
        time.sleep(REQUEST_DELAY)

    print(f"\n{'='*60}")
    print(f"  Corridors swept : {len(corridors)}")
    print(f"  Raw nearby hits : {total_raw}")
    print(f"  NEW companies   : {total_new}")
    print(f"{'='*60}")

    if total_new > 0:
        print("\nExporting updated XLSX…")
        export_xlsx(output_dir)
        print("  Done.")


def _write_log(path, street, addr, lat, lng, status, raw, new, err):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=LOG_COLS, extrasaction="ignore").writerow({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "street": street, "sample_address": addr,
            "lat": lat, "lng": lng, "status_code": status,
            "raw_results": raw, "new_results": new, "error_message": err,
        })


def export_xlsx(output_dir):
    df = pd.read_csv(os.path.join(output_dir, "deduped_companies.csv"))
    xlsx_path = os.path.join(output_dir, "deduped_companies.xlsx")
    header_fill = PatternFill(fill_type="solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    col_widths = {
        "place_id": 30, "company_name": 45, "formatted_address": 55,
        "city_searched": 20, "zone": 42, "keyword_searched": 28, "raw_query": 55,
    }
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Leads", index=False)
        ws = writer.sheets["All Leads"]
        for cell in ws[1]:
            cell.fill = header_fill; cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        for i, col in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = col_widths.get(col, 20)
        ws.freeze_panes = "A2"

        summary = (
            df.groupby("zone")
            .agg(unique_companies=("place_id", "nunique"), cities=("city_searched", "nunique"))
            .reset_index()
        )
        summary.columns = ["Zone", "Unique Companies", "Cities Covered"]
        summary.to_excel(writer, sheet_name="Summary", index=False)
        ws2 = writer.sheets["Summary"]
        for cell in ws2[1]:
            cell.fill = header_fill; cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        ws2.column_dimensions["A"].width = 45
        ws2.column_dimensions["B"].width = 22
        ws2.column_dimensions["C"].width = 18
        ws2.freeze_panes = "A2"

        for zone_name, zone_df in df.groupby("zone"):
            short = zone_name.split("—")[-1].strip().replace("/", "-")[:28]
            zone_df.to_excel(writer, sheet_name=short, index=False)
            ws3 = writer.sheets[short]
            for cell in ws3[1]:
                cell.fill = header_fill; cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            for i, col in enumerate(zone_df.columns, 1):
                ws3.column_dimensions[get_column_letter(i)].width = col_widths.get(col, 20)
            ws3.freeze_panes = "A2"


if __name__ == "__main__":
    run("./places_output")
