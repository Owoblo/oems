"""
Google Places API lead extraction script for Southwestern Ontario OEM/industrial companies.
"""

import argparse
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

# ---------------------------------------------------------------------------
# Geography & keywords
# ---------------------------------------------------------------------------

ZONES = {
    "Zone 1 — Windsor / Essex County": [
        "Windsor", "LaSalle", "Tecumseh", "Amherstburg", "Lakeshore", "Belle River",
        "Comber", "Stoney Point", "St. Joachim", "Puce", "Emeryville", "Anderdon",
        "Leamington", "Kingsville", "Essex", "Harrow", "McGregor", "Cottam", "Ruthven",
        "Colchester", "Maidstone", "Wheatley",
    ],
    "Zone 2 — Chatham-Kent": [
        "Chatham", "Chatham Kent", "Tilbury", "Wallaceburg", "Dresden", "Pain Court",
        "Blenheim", "Merlin", "Charing Cross", "Cedar Springs", "Dealtown", "Ridgetown",
        "Thamesville", "Bothwell", "Highgate", "Morpeth", "Muirkirk", "Mitchell's Bay",
        "Lighthouse Cove", "Erieau", "Shrewsbury", "Erie Beach",
    ],
    "Zone 3 — Sarnia / Lambton County": [
        "Sarnia", "Point Edward", "Brights Grove", "Camlachie", "Corunna", "Mooretown",
        "Courtright", "Sombra", "Port Lambton", "St. Clair", "Dawn-Euphemia", "Petrolia",
        "Oil Springs", "Brigden", "Wyoming", "Plympton-Wyoming", "Watford", "Warwick",
        "Alvinston", "Brooke-Alvinston", "Arkona", "Forest", "Thedford", "Grand Bend",
        "Lambton Shores", "Port Franks", "Ipperwash",
    ],
    "Zone 4 — London / Middlesex": [
        "London", "Lucan", "Lucan Biddulph", "Ailsa Craig", "Parkhill", "Ilderton",
        "North Middlesex", "Strathroy", "Strathroy-Caradoc", "Mount Brydges", "Kerwood",
        "Glencoe", "Newbury", "Wardsville", "Adelaide-Metcalfe", "Southwest Middlesex",
        "Komoka", "Middlesex Centre", "Dorchester", "Thames Centre", "Thamesford",
        "Belmont", "St. Thomas", "Central Elgin", "Southwold", "Talbotville", "Shedden",
        "Fingal", "Port Stanley", "Dutton", "Dutton-Dunwich", "West Lorne", "Rodney",
        "Aylmer", "Springfield", "Malahide", "Bayham", "Vienna", "Port Burwell",
        "St. Marys", "Ingersoll",
    ],
    "Zone 5 — Woodstock / Oxford County": [
        "Woodstock", "Ingersoll", "Beachville", "Sweaburg", "Burgessville", "Otterville",
        "Norwich", "Mount Elgin", "Courtland", "Tillsonburg", "Tavistock", "Thamesford",
        "Innerkip", "East Zorra-Tavistock", "Embro", "Hickson", "Kintore", "Zorra",
        "Drumbo", "Princeton", "Plattsville", "Bright", "Delhi", "Aylmer",
    ],
    "Zone 6 — Kitchener / Waterloo / Cambridge / Guelph": [
        "Kitchener", "Waterloo", "Cambridge", "Guelph", "Elmira", "St. Jacobs",
        "Conestogo", "Breslau", "Woolwich", "New Hamburg", "Baden", "Wellesley",
        "Wilmot", "Ayr", "North Dumfries", "Puslinch", "Guelph-Eramosa", "Rockwood",
        "Fergus", "Elora", "Centre Wellington", "Drayton", "Mapleton", "Arthur",
        "Palmerston", "Stratford", "Listowel", "Paris",
    ],
}

KEYWORDS = [
    "manufacturer",
    "manufacturing company",
    "OEM manufacturer",
    "automotive parts manufacturer",
    "auto parts manufacturer",
    "machine shop",
    "CNC machine shop",
    "metal fabrication",
    "fabrication shop",
    "industrial supplier",
    "industrial equipment supplier",
    "warehouse",
    "distribution center",
    "plastics manufacturer",
    "packaging manufacturer",
    "food manufacturer",
    "tool and die maker",
    "injection molding company",
    "logistics warehouse",
    "commercial printing company",
]

# Test-mode subset
TEST_CITIES = {"Kitchener", "Cambridge", "London"}
TEST_KEYWORDS = ["manufacturer", "machine shop", "metal fabrication"]

# ---------------------------------------------------------------------------
# API constants
# ---------------------------------------------------------------------------

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.id,places.displayName,places.formattedAddress"
MAX_RESULTS_PER_QUERY = 20
REQUEST_DELAY_SECONDS = 0.5
RETRY_DELAYS = [2, 4, 8]  # seconds between retries on rate-limit

# ---------------------------------------------------------------------------
# CSV columns
# ---------------------------------------------------------------------------

