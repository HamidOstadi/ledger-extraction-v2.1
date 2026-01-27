# Historical Ledger OCR Project
## Executive Summary — Version 2.6

**Author:** Hamid Ostadi  
**Date:** January 2026  
**Supervisor:** H-AI KHu Lab

---

## Overview

Version 2.6 addressed supervisor feedback regarding text segmentation and numerical precision by implementing a **dual-prompt system** with specialized handling for complex dual-column pages. The solution introduced a new `side` field to the schema and split extraction for 1889.pdf, achieving the **lowest currency issue rate** and **highest row count** of any version.

**Key Results:**
- **7,610 rows** extracted from **271 pages** — most of any version
- **102 currency violations (1.34%)** — lowest error rate achieved
- **Zero extraction errors** — all 15 failed pages recovered
- **1889.pdf: Zero currency issues** — split extraction with Z-pattern works perfectly

---

## Supervisor Feedback & Investigation

### Feedback Received (V2.5 Review)

Jiani identified two primary areas for improvement:

> 1. **Text Segmentation Errors:** Page segmentation for text sections is too granular. Many text blocks are being cut off, preserving only the first half of the original image text.
> 2. **Numerical Precision Gap:** Although accuracy is roughly on par with the best performance levels, another member (Jungwoo) has achieved a higher degree of precision in digital recognition.

### Investigation Conducted

**1. Text Truncation Analysis**

We manually reviewed approximately **50 rows** across three categories:
- Short descriptions (< 10 characters)
- Medium descriptions (50-80 characters)
- Long descriptions (> 100 characters)

**Finding:** No major truncation issues were found in the general extraction. Descriptions were captured in full length without missing characters. The model successfully handles multi-line descriptions that wrap across two lines in the original documents.

**Exception Identified:** File **1889.pdf** has a completely different structure (dual-column balance sheet) requiring specialized handling.

**2. Jungwoo's Approach Analysis**

We analyzed Jungwoo's extraction prompts and identified several advanced techniques:
- Multi-agent pipeline (Context Agent → Extraction Agent → Correction Agent)
- Specialized complex page prompt with "Z-pattern" extraction
- `side` field for tracking left/right columns

**Comparison Deferred:** Jungwoo's sample output (1700 Page 7) could not be compared directly as **1700.pdf is not included in our dataset** of 33 files. We recommend requesting this file from supervisors to enable direct comparison.

---

## V2.6 Solution: Dual-Prompt System

Based on the investigation findings, we implemented a two-pronged approach:

### 1. Schema Update

Added a new `side` field to track column position:

| `side` Value | Meaning | Files |
|--------------|---------|-------|
| `"NA"` | Standard single-column ledger | 32 files (7,337 rows) |
| `"left"` | Receipts column (dual-column) | 1889.pdf (148 rows) |
| `"right"` | Payments column (dual-column) | 1889.pdf (125 rows) |
| `"center"` | Page title spanning full width | 1889.pdf (5 rows) |

### 2. Standard Prompt (32 Files)

For regular single-column ledgers:
- Original V2.5 prompt with `side = "NA"`
- Token limit: 4,096

### 3. Complex Prompt with Split Extraction (1889.pdf)

For dual-column balance sheets:
- **Z-Pattern Extraction:** Extract LEFT side (Receipts) first, then RIGHT side (Payments)
- **Two API Calls Per Page:** Prevents token limit truncation
- **Token Limit:** 8,192 per call
- **Automatic Detection:** File routing based on file_id

### 4. Retry Mechanism

For failed pages due to JSON truncation:
- Simplified prompt with essential instructions only
- Increased token limit (8,192 → 16,384)
- Successfully recovered all 15 failed pages

---

## Results

### Version Comparison

| Metric | V2.2 | V2.4 | V2.5 | V2.6 (Final) | Best |
|--------|------|------|------|--------------|------|
| Model | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1-mini | — |
| Prompt | Original | Vertical Line | Original | Original + Split | — |
| Total Rows | 7,477 | 7,454 | 7,592 | **7,610** | **V2.6** |
| Total Pages | 268 | 268 | 271 | **271** | V2.5/V2.6 |
| Currency Issues | 198 (2.65%) | 126 (1.69%) | 177 (2.33%) | **102 (1.34%)** | **V2.6** |
| Extraction Errors | 0 | 0 | 0 | **0** | All |

### Page Recovery

