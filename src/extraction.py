"""
Extraction module for the Ledger OCR Project V2.6
- Standard prompt for regular ledgers (side = "NA")
- Split extraction for dual-column balance sheets like 1889.pdf (side = "left"/"right"/"center")
"""

import json
import pandas as pd
from openai import OpenAI

from src.config import OPENAI_API_KEY, MODEL_NAME, COLUMNS
from src.pdf_utils import pdf_page_to_image, pil_image_to_base64
from src.schema import (
    clean_pence_fraction,
    infer_row_type,
    calculate_confidence_score,
    apply_schema_defaults,
    normalize_empty_values,
)


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


# =============================================================================
# FILES REQUIRING SPECIAL HANDLING
# =============================================================================

COMPLEX_FILES = ["1889"]  # Dual-column balance sheets requiring split extraction


# =============================================================================
# STANDARD PROMPT (For all files except 1889)
# =============================================================================

SYSTEM_PROMPT_STANDARD = """
You are transcribing historical accounting ledgers from high-resolution scans of 18th-19th century English parish records.

PAGE STRUCTURE:
Each page typically has:
1. A PAGE TITLE at the very top (often in Latin with dates) — extract this as row_type="title"
2. A body of ledger rows with columns: [Description] [Pounds] [Shillings] [Pence]
3. A TOTAL/SUM row at the bottom (often with "Summa" or underlined) — extract as row_type="total"

ROW TYPES — You MUST classify each row correctly:
- "title" = The large heading at the very top of the page (dates, "Computus", etc.). ALWAYS extract this.
- "section_header" = Place names or labels that have NO amounts in the £/s/d columns. These serve as grouping headers.
- "entry" = Normal rows WITH amounts in the £/s/d columns.
- "total" = Sum lines, often with "Summa", underlined, or at the bottom of a section.

CRITICAL RULE FOR SECTION HEADERS:
If a row has text in the description but NO numbers in ANY of the three amount columns (pounds, shillings, pence), it is a "section_header", NOT an "entry". Do NOT skip these rows — extract them with empty amount fields.

BRACE GROUPINGS:
Some ledgers use a curly brace "{" to group multiple sub-entries under one parent entry.
When you see this pattern:
- Extract EACH line as a separate row
- Set group_brace_id to the same number for all rows in the group
- The parent entry may or may not have its own amounts

CURRENCY RULES:
- Pounds, shillings, pence must exactly match what is written (do not calculate or infer)
- SHILLINGS must be 0-19 (20 shillings = 1 pound)
- PENCE must be 0-11 (12 pence = 1 shilling)
- Pence fractions: "q" or "qd" = 1/4, "ob" = 1/2, "3q" = 3/4
- Put whole pence in amount_pence_whole, fraction in amount_pence_fraction
- If a column is blank, use empty string "" — do NOT invent values

TEXT TRANSCRIPTION:
- Preserve original spelling and spacing (e.g., "Long witnam" not "Longwitnam")
- Do not include margin notes or annotations
- For unclear writing, make your best faithful guess

OUTPUT FORMAT:
Return a JSON object with:
{
  "page_type": "ledger",
  "page_title": "the title text at top of page",
  "rows": [
    {
      "row_index": 1,
      "row_type": "title",
      "side": "NA",
      "date_raw": "",
      "description": "...",
      "amount_pounds": "",
      "amount_shillings": "",
      "amount_pence_whole": "",
      "amount_pence_fraction": "",
      "transaction_type": "",
      "group_brace_id": ""
    },
    ...
  ]
}

IMPORTANT: The "side" field must ALWAYS be "NA" for standard ledger pages.

FINAL CHECKLIST:
□ Did I include the page title as the first row?
□ Did I include section headers (rows with no amounts)?
□ Are ALL shillings values between 0-19?
□ Are ALL pence values between 0-11?
□ Is "side" set to "NA" for every row?
"""

USER_PROMPT_STANDARD = "Please read this ledger page and extract ALL rows as described. Remember to include the title row and any section headers (rows without amounts). Set side=\"NA\" for all rows."


# =============================================================================
# COMPLEX PROMPTS (For 1889.pdf - Split extraction: LEFT then RIGHT)
# =============================================================================

