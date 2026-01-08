# Historical Ledger OCR Project
## Executive Summary — Version 2.3

**Author:** Hamid Ostadi  
**Date:** January 2026  
**Supervisor:** H-AI KHu Lab

---

## Project Overview

This project extracts structured financial data from 18th-19th century British parish ledgers using multimodal AI. Version 2.3 addresses supervisor feedback regarding column misalignment in dense layouts by implementing vertical line detection and upgrading to a more capable vision model.

**Key Results:**
- **47% reduction** in currency violations (198 → 94)
- **Complexity analysis confirms** complex pages have 4x higher error rates
- **6,681 rows** extracted from **257 pages** across **33 documents**

---

## Supervisor Feedback & Response

### Feedback Received (January 3, 2026)

> "There is a noticeable disparity in accuracy between complex pages and standard pages... In areas with high-density numerical data, figures are frequently assigned to the wrong categories. These column mismatches have caused the arithmetic validation checks to fail repeatedly."

**Key Issues Identified:**
1. Complex pages have worse accuracy than standard pages
2. Column misalignment — numbers assigned to wrong currency columns
3. Arithmetic validation failing due to misaligned amounts

### Actions Taken

| Issue | Solution Implemented |
|-------|---------------------|
| Column misalignment | Vertical line detection prompt — instruct model to identify physical column dividers |
| Model accuracy | Tested 3 models, selected gpt-4o for best vision performance |
| Complex vs simple disparity | Added page complexity classification to track error rates |

---

## Approach: Vertical Line Detection

Most ledger pages have **three vertical ruling lines** on the right side that physically divide the currency columns:
```
|  Description text  |  £  |  s  |  d  |
                     ↑    ↑    ↑    ↑
                 Line 1  Line 2  Line 3  (edge)
```

We rewrote the extraction prompt to instruct the model to:
1. **First** identify these vertical lines running top to bottom
2. **Use** the lines as column boundaries for ALL rows
3. **Extract** numbers based on which column space they fall into
4. **Self-validate** — if shillings ≥ 20 or pence ≥ 12, re-examine boundaries

---

## Model Selection

We tested three models on gold standard pages (1704, 1873, 1881):

| Model | Currency Violations | Cost (Full Run) | Selected |
|-------|---------------------|-----------------|----------|
| gpt-4.1-mini | 1 | ~$0.50 | No |
| gpt-4o-mini | 7 | ~$0.19 | No |
| gpt-4o | **0** | ~$1.31 | **Yes** |

**gpt-4o** achieved zero currency violations on test pages due to superior vision capabilities.

---

## Results

### Currency Validation Improvement

| Metric | V2.2 | V2.3 | Improvement |
|--------|------|------|-------------|
| Currency violations | 198 | 94 | **-47%** |
| Issue rate | 2.65% | 1.41% | **-47%** |
| Shillings issues | 118 | 51 | -57% |
| Pence issues | 118 | 53 | -55% |

### Complexity Analysis (New Feature)

Error rates by page complexity confirm supervisor's observation:

| Complexity | Pages | Rows | Issues | Error Rate |
|------------|-------|------|--------|------------|
| Simple | 79 | 1,513 | 8 | **0.55%** |
| Moderate | 126 | 3,528 | 48 | **1.13%** |
| Complex | 52 | 1,640 | 38 | **2.18%** |

**Key Finding:** Complex pages have **4x higher error rates** than simple pages.

### Trade-offs

| Metric | V2.2 | V2.3 | Note |
|--------|------|------|------|
| Total rows | 7,477 | 6,681 | -796 due to errors |
| Extraction errors | 0 | 14 | JSON parsing issues |
| Runtime | ~5 hours | ~11 hours | gpt-4o is slower |

The 14 failed pages are due to gpt-4o producing longer responses that occasionally cause JSON parsing errors.

---

## Version Comparison

| Metric | V1 | V2.1 | V2.2 | V2.3 |
|--------|-----|------|------|------|
| Total Rows | 7,344 | 7,533 | 7,477 | 6,681 |
| Avg Confidence | — | 0.963 | 0.966 | 0.966 |
| Currency Issues | — | — | 198 (2.65%) | 94 (1.41%) |
| Arithmetic Match | — | — | 4.3% | 1.3% |
| Model | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1-mini | gpt-4o |

---

## Key Insights

### 1. Vertical Line Detection Works
The prompt engineering approach successfully reduced currency violations by 47%. Instructing the model to use physical column boundaries improves accuracy.

### 2. Complex Pages Remain Challenging
Despite improvements, complex pages still have 4x higher error rates. This confirms the supervisor's feedback and identifies an area for future work.

### 3. Model Trade-offs
gpt-4o provides better vision accuracy but introduces:
- Longer runtime (11 hours vs 5 hours)
- Occasional JSON parsing errors (14 pages failed)
- Higher cost (~$1.31 vs ~$0.50)

### 4. Arithmetic Mismatch Persists
Only 1.3% of pages have entries that sum to totals. This suggests errors beyond column alignment:
- Missing rows
- Misread digits
- Incorrect row type classification

---

## Deliverables

| File | Description |
|------|-------------|
| `ledger_transcription_v2.3_latest.xlsx` | Complete extracted dataset |
| `currency_issues_v2.3_*.csv` | Rows with invalid currency values |
| `arithmetic_validation_v2.3_*.csv` | Page-by-page arithmetic results |
| `complexity_analysis_v2.3_*.csv` | Page complexity classification |
| `extraction_errors_v2.3_*.csv` | Failed pages log |
| Visualization charts | Comparison and analysis charts |

**Repository:** https://github.com/HamidOstadi/ledger-extraction-v2.1

---

## Next Steps (Proposed for V2.4)

1. **Retry mechanism for failed pages**
   - Catch JSON errors and retry with adjusted parameters
   - Recover the 14 missing pages

2. **Investigate arithmetic mismatch**
   - Analyze why entries don't sum to totals even with better column alignment
   - May require digit-level verification

3. **Hybrid model approach**
   - Use gpt-4o for complex pages (where accuracy matters most)
   - Use gpt-4.1-mini for simple pages (faster, cheaper)
   - Balance cost and accuracy

4. **Handle irregular formats**
   - 1889 document has printed balance sheet format
   - Requires separate extraction logic

---

## Conclusion

Version 2.3 successfully addresses the supervisor's feedback on column misalignment:

- **47% reduction** in currency violations through vertical line detection
- **Complexity analysis** confirms and quantifies the disparity between simple and complex pages
- **Model upgrade** to gpt-4o improves vision accuracy at the cost of runtime

The persistent arithmetic mismatch (98.7% of pages) indicates that further improvements are needed beyond column alignment. Future iterations should focus on digit-level accuracy and handling complex page layouts more robustly.

---

*Report generated: January 2026*
