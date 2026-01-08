"""
Extraction module for the Ledger OCR Project V2.3
Enhanced with vertical line column detection for accurate amount parsing
"""

import json
import base64
import pandas as pd
from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    MODEL_NAME,
    COLUMNS,
)
from src.pdf_utils import pdf_page_to_image, pil_image_to_base64
from src.schema import (
    clean_pence_fraction,
    calculate_confidence_score,
    infer_row_type,
    apply_schema_defaults,
    normalize_empty_values,
)


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """
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

================================================================================
CRITICAL: IDENTIFYING CURRENCY COLUMNS USING VERTICAL LINES
================================================================================

STEP 1: LOCATE THE VERTICAL DIVIDER LINES
Most ledger pages have THREE VERTICAL LINES running from top to bottom on the RIGHT side of the page. These lines physically divide the currency columns:

    |  Description text here  |  £  |  s  |  d  |
                              ↑    ↑    ↑    ↑
                          Line 1  Line 2  Line 3  (page edge)

- The space between Line 1 and Line 2 = POUNDS (£)
- The space between Line 2 and Line 3 = SHILLINGS (s)
- The space between Line 3 and the page edge = PENCE (d)

STEP 2: USE THE VERTICAL LINES AS GUIDES
Before extracting any numbers:
1. FIRST, scan the right portion of the page to identify these vertical ruling lines
2. Note where each line runs vertically down the page
3. These lines define the column boundaries for ALL rows

STEP 3: EXTRACT NUMBERS BASED ON COLUMN POSITION
For each row, read the numbers that fall WITHIN each column space:
- Numbers between Line 1 and Line 2 → amount_pounds
- Numbers between Line 2 and Line 3 → amount_shillings  
- Numbers between Line 3 and page edge → amount_pence_whole

IMPORTANT: The vertical lines are your PRIMARY guide. Trust the physical column boundaries over visual spacing between numbers.

================================================================================
CURRENCY VALIDATION RULES
================================================================================

After extracting amounts, VERIFY they make sense:
- SHILLINGS must be 0-19 (because 20 shillings = 1 pound)
- PENCE must be 0-11 (because 12 pence = 1 shilling)
- POUNDS can be any positive number

IF VALIDATION FAILS:
If you extract shillings >= 20 or pence >= 12, you have likely:
1. Misidentified the column boundaries, OR
2. Merged numbers from adjacent columns

GO BACK and re-examine the vertical lines to correctly separate the values.

COMMON ERRORS TO AVOID:
❌ WRONG: Reading "15  6" as pounds=156 (merged two columns)
✓ RIGHT:  Reading "15  6" as shillings=15, pence=6

❌ WRONG: Putting 25 in shillings (impossible — max is 19)  
✓ RIGHT:  Re-check the vertical lines; 25 is likely "2" and "5" in separate columns

================================================================================
HANDLING VARIATIONS IN COLUMN STRUCTURE
================================================================================

VARIATION 1: Clear vertical lines present
→ Use the lines directly as column boundaries

VARIATION 2: Faint or partial vertical lines
→ Look at the TOP (header row) or BOTTOM (total row) where lines are often clearer
→ Project those column positions to all rows

VARIATION 3: No visible vertical lines
→ Use the TOTAL row at the bottom as your guide — totals are usually well-aligned
→ Identify the three column positions from the total, then apply to all rows above

VARIATION 4: Dense or crowded numbers
→ The vertical lines are especially important here
→ Trust the physical column position over apparent spacing

================================================================================

BRACE GROUPINGS:
Some ledgers use a curly brace "{" to group multiple sub-entries under one parent entry.
For example:
  Tintinhull { Napper  — 02  5  5
             { Hopkins — 01 18  7

When you see this pattern:
- Extract EACH line as a separate row
- Set group_brace_id to the same number for all rows in the group
- The parent entry may or may not have its own amounts

CURRENCY NOTATION:
- Pence fractions: 1/4, 1/2, 3/4 or unicode ¼, ½, ¾
  * "q" or "qd" after a number = 1/4 (quarter pence)
  * "ob" = 1/2 (half pence)
  * Ignore trailing "d" (denarius)
- Put whole pence in amount_pence_whole, fraction in amount_pence_fraction
- If a column is empty, use "" — do NOT invent values

PAGE TYPES:
- "ledger" = Standard format with entries and amounts
- "balance_sheet" = Multi-column format with Credit/Debit sections

For balance sheets, identify transaction_type as:
- "credit" or "debit"
- "income" or "expenditure"

TEXT TRANSCRIPTION:
- Preserve original spelling and spacing
- Do not include margin notes
- For unclear writing, make your best faithful guess

OUTPUT FORMAT:
Return a JSON object with:
{
  "page_type": "ledger" or "balance_sheet",
  "page_title": "the title text at top of page",
  "rows": [
    {
      "row_index": 1,
      "row_type": "title|entry|section_header|total",
      "date_raw": "",
      "description": "...",
      "amount_pounds": "",
      "amount_shillings": "",
      "amount_pence_whole": "",
      "amount_pence_fraction": "",
      "is_total_row": false,
      "group_brace_id": "",
      "transaction_type": ""
    },
    ...
  ]
}

FINAL CHECKLIST:
□ Did I identify the vertical column divider lines?
□ Did I use those lines to determine column boundaries?
□ Are ALL shillings values between 0-19?
□ Are ALL pence values between 0-11?
□ Did I include the page title as the first row?
□ Did I include section headers (rows with no amounts)?
"""