RAW_COLS = [
    "place_id", "company_name", "formatted_address",
    "city_searched", "zone", "keyword_searched", "raw_query",
]
LOG_COLS = [
    "timestamp", "zone", "city", "keyword",
    "raw_query", "status_code", "number_of_results", "error_message",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_queries(zones: dict, keywords: list) -> list[dict]:
    """Return a flat list of query dicts for every city × keyword combo."""
    queries = []
    for zone, cities in zones.items():
        for city in cities:
            for keyword in keywords:
                raw_query = f"{keyword} in {city}, Ontario, Canada"
                queries.append(
                    {
                        "zone": zone,
                        "city": city,
                        "keyword": keyword,
                        "raw_query": raw_query,
                    }
                )
    return queries


def dedup_key(place_id: str, name: str, address: str) -> str:
    if place_id:
        return f"id:{place_id}"
    return f"na:{name.lower().strip()}|{address.lower().strip()}"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def open_csv_writer(filepath: str, cols: list, write_header: bool):
    """Open a CSV file in append mode, optionally writing the header first."""
    f = open(filepath, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    if write_header:
        writer.writeheader()
    return f, writer


# ---------------------------------------------------------------------------
# Core API call
# ---------------------------------------------------------------------------

def call_places_api(api_key: str, query_info: dict) -> tuple[int, list[dict], str]:
    """
    Call the Places Text Search endpoint.
    Returns (status_code, list_of_place_dicts, error_message).
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    payload = {
        "textQuery": query_info["raw_query"],
        "maxResultCount": MAX_RESULTS_PER_QUERY,
    }

    for attempt, retry_delay in enumerate([0] + RETRY_DELAYS):
        if retry_delay:
            print(f"    Rate-limited. Retrying in {retry_delay}s (attempt {attempt + 1}/3)…")
            time.sleep(retry_delay)
        try:
            resp = requests.post(PLACES_URL, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            return 0, [], str(exc)

        if resp.status_code == 429:
            continue  # retry
        if resp.status_code != 200:
            return resp.status_code, [], resp.text[:300]

        data = resp.json()
        places_raw = data.get("places", [])
        ontario_pat = re.compile(r',\s*ON\b|,\s*Ontario\b', re.IGNORECASE)
        results = []
        for p in places_raw:
            addr = p.get("formattedAddress", "")
            if not ontario_pat.search(addr):
                continue  # skip non-Ontario results
            results.append(
                {
                    "place_id": p.get("id", ""),
                    "company_name": (p.get("displayName") or {}).get("text", ""),
                    "formatted_address": addr,
                    "city_searched": query_info["city"],
                    "zone": query_info["zone"],
                    "keyword_searched": query_info["keyword"],
                    "raw_query": query_info["raw_query"],
                }
            )
        return resp.status_code, results, ""

    return 429, [], "Rate-limited after all retries"


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(args) -> None:
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()

    # Determine search scope
    if args.test:
        active_zones = {
            zone: [c for c in cities if c in TEST_CITIES]
            for zone, cities in ZONES.items()
        }
        active_zones = {z: c for z, c in active_zones.items() if c}
        active_keywords = TEST_KEYWORDS
        mode_label = "TEST"
    else:
        active_zones = ZONES
        active_keywords = KEYWORDS
        mode_label = "FULL"

    queries = build_queries(active_zones, active_keywords)
    total_planned = len(queries)
    max_calls = args.max_calls if args.max_calls is not None else total_planned

    print(f"\n{'='*60}")
    print(f"  Mode          : {mode_label}")
    print(f"  Planned calls : {total_planned}")
    print(f"  Max calls cap : {max_calls}")
    print(f"  Dry run       : {args.dry_run}")
    print(f"  Output dir    : {args.output_dir}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("DRY RUN — planned queries (first 20 shown):\n")
        for q in queries[:20]:
            print(f"  [{q['zone'].split('—')[0].strip()}] {q['raw_query']}")
        if total_planned > 20:
            print(f"  … and {total_planned - 20} more")
        print(f"\nTotal: {total_planned} queries. No API calls made.")
        return

    # Interactive full-run confirmation (only when stdin is a terminal)
    if not args.test and not args.full and sys.stdin.isatty():
        ans = input(
            f"\nAbout to run {min(total_planned, max_calls)} API calls. "
            "Continue? [y/N] "
        ).strip().lower()
        if ans != "y":
            print("Aborted.")
            return

    if not api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable is not set.")
        sys.exit(1)

    ensure_dir(args.output_dir)
    raw_path = os.path.join(args.output_dir, "raw_results.csv")
    dedup_path = os.path.join(args.output_dir, "deduped_companies.csv")
    log_path = os.path.join(args.output_dir, "run_log.csv")

    # Write fresh headers (overwrite any prior run artefacts for this session)
    for path, cols in [(raw_path, RAW_COLS), (dedup_path, RAW_COLS), (log_path, LOG_COLS)]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=cols).writeheader()

    seen_keys: set[str] = set()
    calls_made = 0
    total_raw = 0
    total_deduped = 0

    for q in queries:
        if calls_made >= max_calls:
            print(f"\nReached max-calls cap of {max_calls}. Stopping.")
            break

        calls_made += 1
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        print(f"[{calls_made}/{min(total_planned, max_calls)}] {q['raw_query']}")

        status_code, results, error_msg = call_places_api(api_key, q)

        # Log entry
        log_row = {
            "timestamp": ts,
            "zone": q["zone"],
            "city": q["city"],
            "keyword": q["keyword"],
            "raw_query": q["raw_query"],
            "status_code": status_code,
            "number_of_results": len(results),
            "error_message": error_msg,
        }
        with open(log_path, "a", newline="", encoding="utf-8") as lf:
            csv.DictWriter(lf, fieldnames=LOG_COLS, extrasaction="ignore").writerow(log_row)

        if error_msg:
            print(f"  ERROR ({status_code}): {error_msg}")
        else:
            print(f"  → {len(results)} results")

        # Append raw results
        if results:
            total_raw += len(results)
            with open(raw_path, "a", newline="", encoding="utf-8") as rf:
                w = csv.DictWriter(rf, fieldnames=RAW_COLS, extrasaction="ignore")
                w.writerows(results)

            # Deduplicate and append new entries only
            new_deduped = []
            for r in results:
                key = dedup_key(r["place_id"], r["company_name"], r["formatted_address"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    new_deduped.append(r)

            if new_deduped:
                total_deduped += len(new_deduped)
                with open(dedup_path, "a", newline="", encoding="utf-8") as df:
                    w = csv.DictWriter(df, fieldnames=RAW_COLS, extrasaction="ignore")
                    w.writerows(new_deduped)

        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\n{'='*60}")
    print(f"  Done.")
    print(f"  API calls made    : {calls_made}")
    print(f"  Raw results       : {total_raw}")
    print(f"  Deduped results   : {total_deduped}")
    print(f"  Output directory  : {args.output_dir}")
    print(f"{'='*60}")

    if total_deduped > 0:
        print("\nExporting XLSX…")
        xlsx_path = export_xlsx(args.output_dir)
        print(f"  Saved: {xlsx_path}")


# ---------------------------------------------------------------------------
# XLSX export
# ---------------------------------------------------------------------------

def export_xlsx(output_dir: str) -> str:
    """Export deduped_companies.csv to a formatted XLSX file."""
    csv_path = os.path.join(output_dir, "deduped_companies.csv")
    xlsx_path = os.path.join(output_dir, "deduped_companies.xlsx")

    df = pd.read_csv(csv_path)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # --- Main leads sheet ---
        df.to_excel(writer, sheet_name="All Leads", index=False)
        ws = writer.sheets["All Leads"]

        # Header styling
        header_fill = PatternFill(fill_type="solid", fgColor="1F4E79")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Column widths
        col_widths = {
            "place_id": 30, "company_name": 45, "formatted_address": 55,
            "city_searched": 20, "zone": 42, "keyword_searched": 28, "raw_query": 55,
        }
        for i, col in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = col_widths.get(col, 20)

        # Freeze header row
        ws.freeze_panes = "A2"

        # --- Per-zone sheets ---
        for zone_name, zone_df in df.groupby("zone"):
            short = zone_name.split("—")[-1].strip().replace("/", "-")[:28]
            zone_df.to_excel(writer, sheet_name=short, index=False)
            ws2 = writer.sheets[short]
            for cell in ws2[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for i, col in enumerate(zone_df.columns, 1):
                ws2.column_dimensions[get_column_letter(i)].width = col_widths.get(col, 20)
            ws2.freeze_panes = "A2"

        # --- Summary sheet ---
        summary = (
            df.groupby("zone")
            .agg(unique_companies=("place_id", "nunique"), cities_covered=("city_searched", "nunique"))
            .reset_index()
        )
        summary.columns = ["Zone", "Unique Companies", "Cities Covered"]
        summary.to_excel(writer, sheet_name="Summary", index=False)
        ws3 = writer.sheets["Summary"]
        for cell in ws3[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws3.column_dimensions["A"].width = 45
        ws3.column_dimensions["B"].width = 20
        ws3.column_dimensions["C"].width = 20
        ws3.freeze_panes = "A2"

    return xlsx_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Google Places API lead extractor for Southwestern Ontario OEM companies."
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned queries without making any API calls.",
    )
    mode.add_argument(
        "--test",
        action="store_true",
        help="Run a small test subset (Kitchener, Cambridge, London × 3 keywords).",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Run the full search across all cities and keywords (non-interactive).",
    )

    parser.add_argument(
        "--max-calls",
        type=int,
        default=None,
        metavar="N",
        help="Cap the total number of API calls (useful for billing control).",
    )
    parser.add_argument(
        "--output-dir",
        default="./places_output",
        metavar="DIR",
        help="Directory to write CSV output files (default: ./places_output).",
    )

    args = parser.parse_args()

    # Default to test mode if nothing specified and running interactively
    if not args.dry_run and not args.test and not args.full:
        if sys.stdin.isatty():
            print(
                "No mode specified. Use --dry-run, --test, or --full.\n"
                "Example: python places_pull.py --test"
            )
            parser.print_help()
            sys.exit(1)
        else:
            print("Non-interactive mode requires --test or --full flag.")
            sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
