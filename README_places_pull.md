# Google Places Lead Extractor — Southwestern Ontario OEMs

Extracts industrial/manufacturing company names and addresses from the
Google Places API (New) Text Search endpoint.

---

## 1. Create a Google API Key

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Select or create a project (e.g. `oems-lead-gen`).
3. Navigate to **APIs & Services → Credentials → Create Credentials → API key**.
4. Copy the key.
5. (Recommended) Restrict the key to the **Places API (New)** only under
   **API restrictions**, and add an IP restriction if running from a fixed server.

---

## 2. Enable the Correct API

In **APIs & Services → Library**, search for and enable:

- **Places API (New)**

> **Do not** enable the legacy "Places API" — the script uses the v1 endpoint
> (`places.googleapis.com/v1`).

---

## 3. Set the Environment Variable

```bash
# Linux / macOS
export GOOGLE_PLACES_API_KEY="YOUR_KEY_HERE"

# Windows (PowerShell)
$env:GOOGLE_PLACES_API_KEY = "YOUR_KEY_HERE"

# Windows (cmd)
set GOOGLE_PLACES_API_KEY=YOUR_KEY_HERE
```

You can also add it to a `.env` file and source it, but **never commit the key
to version control**.

---

## 4. Install Dependencies

```bash
pip install requests pandas
```

---

## 5. Running the Script

### Dry run — see planned queries, zero API calls

```bash
python places_pull.py --dry-run
```

### Test run — 3 cities × 3 keywords = 9 calls max

```bash
python places_pull.py --test
```

### Full run with a billing cap

```bash
python places_pull.py --full --max-calls 500
```

### Full run, unlimited (all 6 zones × all cities × all keywords)

```bash
python places_pull.py --full
```

### Custom output directory

```bash
python places_pull.py --test --output-dir ./my_output
```

---

## 6. Output Files

All files are written to `./places_output/` (or the directory you specify).

| File | Contents |
|------|----------|
| `raw_results.csv` | Every result from every API call, including duplicates |
| `deduped_companies.csv` | One row per unique company (deduped by `place_id`) |
| `run_log.csv` | One row per API call with status code and result count |

### CSV columns

`raw_results.csv` and `deduped_companies.csv`:

| Column | Source |
|--------|--------|
| `place_id` | `places.id` |
| `company_name` | `places.displayName.text` |
| `formatted_address` | `places.formattedAddress` |
| `city_searched` | The city used in the query |
| `zone` | The zone label (e.g. Zone 6 — Kitchener…) |
| `keyword_searched` | The keyword used in the query |
| `raw_query` | The full text query sent to the API |

---

## 7. Controlling Billing

The script is designed to stay in the cheapest billing tier:

- **Field mask** is locked to `places.id,places.displayName,places.formattedAddress`.
  This avoids the "Pro" SKU that is charged for fields like phone, website, hours,
  ratings, photos, etc.
- **No Place Details calls** are made — only Text Search.
- **`--max-calls N`** caps the total number of API requests per run. Start with
  `--max-calls 50` and check your Google Cloud billing dashboard before scaling up.
- **`--dry-run`** lets you see every planned query for free before spending a cent.

### Estimated cost

Google charges per Text Search call. At the time of writing, Text Search
(Basic fields only) is billed per 1,000 requests. Check the
[Places API pricing page](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)
for current rates.

Full run (all zones, all cities, all keywords) ≈ 2,700+ queries. Always test
with `--test` first and monitor your billing dashboard.

---

## 8. Deduplication Logic

1. Primary key: `place_id` (Google's stable identifier).
2. Fallback key (when `place_id` is empty):
   `lowercase(company_name) + "|" + lowercase(formatted_address)`.
3. The **first** city/keyword combination that surfaced a result is kept.
4. `raw_results.csv` always contains every hit — no deduplication applied.

---

## 9. Resuming / Re-running

Each run **overwrites** the output CSVs from scratch (headers are written fresh).
If you want to append to a prior run, merge the files manually using the
`place_id` column for deduplication:

```python
import pandas as pd
a = pd.read_csv("run1/deduped_companies.csv")
b = pd.read_csv("run2/deduped_companies.csv")
merged = pd.concat([a, b]).drop_duplicates(subset="place_id")
merged.to_csv("combined.csv", index=False)
```