| Stage | Failed Pages | Total Rows |
|-------|--------------|------------|
| V2.6 Initial | 15 | 6,956 |
| V2.6 After Recovery | **0** | **7,610** |

All 15 failed pages were successfully recovered, adding **654 rows** to the dataset.

### 1889.pdf Split Extraction Results

| Side | Rows | Currency Issues |
|------|------|-----------------|
| Center (Title) | 5 | 0 |
| Left (Receipts) | 148 | 0 |
| Right (Payments) | 125 | 0 |
| **Total** | **273** | **0** |

The split extraction approach achieved **zero currency violations** on the complex dual-column file.

### Currency Issues by File Type

| File Type | Rows | Currency Issues | Rate |
|-----------|------|-----------------|------|
| Standard Files (32) | 7,337 | 102 | 1.39% |
| Complex File (1889) | 273 | 0 | 0.00% |
| **Total** | **7,610** | **102** | **1.34%** |

---

## Key Insights

### 1. Split Extraction Solves Token Limit Issues

The 1889.pdf file initially failed extraction due to JSON truncation (response exceeded token limit with ~93 rows per page). By splitting into LEFT and RIGHT extractions:
- Each call stays within token limits
- Complete data is captured without truncation
- Zero currency violations achieved

### 2. Text Segmentation Is Not a Major Issue

Manual verification of ~50 rows found no significant truncation problems. The model handles:
- Multi-line descriptions that wrap across lines
- Long descriptions (150+ characters)
- Latin text and historical spelling

### 3. Currency Issue Rate Reduced by 49%

| Version | Currency Issue Rate | Change from V2.2 |
|---------|---------------------|------------------|
| V2.2 | 2.65% | — |
| V2.4 | 1.69% | -36% |
| V2.5 | 2.33% | -12% |
| V2.6 | **1.34%** | **-49%** |

### 4. Specialized Handling Outperforms Generic Approaches

The 1889.pdf results demonstrate that **document-specific prompts** can achieve significantly better accuracy than one-size-fits-all approaches.

---

## Deliverables

| File | Description |
|------|-------------|
| `ledger_transcription_v2.6_latest.xlsx` | Complete extracted dataset (7,610 rows) |
| `currency_issues_v2.6_*.csv` | Rows with currency violations (102 rows) |
| `extraction_errors_v2.6_*.csv` | Error log (all recovered) |
| `chart_v26_version_comparison.png` | V2.2 vs V2.4 vs V2.5 vs V2.6 metrics |
| `chart_v26_currency_progression.png` | Currency issue rate trend |
| `chart_v26_1889_split_results.png` | 1889.pdf split extraction results |
| `chart_v26_page_recovery.png` | Page recovery (15 → 0) |
| `chart_v26_development_process.png` | Development flow diagram |
| `chart_v26_side_distribution.png` | Side field distribution |

**Repository:** https://github.com/HamidOstadi/ledger-extraction-v2.1

---

## Recommendations

### For This Dataset

V2.6 is the recommended version for this dataset:
- Highest row count (7,610)
- Lowest currency issue rate (1.34%)
- Proper handling of complex dual-column pages

### For Future Development

1. **Apply Split Extraction to Other Complex Files**
   - If additional dual-column or multi-section files are identified, use the same approach
   - The `side` field infrastructure is already in place

2. **Investigate Remaining Currency Issues**
   - 102 issues remain in standard files
   - Top files: 1865 (22), 1869 (9), 1873 (8)
   - Consider targeted prompt refinement for these files

3. **Compare with Jungwoo's Results**
   - Request 1700.pdf from supervisors
   - Enable direct accuracy comparison
   - Evaluate adoption of correction agent approach

4. **Correction Agent (Future V2.7)**
   - Add post-extraction audit step
   - "Forensic" verification of flagged rows
   - Could further reduce currency violations

---

## Conclusion

V2.6 successfully addressed the supervisor feedback through systematic investigation and targeted solutions:

- **Text segmentation:** Manual verification of ~50 rows confirmed no major truncation issues; 1889.pdf identified as requiring special handling
- **Numerical precision:** Achieved lowest currency issue rate (1.34%) through dual-prompt system and split extraction
- **1889.pdf:** Zero currency violations with Z-pattern extraction approach
- **Data completeness:** 7,610 rows extracted (highest of any version) with zero errors

V2.6 represents the **best-performing version** across all key metrics. The dual-prompt architecture provides a foundation for handling diverse document layouts while maintaining high extraction accuracy.

---

*Report generated: January 2026*
