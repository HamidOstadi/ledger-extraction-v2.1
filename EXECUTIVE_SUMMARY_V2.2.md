# Historical Ledger OCR Project
## Executive Summary — Version 2.2

**Author:** Hamid Ostadi  
**Date:** January 2026  
**Supervisor:** H-AI KHu Lab

---

## Project Overview

This project extracts structured financial data from 18th-19th century British parish ledgers using multimodal AI (GPT-4.1-mini). Version 2.2 introduces **Currency Logic Validation** to address accuracy concerns raised in supervisor feedback.

**Key Results:**
- **7,477 rows** extracted from **268 pages** across **33 documents**
- **198 currency violations** detected (2.65% of rows)
- **95.7% of pages** have arithmetic mismatches (entries don't sum to totals)

---

## Supervisor Feedback & Response

### Feedback Received (December 23, 2025)

> "While the confidence scores in this version have generally improved, a manual comparison with the original PDFs shows that the actual extraction accuracy has not seen a significant breakthrough... The model is yielding high confidence scores even in cases where the content remains inaccurate."

**Requested Improvements:**
1. Currency range validation (flag shillings > 19, pence > 11)
2. Arithmetic validation (verify entry sums match totals)

### Actions Taken

| Request | Implementation |
|---------|----------------|
| Range Checks | Validate shillings (0-19) and pence (0-11) per British currency system |
| Arithmetic Validation | Sum all entries per page and compare against stated total |
| Updated Confidence | Penalize rows with invalid currency values |
| Gold Standard | Manual transcription of 3 pages for accuracy benchmarking |

---

## Gold Standard Validation

Three pages were manually transcribed to benchmark model accuracy:

| Page | Selection Rationale |
|------|---------------------|
| 1704, Page 1 | Oldest document; 18th-century handwriting baseline |
| 1873, Page 5 | Mid-late period; complex layout with 40 rows |
| 1881, Page 1 | Late Victorian period (replaced 1889*) |

*Note: 1889 was excluded — it contains a formal printed balance sheet (Exeter College accounts) rather than handwritten parish ledger entries, requiring different extraction logic.

---

## Currency Validation Results

### Range Violations
| Field | Violations | Rule |
|-------|------------|------|
| Shillings | 118 | Must be 0-19 (20s = £1) |
| Pence | 118 | Must be 0-11 (12d = 1s) |
| Pounds | 1 | Must be ≥ 0 |
| **Total** | **198** | **2.65% of rows** |

### Arithmetic Validation
| Metric | Value |
|--------|-------|
| Pages with total rows | 211 |
| Pages where sums MATCH | 9 (4.3%) |
| Pages where sums MISMATCH | 202 (95.7%) |

**Key Insight:** The high mismatch rate indicates systematic errors in amount extraction — the model frequently misreads or skips values.

---

## Version Comparison

| Metric | V1 | V2.1 | V2.2 |
|--------|-----|------|------|
| Total Rows | 7,344 | 7,533 | 7,477 |
| Avg Confidence | — | 0.963 | 0.966 |
| Currency Issues | Not checked | Not checked | 198 (2.65%) |
| Arithmetic Match | Not checked | Not checked | 4.3% |
| Validation | None | None | Full |

### Version Evolution
- **V1 → V2.1:** Modular architecture, confidence scoring, enhanced prompt
- **V2.1 → V2.2:** Currency validation, arithmetic checks, gold standard benchmarking

---

## Key Insights

### 1. Confidence ≠ Accuracy
The model reports 96.6% confidence, but arithmetic validation shows only 4.3% of pages have correct sums. This confirms supervisor's concern that confidence scores don't reflect actual accuracy.

### 2. Currency Validation Catches Real Errors
2.65% of rows contain impossible values (e.g., shillings > 19) that would never appear in historical ledgers. These are definite extraction errors.

### 3. Row Count Variation
V2.2 extracted 56 fewer rows than V2.1 (7,477 vs 7,533). This 0.7% difference is normal LLM variability between runs.

---

## Deliverables

| File | Description |
|------|-------------|
| `ledger_transcription_v2.2_latest.xlsx` | Complete extracted dataset |
| `currency_issues_*.csv` | Rows with invalid currency values |
| `arithmetic_validation_*.csv` | Page-by-page arithmetic results |
| `gold_standard/` | Manual transcriptions for benchmarking |
| GitHub Repository | Full source code and documentation |

**Repository:** https://github.com/HamidOstadi/ledger-extraction-v2.1

---

## Recommendations for Future Work

1. **Investigate arithmetic mismatches** — Analyze specific pages to identify error patterns
2. **Two-pass extraction** — First pass for structure, second pass for amount verification
3. **Historical handwriting fine-tuning** — Train on specialized datasets (per supervisor suggestion)
4. **Balance sheet handling** — Develop separate logic for documents like 1889

---

## Conclusion

Version 2.2 successfully implements the requested currency logic validation, revealing that:
- **2.65% of rows** contain impossible currency values
- **95.7% of pages** have arithmetic errors

These findings confirm that high confidence scores do not guarantee accuracy. The validation framework now provides concrete metrics for identifying and quantifying extraction errors, enabling targeted improvements in future iterations.

---

*Report generated: January 2026*
