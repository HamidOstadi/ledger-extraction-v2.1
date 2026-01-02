"""
Validation utilities for the Ledger OCR Project V2
"""

import pandas as pd
from src.config import COLUMNS
from src.schema import safe_to_int, validate_currency_range, MAX_SHILLINGS, MAX_PENCE


def compare_with_ground_truth(
    df_extracted: pd.DataFrame,
    df_ground_truth: pd.DataFrame,
    key_columns: list[str] = ["file_id", "page_number", "row_index"],
) -> pd.DataFrame:
    """Compare extracted data with ground truth."""
    comparison = df_ground_truth.merge(
        df_extracted,
        on=key_columns,
        suffixes=("_truth", "_extracted"),
        how="outer",
        indicator=True,
    )
    return comparison


def calculate_field_accuracy(comparison_df: pd.DataFrame, field_name: str) -> dict:
    """Calculate accuracy metrics for a specific field."""
    truth_col = f"{field_name}_truth"
    extracted_col = f"{field_name}_extracted"
    
    if truth_col not in comparison_df.columns or extracted_col not in comparison_df.columns:
        return {"error": f"Field {field_name} not found"}
    
    both_present = comparison_df[comparison_df["_merge"] == "both"].copy()
    
    if len(both_present) == 0:
        return {"match_count": 0, "total_count": 0, "accuracy_pct": 0.0}
    
    both_present[truth_col] = both_present[truth_col].astype(str).str.strip().str.lower()
    both_present[extracted_col] = both_present[extracted_col].astype(str).str.strip().str.lower()
    
    matches = (both_present[truth_col] == both_present[extracted_col]).sum()
    total = len(both_present)
    accuracy = round(matches / total * 100, 2) if total > 0 else 0.0
    
    return {
        "match_count": int(matches),
        "total_count": int(total),
        "accuracy_pct": accuracy,
    }


def generate_accuracy_report(comparison_df: pd.DataFrame, fields_to_check: list[str] = None) -> pd.DataFrame:
    """Generate an accuracy report for multiple fields."""
    if fields_to_check is None:
        fields_to_check = [
            "row_type", "description", "amount_pounds",
            "amount_shillings", "amount_pence_whole", "amount_pence_fraction",
        ]
    
    results = []
    for field in fields_to_check:
        metrics = calculate_field_accuracy(comparison_df, field)
        metrics["field"] = field
        results.append(metrics)
    
    return pd.DataFrame(results)[["field", "match_count", "total_count", "accuracy_pct"]]


def convert_to_pence(pounds, shillings, pence) -> int | None:
    """
    Convert £/s/d to total pence for arithmetic comparison.
    
    1 pound = 20 shillings = 240 pence
    1 shilling = 12 pence
    """
    p = safe_to_int(pounds) or 0
    s = safe_to_int(shillings) or 0
    d = safe_to_int(pence) or 0
    
    return (p * 240) + (s * 12) + d


def validate_page_arithmetic(df_page: pd.DataFrame) -> dict:
    """
    Validate that entry rows sum to the total row on a page.
    
    Returns:
        Dictionary with validation results
    """
    # Separate entries and totals
    entries = df_page[df_page["row_type"] == "entry"].copy()
    totals = df_page[df_page["row_type"] == "total"].copy()
    
    if len(totals) == 0:
        return {
            "status": "no_totals",
            "message": "No total rows found on page",
            "can_validate": False,
        }
    
    if len(entries) == 0:
        return {
            "status": "no_entries",
            "message": "No entry rows found on page",
            "can_validate": False,
        }
    
    # Calculate sum of all entries
    entry_total_pence = 0
    for _, row in entries.iterrows():
        entry_total_pence += convert_to_pence(
            row.get("amount_pounds"),
            row.get("amount_shillings"),
            row.get("amount_pence_whole"),
        )
    
    # Get the stated total (use last total row)
    last_total = totals.iloc[-1]
    stated_total_pence = convert_to_pence(
        last_total.get("amount_pounds"),
        last_total.get("amount_shillings"),
        last_total.get("amount_pence_whole"),
    )
    
    # Calculate difference
    difference = entry_total_pence - stated_total_pence
    matches = difference == 0
    
    # Convert back to £/s/d for reporting
    def pence_to_lsd(total_pence):
        pounds = total_pence // 240
        remaining = total_pence % 240
        shillings = remaining // 12
        pence = remaining % 12
        return pounds, shillings, pence
    
    calc_p, calc_s, calc_d = pence_to_lsd(entry_total_pence)
    stated_p, stated_s, stated_d = pence_to_lsd(stated_total_pence)
    
    return {
        "status": "match" if matches else "mismatch",
        "can_validate": True,
        "calculated": {
            "pounds": calc_p,
            "shillings": calc_s,
            "pence": calc_d,
            "total_pence": entry_total_pence,
        },
        "stated": {
            "pounds": stated_p,
            "shillings": stated_s,
            "pence": stated_d,
            "total_pence": stated_total_pence,
        },
        "difference_pence": abs(difference),
        "matches": matches,
    }


