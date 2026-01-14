# Historical Ledger OCR Project
## Executive Summary — Version 2.4

**Author:** Hamid Ostadi  
**Date:** January 2026  
**Supervisor:** H-AI KHu Lab

---

## Overview

Version 2.4 addresses the regression issue identified in V2.3 through systematic diagnostic testing. By isolating whether the model or the prompt caused the regression, we identified that **gpt-4o was the problem**, not the vertical line detection prompt. Reverting to gpt-4.1-mini while keeping the improved prompt resolved the issues.

**Key Results:**
- **7,454 rows** extracted from **268 pages** (restored from V2.3's 257)
- **126 currency violations (1.69%)** — improved from V2.2's 198 (2.65%)
- **Zero extraction errors** — all failed pages recovered
- **11 arithmetic matches** — best across all versions

---

## Supervisor Feedback & Investigation

### Feedback Received (V2.3 Review)

> "The performance of V2.3 on regular pages has shown a relatively obvious decline... The data that was stable in the old version now shows a large number of column offsets."

### Diagnostic Question

**Is the regression caused by the MODEL (gpt-4o) or the PROMPT (vertical line detection)?**

### Experiment Design

We tested the same three regressed pages with different model/prompt combinations:

| Configuration | 1895 P2 | 1873 P3 | 1881 P7 |
|---------------|---------|---------|---------|
| V2.2: gpt-4.1-mini + original prompt | 0 | 0 | 0 |
| V2.3: gpt-4o + vertical line prompt | 5 | 4 | 3 |
| **Test: gpt-4.1-mini + vertical line prompt** | **2** | **0** | **0** |

### Finding

When using gpt-4.1-mini with the V2.3 prompt:
- 1873 P3: 0 issues (same as V2.2) ✓
- 1881 P7: 0 issues (same as V2.2) ✓
- 1895 P2: 2 issues (better than V2.3's 5)

**Conclusion:** The regression was caused by **gpt-4o**, not the vertical line prompt. gpt-4o interprets visual layouts differently and introduced errors on pages that gpt-4.1-mini handled correctly.

---

## V2.4 Solution

Based on the diagnostic findings:

1. **Reverted to gpt-4.1-mini** — More stable and consistent for these ledgers
2. **Kept vertical line prompt** — The prompt improvements are valid and helpful
3. **Added retry mechanism** — Recover failed pages with simplified prompt and higher token limit

---

## Results

### Version Comparison

| Metric | V2.2 | V2.3 | V2.4 |
|--------|------|------|------|
| Model | gpt-4.1-mini | gpt-4o | gpt-4.1-mini |
| Prompt | Original | Vertical Line | Vertical Line |
| Total Rows | 7,477 | 6,681 | **7,454** |
| Total Pages | 268 | 257 | **268** |
| Currency Issues | 198 (2.65%) | 94 (1.41%) | **126 (1.69%)** |
| Arithmetic Match | 9 | 3 | **11** |
| Extraction Errors | 0 | 14 | **0** |

### Page Recovery

V2.4 initially had 17 failed pages due to JSON parsing errors. A retry mechanism with:
- Simplified prompt
- Increased max_tokens (4096 → 8192)

Successfully recovered **all 17 pages** (804 additional rows).

### Complexity Analysis

| Complexity | Pages | Rows | Issues | Error Rate |
|------------|-------|------|--------|------------|
| Simple | 87 | 1,684 | 30 | 1.78% |
| Moderate | 115 | 3,474 | 27 | **0.78%** |
| Complex | 66 | 2,296 | 69 | **3.01%** |

**Observation:** Complex pages have ~4x higher error rates than moderate pages. This remains a target for future improvement.

---

## Key Insights

### 1. Model Selection Matters More Than Expected

gpt-4o, despite being a "better" model, performed worse on these historical ledgers. This suggests:
- Newer/larger models aren't always better for specific tasks
- Domain-specific testing is essential before switching models

### 2. Vertical Line Detection Prompt Works

The prompt improvement from V2.3 is valid — it helps with column alignment when paired with the right model (gpt-4.1-mini).

### 3. Retry Mechanisms Are Essential

JSON parsing errors can be recovered with:
- Simplified prompts (less complexity = more stable output)
- Higher token limits (prevent truncation)

### 4. Complex Pages Need Special Attention

The 3.01% error rate on complex pages (vs 0.78% on moderate) indicates that a one-size-fits-all approach has limitations.

---

## Deliverables

| File | Description |
|------|-------------|
| `ledger_transcription_v2.4_latest.xlsx` | Complete extracted dataset (7,454 rows) |
| `currency_issues_v2.4_*.csv` | Rows with currency violations |
| `arithmetic_validation_v2.4_*.csv` | Page-by-page arithmetic results |
| `complexity_analysis_v2.4_*.csv` | Page complexity classification |
| `chart_v24_diagnostic_test.png` | Model comparison experiment |
| `chart_v24_version_comparison.png` | V2.2 vs V2.3 vs V2.4 metrics |
| `chart_v24_complexity_analysis.png` | Error rates by page complexity |
| `chart_v24_page_recovery.png` | Failed page recovery results |
| `chart_v24_investigation_process.png` | Diagnostic process flowchart |

**Repository:** https://github.com/HamidOstadi/ledger-extraction-v2.1

---

## Proposed Next Steps (V2.5)

1. **Adaptive Prompting for Complex Pages**
   - Use different prompts based on page complexity
   - Simple pages: Original prompt (less overhead)
   - Complex pages: Enhanced prompt with additional guidance

2. **Pre-Classification Pipeline**
   - Quick layout scan before full extraction
   - Route pages to appropriate extraction strategy

3. **Investigate Arithmetic Mismatch**
   - Only 11 of 223 pages (4.9%) have correct sums
   - May require digit-level verification

---

## Conclusion

V2.4 successfully resolved the V2.3 regression through systematic diagnostic testing:

- **Identified root cause:** gpt-4o model, not the prompt
- **Implemented solution:** Reverted to gpt-4.1-mini with improved prompt
- **Recovered all data:** Zero extraction errors, 7,454 rows extracted

The investigation process demonstrated the value of hypothesis-driven debugging when addressing performance regressions. Complex pages remain challenging (3.01% error rate) and will be the focus of V2.5 development.

---

*Report generated: January 2026*