USER_PROMPT = """
Extract all data from this ledger page image.

IMPORTANT — FOLLOW THESE STEPS:
1. FIRST, look at the RIGHT side of the page and identify the VERTICAL LINES that divide the currency columns (Pounds | Shillings | Pence)
2. Use these vertical lines as column boundaries for ALL rows
3. Extract numbers based on which column space they fall into
4. VERIFY: Shillings must be 0-19, Pence must be 0-11

Include the page title, all entries, section headers (no amounts), and totals.

Return valid JSON only.
"""


def extract_page_rows(
    file_id: str,
    pdf_path: str,
    page_number: int,
) -> pd.DataFrame:
    """
    Extract rows from a single page of a PDF.

    Args:
        file_id: Identifier for the PDF file
        pdf_path: Path to the PDF file
        page_number: Page number to extract (1-based)

    Returns:
        DataFrame with extracted rows
    """
    # Convert PDF page to image
    img = pdf_page_to_image(pdf_path, page_number)
    img_base64 = pil_image_to_base64(img)

    # Call OpenAI API
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    # Parse response
    content = response.choices[0].message.content

    # Clean up JSON (remove markdown code blocks if present)
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    # Parse JSON
    data = json.loads(content)

    # Convert to DataFrame
    rows = data.get("rows", [])
    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(rows)

    # Apply schema defaults
    df = apply_schema_defaults(df, file_id, page_number)

    # Set page_type and page_title from response
    df["page_type"] = data.get("page_type", "ledger")
    df["page_title"] = data.get("page_title", "")

    # Clean pence fractions
    for idx, row in df.iterrows():
        pence_whole = row.get("amount_pence_whole", "")
        pence_frac = row.get("amount_pence_fraction", "")
        cleaned_whole, cleaned_frac = clean_pence_fraction(pence_whole, pence_frac)
        df.at[idx, "amount_pence_whole"] = cleaned_whole
        df.at[idx, "amount_pence_fraction"] = cleaned_frac

    # Normalize empty values
    for col in ["amount_pounds", "amount_shillings", "amount_pence_whole", "amount_pence_fraction"]:
        if col in df.columns:
            df[col] = df[col].apply(normalize_empty_values)

    # Infer row types where needed
    for idx, row in df.iterrows():
        if row.get("row_type") not in ["title", "total", "section_header", "entry"]:
            df.at[idx, "row_type"] = infer_row_type(row)

    # Calculate confidence scores
    df["confidence_score"] = df.apply(calculate_confidence_score, axis=1)

    # Ensure all columns are present
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Reorder columns
    df = df[COLUMNS]

    return df


def extract_full_pdf(
    file_id: str,
    pdf_path: str,
    num_pages: int,
) -> tuple[pd.DataFrame, list]:
    """
    Extract all pages from a PDF.

    Args:
        file_id: Identifier for the PDF file
        pdf_path: Path to the PDF file
        num_pages: Number of pages to extract

    Returns:
        Tuple of (combined DataFrame, list of errors)
    """
    all_dfs = []
    errors = []

    for page_no in range(1, num_pages + 1):
        try:
            df_page = extract_page_rows(file_id, pdf_path, page_no)
            all_dfs.append(df_page)
        except Exception as e:
            errors.append({
                "file_id": file_id,
                "page_number": page_no,
                "error": str(e),
            })

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=COLUMNS)

    return combined, errors