SYSTEM_PROMPT_LEFT = """
You are transcribing the LEFT SIDE ONLY of a dual-column historical ledger page from Exeter College.

PAGE STRUCTURE:
This page has TWO sides - you are ONLY extracting the LEFT side (Receipts/Income).
The LEFT side is everything to the LEFT of the central vertical divider.

WHAT TO EXTRACT (LEFT SIDE ONLY):
1. The PAGE TITLE at the top (this spans the full page, mark as side="center")
2. ALL rows from the LEFT column labeled "Receipts" including:
   - Section headers (A. External, B. Internal, C. From Trust Funds, etc.)
   - Entry rows with amounts
   - Total/sum rows

DO NOT extract anything from the RIGHT side (Payments) - that will be done separately.

ROW CLASSIFICATION:
- "title" = The page title at the very top (side="center")
- "section_header" = Section labels like "A. External", "Receipts" (side="left")
- "entry" = Transaction rows with amounts (side="left")
- "total" = Sum lines (side="left")

SIDE FIELD:
- "center" = Page title only
- "left" = ALL other rows (since you're only extracting the left side)

CURRENCY RULES:
- SHILLINGS must be 0-19
- PENCE must be 0-11
- Pence fractions: "q"=1/4, "ob"=1/2, "3q"=3/4

OUTPUT FORMAT:
Return a JSON object with:
{
  "page_type": "balance_sheet",
  "page_title": "...",
  "extraction_side": "left",
  "rows": [...]
}
"""

SYSTEM_PROMPT_RIGHT = """
You are transcribing the RIGHT SIDE ONLY of a dual-column historical ledger page from Exeter College.

PAGE STRUCTURE:
This page has TWO sides - you are ONLY extracting the RIGHT side (Payments/Expenditure).
The RIGHT side is everything to the RIGHT of the central vertical divider.

WHAT TO EXTRACT (RIGHT SIDE ONLY):
1. ALL rows from the RIGHT column labeled "Payments" including:
   - Section headers (A. External, B. Internal, C. University Purposes, etc.)
   - Entry rows with amounts
   - Total/sum rows

DO NOT extract the page title (already extracted) or anything from the LEFT side.

ROW CLASSIFICATION:
- "section_header" = Section labels like "A. External", "Payments" (side="right")
- "entry" = Transaction rows with amounts (side="right")
- "total" = Sum lines (side="right")

SIDE FIELD:
- "right" = ALL rows (since you're only extracting the right side)

CURRENCY RULES:
- SHILLINGS must be 0-19
- PENCE must be 0-11
- Pence fractions: "q"=1/4, "ob"=1/2, "3q"=3/4

OUTPUT FORMAT:
Return a JSON object with:
{
  "page_type": "balance_sheet",
  "extraction_side": "right",
  "rows": [...]
}
"""

USER_PROMPT_LEFT = "Extract ONLY the LEFT side (Receipts) of this ledger page. Include the page title (center) and all rows from the left column. Do NOT include anything from the right side (Payments)."

USER_PROMPT_RIGHT = "Extract ONLY the RIGHT side (Payments) of this ledger page. Do NOT include the page title or anything from the left side (Receipts)."


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_page_rows_standard(
    file_id: str,
    pdf_path: str,
    page_number: int,
    model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    """
    Extract ledger rows from a standard single-column page.
    """
    # Convert page to base64
    img = pdf_page_to_image(pdf_path, page_number)
    img_b64 = pil_image_to_base64(img)

    # Call the API
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_STANDARD},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT_STANDARD},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    content = response.choices[0].message.content.strip()

    # Parse JSON response
    raw = content
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    data = json.loads(raw)

    # Extract metadata
    page_type = data.get("page_type", "ledger")
    page_title = data.get("page_title", "")
    rows = data.get("rows", [])

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Ensure 'side' is "NA" for standard files
    df["side"] = "NA"

    # Apply metadata
    df = apply_schema_defaults(df, file_id, page_number)
    df["page_type"] = page_type
    df["page_title"] = page_title

    # Post-processing
    df = post_process_extraction(df)

    return df


