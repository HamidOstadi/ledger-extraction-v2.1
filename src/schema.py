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
HISTORICAL_FRACTION_MAP = {
    "q": "1/4",
    "qd": "1/4",
    "qr": "1/4",
    "ob": "1/2",
    "obd": "1/2",
}

# Currency validation constants (19th-century British currency system)
MAX_SHILLINGS = 19  # 20 shillings = 1 pound
MAX_PENCE = 11      # 12 pence = 1 shilling


def clean_pence_fraction(pence_whole, pence_fraction: str) -> tuple:
    """
    Clean and validate pence fraction values.
    """
    frac = str(pence_fraction).strip().lower()
    whole = pence_whole
    
    if frac in ("", "none", "nan"):
        return whole, ""
    
    # Remove trailing 'd' or ' d' (denarius suffix)
    frac = re.sub(r'\s*d$', '', frac).strip()
    
    # Map unicode fractions
    original_frac = str(pence_fraction).strip()
    for unicode_char, standard in UNICODE_FRACTION_MAP.items():
        if unicode_char in original_frac:
            return whole, standard
    
    # Map historical notation
    if frac in HISTORICAL_FRACTION_MAP:
        return whole, HISTORICAL_FRACTION_MAP[frac]
    
    # Check if valid standard fraction
    if frac in VALID_PENCE_FRACTIONS:
        return whole, frac
    
    # Handle fractions with extra whitespace
    frac_normalized = re.sub(r'\s*/\s*', '/', frac)
    if frac_normalized in VALID_PENCE_FRACTIONS:
        return whole, frac_normalized
    
    # If fraction is a pure digit and whole is empty/zero
    if frac.isdigit() and str(whole).strip() in ("", "0"):
        return int(frac), ""
    
    return whole, ""


def normalize_empty_values(value) -> str:
    """Convert None, NaN, or other empty-like values to empty string."""
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return value


def safe_to_int(value) -> int | None:
    """Safely convert a value to integer, returning None if not possible."""
    if value is None or pd.isna(value):
        return None
    s = str(value).strip()
    if s in ("", "nan", "None", "NaN"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def validate_currency_range(row: pd.Series) -> dict:
    """
    Validate that currency values are within historical valid ranges.
    
    British currency system (pre-decimalization):
    - 20 shillings = 1 pound
    - 12 pence = 1 shilling
    
    Returns:
        Dictionary with validation results
    """
    issues = []
    
    # Check shillings (must be 0-19)
    shillings = safe_to_int(row.get("amount_shillings"))
    if shillings is not None and (shillings < 0 or shillings > MAX_SHILLINGS):
        issues.append({
            "field": "amount_shillings",
            "value": shillings,
            "issue": f"Shillings must be 0-{MAX_SHILLINGS}, got {shillings}",
            "severity": "error",
        })
    
    # Check pence (must be 0-11)
    pence = safe_to_int(row.get("amount_pence_whole"))
    if pence is not None and (pence < 0 or pence > MAX_PENCE):
        issues.append({
            "field": "amount_pence_whole",
            "value": pence,
            "issue": f"Pence must be 0-{MAX_PENCE}, got {pence}",
            "severity": "error",
        })
    
    # Check for negative pounds (unlikely but invalid)
    pounds = safe_to_int(row.get("amount_pounds"))
    if pounds is not None and pounds < 0:
        issues.append({
            "field": "amount_pounds",
            "value": pounds,
            "issue": f"Pounds cannot be negative, got {pounds}",
            "severity": "error",
        })
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }


def has_any_amount(row: pd.Series) -> bool:
    """Check if a row has any currency amount values."""
    amount_cols = ["amount_pounds", "amount_shillings", "amount_pence_whole"]
    for col in amount_cols:
        if col in row:
            val = str(row[col]).strip()
            if val not in ("", "None", "nan"):
                return True
    return False


def infer_row_type(row: pd.Series) -> str:
    """Infer the row type based on content."""
    current_type = row.get("row_type", "entry")
    
    if current_type == "title":
        return "title"
    
    if current_type == "total":
        return "total"
    
    if not has_any_amount(row):
        return "section_header"
    
    return current_type


