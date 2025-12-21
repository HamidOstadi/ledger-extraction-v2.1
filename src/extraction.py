"""
AI extraction utilities for the Ledger OCR Project V2
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

Examples of section headers (no amounts):
- "Merton" (place name, no amounts)
- "Item de arreragÿs" (label, no amounts)
- "Thrup" (place name, no amounts)

BRACE GROUPINGS:
Some ledgers use a curly brace "{" to group multiple sub-entries under one parent entry.
For example:
  Tintinhull { Napper  — 02  5  5
             { Hopkins — 01 18  7

When you see this pattern:
- Extract EACH line as a separate row
- Set group_brace_id to the same number for all rows in the group (e.g., "1" for first group, "2" for second)
- The parent entry (e.g., "Tintinhull") may or may not have its own amounts

CURRENCY RULES:
- Pounds, shillings, pence must exactly match what is written (do not calculate or infer)
- Pence fractions: 1/4, 1/2, 3/4 or unicode ¼, ½, ¾
  * "q" or "qd" after a number = 1/4 (quarter pence), e.g., "8q" means 8 and 1/4
  * "ob" = 1/2 (half pence)
  * Ignore trailing "d" (denarius), e.g., "3/4 d" → fraction is "3/4"
- Put whole pence in amount_pence_whole, fraction in amount_pence_fraction
- If a column is blank, use empty string "" — do NOT invent values

PAGE TYPES:
- "ledger" = Standard single-column format with entries and amounts
- "balance_sheet" = Multi-column format with Credit/Debit or Assets/Liabilities sections

For balance sheets, identify transaction_type as:
- "credit" or "debit"
- "income" or "expenditure"

TEXT TRANSCRIPTION:
- Preserve original spelling and spacing (e.g., "Long witnam" not "Longwitnam")
- Do not include margin notes or annotations
- For unclear writing, make your best faithful guess

OUTPUT FORMAT:
Return a JSON object with:
{
  "page_type": "ledger" or "balance_sheet",
  "page_title": "the title text at top of page",
  "rows": [
    {
      "row_index": 1,
      "row_type": "title",
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

IMPORTANT REMINDERS:
1. ALWAYS include the page title as the first row with row_type="title"
2. ALWAYS include rows without amounts as row_type="section_header"
3. Count carefully — each visible line should be one row
4. Return ONLY valid JSON, no commentary
"""

USER_PROMPT = "Please read this ledger page and extract ALL rows as described. Remember to include the title row and any section headers (rows without amounts)."


def extract_page_rows(
    file_id: str,
    pdf_path: str,
    page_number: int,
    model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    """
    Extract ledger rows from a single PDF page using the multimodal model.
    
    Args:
        file_id: Identifier for the PDF (e.g., "1704")
        pdf_path: Path to the PDF file
        page_number: 1-based page number
        model_name: OpenAI model to use
    
    Returns:
        DataFrame with extracted rows matching the master schema
    """
    # Convert page to base64
    img = pdf_page_to_image(pdf_path, page_number)
    img_b64 = pil_image_to_base64(img)
    
    # Call the API
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            },
        ],
    )
    
    content = response.choices[0].message.content.strip()
    
    # Parse JSON response
    raw = content
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    
    data = json.loads(raw)
    
    # Extract metadata
    page_type = data.get("page_type", "ledger")
    page_title = data.get("page_title", "")
    rows = data.get("rows", [])
    
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    
    # Convert to DataFrame
    df = pd.DataFrame(rows)
    
    # Apply metadata
    df = apply_schema_defaults(df, file_id, page_number)
    df["page_type"] = page_type
    df["page_title"] = page_title
    
    # Normalize empty values in numeric columns
    numeric_cols = ["amount_pounds", "amount_shillings", "amount_pence_whole", "amount_pence_fraction"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_empty_values)
    
    # Clean pence fractions
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


def extract_full_pdf(
    file_id: str,
    pdf_path: str,
    model_name: str = MODEL_NAME,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Extract all pages from a PDF.
    
    Args:
        file_id: Identifier for the PDF
        pdf_path: Path to the PDF file
        model_name: OpenAI model to use
    
    Returns:
        Tuple of (combined DataFrame, list of errors)
    """
    from src.pdf_utils import get_pdf_page_count
    
    num_pages = get_pdf_page_count(pdf_path)
    all_dfs = []
    errors = []
    
    for page_no in range(1, num_pages + 1):
        try:
            df_page = extract_page_rows(file_id, pdf_path, page_no, model_name)
            all_dfs.append(df_page)
        except Exception as e:
            error_info = {
                "file_id": file_id,
                "page_number": page_no,
                "error": str(e),
            }
            errors.append(error_info)
            print(f"  ⚠️ Error on page {page_no}: {e}")
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=COLUMNS)
    
    return combined, errors