def extract_page_rows_complex(
    file_id: str,
    pdf_path: str,
    page_number: int,
    model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    """
    Extract ledger rows from a complex dual-column page using split extraction.
    """
    # Convert page to base64
    img = pdf_page_to_image(pdf_path, page_number)
    img_b64 = pil_image_to_base64(img)

    # Extract LEFT side
    response_left = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_LEFT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT_LEFT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            },
        ],
        max_tokens=8192,
        temperature=0.1,
    )

    content_left = response_left.choices[0].message.content.strip()

    # Parse LEFT JSON
    raw_left = content_left
    if raw_left.startswith("```"):
        raw_left = raw_left.strip("`")
        if raw_left.lower().startswith("json"):
            raw_left = raw_left[4:].strip()
    if raw_left.endswith("```"):
        raw_left = raw_left[:-3].strip()

    data_left = json.loads(raw_left)
    rows_left = data_left.get("rows", [])
    page_title = data_left.get("page_title", "")

    # Extract RIGHT side
    response_right = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_RIGHT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT_RIGHT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            },
        ],
        max_tokens=8192,
        temperature=0.1,
    )

    content_right = response_right.choices[0].message.content.strip()

    # Parse RIGHT JSON
    raw_right = content_right
    if raw_right.startswith("```"):
        raw_right = raw_right.strip("`")
        if raw_right.lower().startswith("json"):
            raw_right = raw_right[4:].strip()
    if raw_right.endswith("```"):
        raw_right = raw_right[:-3].strip()

    data_right = json.loads(raw_right)
    rows_right = data_right.get("rows", [])

    # Combine rows (LEFT first, then RIGHT)
    all_rows = rows_left + rows_right

    # Re-index rows sequentially
    for i, row in enumerate(all_rows):
        row["row_index"] = i + 1

    if not all_rows:
        return pd.DataFrame(columns=COLUMNS)

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)

    # Apply metadata
    df = apply_schema_defaults(df, file_id, page_number)
    df["page_type"] = "balance_sheet"
    df["page_title"] = page_title

    # Post-processing
    df = post_process_extraction(df)

    return df


def post_process_extraction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply common post-processing to extracted data.
    """
    # Normalize empty values in numeric columns
    numeric_cols = ["amount_pounds", "amount_shillings", "amount_pence_whole", "amount_pence_fraction"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_empty_values)

    # Clean pence fractions
    if "amount_pence_whole" in df.columns and "amount_pence_fraction" in df.columns:
        df[["amount_pence_whole", "amount_pence_fraction"]] = df.apply(
            lambda r: pd.Series(clean_pence_fraction(r["amount_pence_whole"], r["amount_pence_fraction"])),
            axis=1,
        )

    # Infer row types for rows without amounts (backup check)
    df["row_type"] = df.apply(infer_row_type, axis=1)

    # Update is_total_row flag
    df["is_total_row"] = df["row_type"] == "total"

    # Calculate confidence scores
    df["confidence_score"] = df.apply(calculate_confidence_score, axis=1)

    # Ensure all columns exist and are in correct order
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS]

    return df


def extract_page_rows(
    file_id: str,
    pdf_path: str,
    page_number: int,
    model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    """
    Extract ledger rows from a single PDF page.
    Automatically selects the appropriate extraction method based on file_id.
    """
    if file_id in COMPLEX_FILES:
        return extract_page_rows_complex(file_id, pdf_path, page_number, model_name)
    else:
        return extract_page_rows_standard(file_id, pdf_path, page_number, model_name)


def extract_full_pdf(
    file_id: str,
    pdf_path: str,
    model_name: str = MODEL_NAME,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Extract all pages from a PDF.
    """
    from src.pdf_utils import get_pdf_page_count

    num_pages = get_pdf_page_count(pdf_path)
    all_dfs = []
    errors = []

    # Log which extraction method is being used
    extraction_type = "COMPLEX (split)" if file_id in COMPLEX_FILES else "STANDARD"
    print(f"  Using {extraction_type} extraction for {file_id} ({num_pages} pages)")

    for page_no in range(1, num_pages + 1):
        try:
            df_page = extract_page_rows(file_id, pdf_path, page_no, model_name)
            all_dfs.append(df_page)
            print(f"    ✓ Page {page_no}: {len(df_page)} rows")
        except Exception as e:
            error_info = {
                "file_id": file_id,
                "page_number": page_no,
                "error": str(e),
            }
            errors.append(error_info)
            print(f"    ⚠️ Page {page_no}: Error - {e}")

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=COLUMNS)

    return combined, errors
