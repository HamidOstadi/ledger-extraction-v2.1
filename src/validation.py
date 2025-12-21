"""
Validation utilities for the Ledger OCR Project V2
"""

import pandas as pd
from src.config import COLUMNS


def compare_with_ground_truth(
    df_extracted: pd.DataFrame,
    df_ground_truth: pd.DataFrame,
    key_columns: list[str] = ["file_id", "page_number", "row_index"],
) -> pd.DataFrame:
    """
    Compare extracted data with ground truth (manual transcription).
    
    Args:
        df_extracted: DataFrame from AI extraction
        df_ground_truth: DataFrame from manual transcription
        key_columns: Columns to join on
    
    Returns:
        Merged DataFrame with _extracted and _truth suffixes for comparison
    """
    comparison = df_ground_truth.merge(
        df_extracted,
        on=key_columns,
        suffixes=("_truth", "_extracted"),
        how="outer",
        indicator=True,
    )
    
    return comparison


def calculate_field_accuracy(
    comparison_df: pd.DataFrame,
    field_name: str,
) -> dict:
    """
    Calculate accuracy metrics for a specific field.
    
    Args:
        comparison_df: Output from compare_with_ground_truth
        field_name: Base field name (e.g., "amount_pounds")
    
    Returns:
        Dictionary with match_count, total_count, accuracy_pct
    """
    truth_col = f"{field_name}_truth"
    extracted_col = f"{field_name}_extracted"
    
    if truth_col not in comparison_df.columns or extracted_col not in comparison_df.columns:
        return {"error": f"Field {field_name} not found in comparison"}
    
    # Only compare rows that exist in both
    both_present = comparison_df[comparison_df["_merge"] == "both"].copy()
    
    if len(both_present) == 0:
        return {"match_count": 0, "total_count": 0, "accuracy_pct": 0.0}
    
    # Normalize values for comparison
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


def generate_accuracy_report(
    comparison_df: pd.DataFrame,
    fields_to_check: list[str] = None,
) -> pd.DataFrame:
    """
    Generate an accuracy report for multiple fields.
    
    Args:
        comparison_df: Output from compare_with_ground_truth
        fields_to_check: List of field names to check (default: key fields)
    
    Returns:
        DataFrame with accuracy metrics per field
    """
    if fields_to_check is None:
        fields_to_check = [
            "row_type",
            "description",
            "amount_pounds",
            "amount_shillings",
            "amount_pence_whole",
            "amount_pence_fraction",
        ]
    
    results = []
    for field in fields_to_check:
        metrics = calculate_field_accuracy(comparison_df, field)
        metrics["field"] = field
        results.append(metrics)
    
    return pd.DataFrame(results)[["field", "match_count", "total_count", "accuracy_pct"]]


def verify_page_balance(
    df_page: pd.DataFrame,
    pounds_col: str = "amount_pounds",
    shillings_col: str = "amount_shillings",
    pence_col: str = "amount_pence_whole",
) -> dict:
    """
    Verify if totals on a balance sheet page are mathematically correct.
    
    Args:
        df_page: DataFrame for a single page
        pounds_col, shillings_col, pence_col: Column names
    
    Returns:
        Dictionary with verification results
    """
    # Separate entries and totals
    entries = df_page[df_page["row_type"] == "entry"].copy()
    totals = df_page[df_page["row_type"] == "total"].copy()
    
    if len(totals) == 0:
        return {"status": "no_totals", "message": "No total rows found on page"}
    
    def safe_sum(series):
        """Convert to numeric and sum, treating blanks as 0."""
        return pd.to_numeric(series.replace("", "0"), errors="coerce").fillna(0).sum()
    
    # Sum all entries
    entry_pounds = safe_sum(entries[pounds_col])
    entry_shillings = safe_sum(entries[shillings_col])
    entry_pence = safe_sum(entries[pence_col])
    
    # Convert to total pence for easier comparison
    entry_total_pence = (entry_pounds * 240) + (entry_shillings * 12) + entry_pence
    
    # Get the last total row (usually the final sum)
    last_total = totals.iloc[-1]
    total_pounds = pd.to_numeric(str(last_total[pounds_col]).replace("", "0") or "0", errors="coerce") or 0
    total_shillings = pd.to_numeric(str(last_total[shillings_col]).replace("", "0") or "0", errors="coerce") or 0
    total_pence = pd.to_numeric(str(last_total[pence_col]).replace("", "0") or "0", errors="coerce") or 0
    
    stated_total_pence = (total_pounds * 240) + (total_shillings * 12) + total_pence
    
    difference = abs(entry_total_pence - stated_total_pence)
    matches = difference == 0
    
    return {
        "status": "verified" if matches else "mismatch",
        "calculated_total_pence": int(entry_total_pence),
        "stated_total_pence": int(stated_total_pence),
        "difference_pence": int(difference),
        "matches": matches,
    }


def summarize_extraction_results(df: pd.DataFrame) -> dict:
    """
    Generate summary statistics for an extraction.
    
    Args:
        df: Complete extracted DataFrame
    
    Returns:
        Dictionary with summary statistics
    """
    # Count unique file+page combinations for accurate page count
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