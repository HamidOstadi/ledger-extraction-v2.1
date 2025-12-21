"""
Schema definitions and data cleaning utilities for the Ledger OCR Project V2
"""

import re
import pandas as pd

from src.config import (
    COLUMNS,
    VALID_ROW_TYPES,
    VALID_PENCE_FRACTIONS,
    VALID_TRANSACTION_TYPES,
)


# Unicode fraction mapping
UNICODE_FRACTION_MAP = {
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
}

# Historical notation mapping
# "q" = quarter = 1/4 pence
# "qd" = quarter pence
# "d" suffix = denarius (pence) - can be ignored
HISTORICAL_FRACTION_MAP = {
    "q": "1/4",
    "qd": "1/4",
    "qr": "1/4",
    "ob": "1/2",      # obolus = half penny
    "obd": "1/2",
}


def clean_pence_fraction(pence_whole, pence_fraction: str) -> tuple:
    """
    Clean and validate pence fraction values.
    
    Handles:
    - Unicode fractions: ¼, ½, ¾
    - Standard fractions: 1/4, 1/2, 3/4
    - Fractions with 'd' suffix: "1/4 d", "3/4d", "1/2 d"
    - Historical notation: "q", "qd" (quarter), "ob" (half)
    
    Args:
        pence_whole: The whole pence value
        pence_fraction: The fraction string to clean
    
    Returns:
        Tuple of (cleaned_whole, cleaned_fraction)
    """
    frac = str(pence_fraction).strip().lower()
    whole = pence_whole
    
    # Handle empty/none values
    if frac in ("", "none", "nan"):
        return whole, ""
    
    # Step 1: Remove trailing 'd' or ' d' (denarius suffix)
    frac = re.sub(r'\s*d$', '', frac).strip()
    
    # Step 2: Map unicode fractions
    # Need to check original (before lowercase) for unicode
    original_frac = str(pence_fraction).strip()
    for unicode_char, standard in UNICODE_FRACTION_MAP.items():
        if unicode_char in original_frac:
            return whole, standard
    
    # Step 3: Map historical notation (q, qd, ob, etc.)
    if frac in HISTORICAL_FRACTION_MAP:
        return whole, HISTORICAL_FRACTION_MAP[frac]
    
    # Step 4: Check if it's already a valid standard fraction
    if frac in VALID_PENCE_FRACTIONS:
        return whole, frac
    
    # Step 5: Handle fractions that might have extra whitespace
    # e.g., "1 / 4" -> "1/4"
    frac_normalized = re.sub(r'\s*/\s*', '/', frac)
    if frac_normalized in VALID_PENCE_FRACTIONS:
        return whole, frac_normalized
    
    # Step 6: If fraction is a pure digit and whole is empty/zero,
    # treat it as whole pence and clear fraction
    if frac.isdigit() and str(whole).strip() in ("", "0"):
        return int(frac), ""
    
    # Otherwise: treat as unknown, drop fraction
    return whole, ""


def normalize_empty_values(value) -> str:
    """
    Convert None, NaN, or other empty-like values to empty string.
    """
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return value


def has_any_amount(row: pd.Series) -> bool:
    """
    Check if a row has any currency amount values.
    """
    amount_cols = ["amount_pounds", "amount_shillings", "amount_pence_whole"]
    for col in amount_cols:
        if col in row:
            val = str(row[col]).strip()
            if val not in ("", "None", "nan"):
                return True
    return False


def infer_row_type(row: pd.Series) -> str:
    """
    Infer the row type based on content.
    Rows without amounts (except title rows) are likely section headers.
    """
    current_type = row.get("row_type", "entry")
    
    # Don't change title rows
    if current_type == "title":
        return "title"
    
    # Don't change total rows
    if current_type == "total":
        return "total"
    
    # If no amounts, likely a section header
    if not has_any_amount(row):
        return "section_header"
    
    return current_type


def calculate_confidence_score(row: pd.Series) -> float:
    """
    Calculate a confidence score (0.0 to 1.0) for a row based on data quality signals.
    
    Scoring factors:
    - Has description: +0.2
    - Has at least one amount field: +0.2
    - Pence fraction is valid: +0.2
    - Row type is consistent with content: +0.2
    - All amount fields are numeric: +0.2
    
    Returns:
        Float between 0.0 and 1.0
    """
    score = 0.0
    
    # Factor 1: Has description
    desc = str(row.get("description", "")).strip()
    if desc and desc.lower() not in ("", "none", "nan"):
        score += 0.2
    
    # Factor 2: Has at least one amount
    if has_any_amount(row):
        score += 0.2
    
    # Factor 3: Valid pence fraction
    pence_frac = str(row.get("amount_pence_fraction", "")).strip()
    if pence_frac in VALID_PENCE_FRACTIONS:
        score += 0.2
    
    # Factor 4: Row type consistency
    row_type = row.get("row_type", "")
    has_amounts = has_any_amount(row)
    
    if row_type == "entry" and has_amounts:
        score += 0.2
    elif row_type == "section_header" and not has_amounts:
        score += 0.2
    elif row_type == "total" and has_amounts:
        score += 0.2
    elif row_type == "title":
        score += 0.2
    
    # Factor 5: Amount fields are properly formatted
    amount_fields_valid = True
    for col in ["amount_pounds", "amount_shillings", "amount_pence_whole"]:
        val = row.get(col, "")
        val_str = str(val).strip()
        if val_str and val_str not in ("", "None", "nan"):
            # Should be numeric or empty
            try:
                float(val_str)
            except ValueError:
                amount_fields_valid = False
                break
    
    if amount_fields_valid:
        score += 0.2
    
    return round(score, 2)


def create_empty_dataframe() -> pd.DataFrame:
    """
    Create an empty DataFrame with the master schema.
    """
    return pd.DataFrame(columns=COLUMNS)


def apply_schema_defaults(df: pd.DataFrame, file_id: str, page_number: int) -> pd.DataFrame:
    """
    Apply default values and metadata to a DataFrame.
    """
    df = df.copy()
    
    # Metadata
    df["file_id"] = file_id
    df["page_number"] = page_number
    
    # Defaults for missing columns
    defaults = {
        "page_type": "ledger",
        "page_title": "",
        "date_raw": "",
        "is_total_row": False,
        "group_brace_id": "",
        "transaction_type": "",
        "num_col_1": "",
        "num_col_2": "",
        "num_col_3": "",
        "num_col_4": "",
        "num_col_5": "",
        "num_col_6": "",
        "entry_confidence": "model",
        "notes": "",
    }
    
    for col, default_val in defaults.items():
        if col not in df.columns:
            df[col] = default_val
    
    return df