def calculate_confidence_score(row: pd.Series) -> float:
    """
    Calculate a confidence score (0.0 to 1.0) for a row based on data quality signals.
    
    Updated scoring factors:
    - Has description: +0.15
    - Has at least one amount field: +0.15
    - Pence fraction is valid: +0.15
    - Row type is consistent with content: +0.15
    - All amount fields are numeric: +0.15
    - Currency values are in valid range: +0.25 (NEW - higher weight)
    
    Returns:
        Float between 0.0 and 1.0
    """
    score = 0.0
    
    # Factor 1: Has description (+0.15)
    desc = str(row.get("description", "")).strip()
    if desc and desc.lower() not in ("", "none", "nan"):
        score += 0.15
    
    # Factor 2: Has at least one amount (+0.15)
    if has_any_amount(row):
        score += 0.15
    
    # Factor 3: Valid pence fraction (+0.15)
    pence_frac = str(row.get("amount_pence_fraction", "")).strip()
    if pence_frac in VALID_PENCE_FRACTIONS:
        score += 0.15
    
    # Factor 4: Row type consistency (+0.15)
    row_type = row.get("row_type", "")
    has_amounts = has_any_amount(row)
    
    if row_type == "entry" and has_amounts:
        score += 0.15
    elif row_type == "section_header" and not has_amounts:
        score += 0.15
    elif row_type == "total" and has_amounts:
        score += 0.15
    elif row_type == "title":
        score += 0.15
    
    # Factor 5: Amount fields are properly formatted (+0.15)
    amount_fields_valid = True
    for col in ["amount_pounds", "amount_shillings", "amount_pence_whole"]:
        val = row.get(col, "")
        val_str = str(val).strip()
        if val_str and val_str not in ("", "None", "nan"):
            try:
                float(val_str)
            except ValueError:
                amount_fields_valid = False
                break
    
    if amount_fields_valid:
        score += 0.15
    
    # Factor 6: Currency values in valid range (+0.25) - NEW
    validation = validate_currency_range(row)
    if validation["is_valid"]:
        score += 0.25
    else:
        # Partial credit if only minor issues
        error_count = len(validation["issues"])
        if error_count == 1:
            score += 0.10  # One issue: partial credit
        # Multiple issues: no credit
    
    return round(min(score, 1.0), 2)


def create_empty_dataframe() -> pd.DataFrame:
    """Create an empty DataFrame with the master schema."""
    return pd.DataFrame(columns=COLUMNS)


def apply_schema_defaults(df: pd.DataFrame, file_id: str, page_number: int) -> pd.DataFrame:
    """Apply default values and metadata to a DataFrame."""
    df = df.copy()
    
    df["file_id"] = file_id
    df["page_number"] = page_number
    
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


def classify_page_complexity(df_page: pd.DataFrame) -> dict:
    """
    Classify a page as 'simple' or 'complex' based on layout characteristics.

    Complexity factors:
    - Row count (more rows = more complex)
    - Multiple section headers (indicates structured sections)
    - Mix of row types (title, entry, section_header, total)
    - Presence of brace groupings

    Returns:
        Dictionary with complexity classification and factors
    """
    factors = {}
    complexity_score = 0

    # Factor 1: Row count
    row_count = len(df_page)
    factors["row_count"] = row_count
    if row_count > 30:
        complexity_score += 2
    elif row_count > 15:
        complexity_score += 1

    # Factor 2: Number of section headers
    if "row_type" in df_page.columns:
        section_headers = (df_page["row_type"] == "section_header").sum()
        factors["section_headers"] = section_headers
        if section_headers > 3:
            complexity_score += 2
        elif section_headers > 1:
            complexity_score += 1

    # Factor 3: Multiple totals (indicates sub-sections)
    if "row_type" in df_page.columns:
        totals = (df_page["row_type"] == "total").sum()
        factors["total_rows"] = totals
        if totals > 1:
            complexity_score += 1

    # Factor 4: Brace groupings
    if "group_brace_id" in df_page.columns:
        brace_groups = df_page["group_brace_id"].nunique()
        # Subtract 1 if empty string is counted
        if "" in df_page["group_brace_id"].values:
            brace_groups -= 1
        factors["brace_groups"] = max(0, brace_groups)
        if brace_groups > 0:
            complexity_score += 1

    # Factor 5: Page type
    if "page_type" in df_page.columns:
        page_type = df_page["page_type"].iloc[0] if len(df_page) > 0 else "ledger"
        factors["page_type"] = page_type
        if page_type == "balance_sheet":
            complexity_score += 2

    # Classify based on score
    factors["complexity_score"] = complexity_score
    if complexity_score >= 4:
        classification = "complex"
    elif complexity_score >= 2:
        classification = "moderate"
    else:
        classification = "simple"

    return {
        "classification": classification,
        "complexity_score": complexity_score,
        "factors": factors,
    }