def validate_currency_ranges_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate currency ranges for all rows in a DataFrame.
    
    Returns:
        DataFrame with validation issues
    """
    issues = []
    
    for idx, row in df.iterrows():
        validation = validate_currency_range(row)
        if not validation["is_valid"]:
            for issue in validation["issues"]:
                issues.append({
                    "row_index": idx,
                    "file_id": row.get("file_id", ""),
                    "page_number": row.get("page_number", ""),
                    "description": row.get("description", "")[:50],
                    "field": issue["field"],
                    "value": issue["value"],
                    "issue": issue["issue"],
                    "severity": issue["severity"],
                })
    
    return pd.DataFrame(issues)


def generate_validation_report(df: pd.DataFrame) -> dict:
    """
    Generate a comprehensive validation report for the entire dataset.
    
    Returns:
        Dictionary with validation summary and details
    """
    report = {
        "total_rows": len(df),
        "currency_range_validation": {},
        "arithmetic_validation": {},
        "summary": {},
    }
    
    # 1. Currency range validation
    range_issues = validate_currency_ranges_batch(df)
    report["currency_range_validation"] = {
        "total_issues": len(range_issues),
        "rows_with_issues": range_issues["row_index"].nunique() if len(range_issues) > 0 else 0,
        "issues_by_field": range_issues["field"].value_counts().to_dict() if len(range_issues) > 0 else {},
        "details": range_issues,
    }
    
    # 2. Arithmetic validation (per page)
    arithmetic_results = []
    for (file_id, page_num), page_df in df.groupby(["file_id", "page_number"]):
        result = validate_page_arithmetic(page_df)
        result["file_id"] = file_id
        result["page_number"] = page_num
        arithmetic_results.append(result)
    
    arithmetic_df = pd.DataFrame(arithmetic_results)
    validatable = arithmetic_df[arithmetic_df["can_validate"] == True]
    
    report["arithmetic_validation"] = {
        "total_pages": len(arithmetic_df),
        "pages_with_totals": len(validatable),
        "pages_matching": len(validatable[validatable["status"] == "match"]) if len(validatable) > 0 else 0,
        "pages_mismatching": len(validatable[validatable["status"] == "mismatch"]) if len(validatable) > 0 else 0,
        "details": arithmetic_df,
    }
    
    # 3. Summary
    range_issue_rate = (report["currency_range_validation"]["rows_with_issues"] / len(df) * 100) if len(df) > 0 else 0
    
    report["summary"] = {
        "total_rows": len(df),
        "rows_with_currency_issues": report["currency_range_validation"]["rows_with_issues"],
        "currency_issue_rate": round(range_issue_rate, 2),
        "pages_with_arithmetic_match": report["arithmetic_validation"]["pages_matching"],
        "pages_with_arithmetic_mismatch": report["arithmetic_validation"]["pages_mismatching"],
    }
    
    return report


def summarize_extraction_results(df: pd.DataFrame) -> dict:
    """Generate summary statistics for an extraction."""
    if "file_id" in df.columns and "page_number" in df.columns:
        total_pages = df.groupby(["file_id", "page_number"]).ngroups
    else:
        total_pages = 0
    
    return {
        "total_rows": len(df),
        "total_pages": total_pages,
        "total_files": df["file_id"].nunique() if "file_id" in df.columns else 0,
        "row_types": df["row_type"].value_counts().to_dict() if "row_type" in df.columns else {},
        "page_types": df["page_type"].value_counts().to_dict() if "page_type" in df.columns else {},
        "avg_confidence": round(df["confidence_score"].mean(), 3) if "confidence_score" in df.columns else None,
        "low_confidence_count": len(df[df["confidence_score"] < 0.6]) if "confidence_score" in df.columns else 0,
    }