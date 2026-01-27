# Historical Ledger OCR Project
## Executive Summary — Version 2.5

**Author:** Hamid Ostadi  
**Date:** January 2026  
**Supervisor:** H-AI KHu Lab

---

## Overview

Version 2.5 investigated whether reverting to the V2.2 prompt (without vertical line detection) would improve digit accuracy, as suggested by gold standard testing. The approach combined the **V2.2 prompt** (proven digit accuracy) with **post-validation** (currency and arithmetic checks). While V2.5 achieved the highest row count and best arithmetic matching, V2.4 retained the lowest currency violation rate.

**Key Results:**
- **7,592 rows** extracted from **271 pages** — most of any version
- **177 currency violations (2.33%)** — higher than V2.4's 1.69%
- **Zero extraction errors** — all 12 failed pages recovered (608 rows)
- **12 arithmetic matches** — best across all versions

---

## Investigation: Digit Accuracy Analysis

### Hypothesis

Based on supervisor feedback that V2.4 showed regression on regular pages, we hypothesized that the **V2.2 original prompt** might have better digit recognition accuracy than V2.4's vertical line detection prompt.

### Gold Standard Comparison

We compared V2.2 and V2.4 extraction results against manually verified gold standard pages:

| Metric | V2.2 | V2.4 | Winner |
|--------|------|------|--------|
| Perfect Matches | 36.8% | 25.0% | **V2.2** |
| Pounds Accuracy | 42.6% | 33.8% | **V2.2** |
| Shillings Accuracy | 50.0% | 36.8% | **V2.2** |
| Pence Accuracy | 57.4% | 42.6% | **V2.2** |

### Critical Finding: 1881 Page 1

The most significant regression appeared on 1881 Page 1:

| Metric | V2.2 | V2.4 |
|--------|------|------|
| Perfect Matches | 61.9% | 14.3% |
| Wrong | 19.0% | 57.1% |

**Root Cause:** V2.4 extracted 26 entry rows vs V2.2's 21 rows. The vertical line detection prompt caused **row misalignment** — extra rows shifted all subsequent values, making them appear "wrong" even if individual digits were correct.

---

## V2.5 Strategy: Post-Validation Approach

Based on the diagnostic findings:

1. **Restored V2.2 prompt** — Proven digit accuracy without vertical line instructions
2. **Applied post-validation** — Currency range checks (shillings 0-19, pence 0-11) and arithmetic validation
3. **Kept gpt-4.1-mini** — Stable and consistent performance
4. **Implemented retry mechanism** — Recover failed pages with simplified prompt

### Rationale

Rather than modifying the prompt further, we chose post-validation because:
- Clear audit trail — raw extraction vs flagged issues
- Easy iteration — can improve validation without re-running extraction
- Diagnostic value — understand where errors originate

---

## Results

### Version Comparison

| Metric | V2.2 | V2.4 | V2.5 (Final) | Best |
|--------|------|------|--------------|------|
| Model | gpt-4.1-mini | gpt-4.1-mini | gpt-4.1-mini | — |
| Prompt | Original | Vertical Line | Original | — |
| Total Rows | 7,477 | 7,454 | **7,592** | **V2.5** |
| Total Pages | 268 | 268 | **271** | **V2.5** |
| Currency Issues | 198 (2.65%) | **126 (1.69%)** | 177 (2.33%) | **V2.4** |
| Arithmetic Match | 9 | 11 | **12** | **V2.5** |
| Extraction Errors | 0 | 0 | **0** | All |

### Page Recovery

V2.5 initially had 12 failed pages due to JSON parsing errors. The retry mechanism successfully recovered **all 12 pages**, adding **608 rows** to the dataset.

| Stage | Failed Pages | Total Rows |
|-------|--------------|------------|
| V2.5 Initial | 12 | 6,984 |
| V2.5 After Recovery | **0** | **7,592** |

### Complexity Analysis

| Complexity | Pages | Rows | Issues | Error Rate |
|------------|-------|------|--------|------------|
| Simple | 73 | 1,376 | 29 | 2.11% |
| Moderate | 115 | 3,468 | 68 | 1.96% |
| Complex | 83 | 2,748 | 80 | 2.91% |

**Observation:** V2.5 shows more uniform error rates across complexity levels (~2%) compared to V2.4's wider spread (0.78% moderate vs 3.01% complex).

---

## Key Insights

### 1. The Prompt vs Validation Trade-off

| Approach | Strength | Weakness |
|----------|----------|----------|
| V2.4 (Vertical Line Prompt) | Fewer currency violations (1.69%) | Row misalignment on some pages |
| V2.5 (Original Prompt + Post-Validation) | More rows extracted (7,592) | Higher currency violations (2.33%) |

### 2. LLM Variability is Significant

Even with identical prompts, the same model produces different results across runs:
- V2.5 test on 1881 P1: 33.3% perfect (vs V2.2's 61.9% on same prompt)
- Entry counts varied: V2.5 extracted 25 rows vs V2.2's 21 rows

This inherent variability means **aggregate metrics are more reliable** than individual page comparisons.

### 3. Vertical Line Detection Has Value

Despite causing row misalignment issues, V2.4's vertical line prompt achieved the **lowest currency violation rate (1.69%)**. The prompt helps the model identify column boundaries on complex pages.

### 4. Post-Validation Provides Audit Trail

The post-validation approach in V2.5 allows:
- Identification of specific problematic rows
- Analysis of error patterns by field (pence: 126, shillings: 77, pounds: 2)
- Clear separation of extraction vs validation issues

---

## Trade-off Analysis

| If You Prioritize... | Use Version |
|---------------------|-------------|
| Lowest currency errors | **V2.4** (1.69%) |
| Most data extracted | **V2.5** (7,592 rows) |
| Best arithmetic matching | **V2.5** (12 pages) |
| Most pages processed | **V2.5** (271 pages) |

---

## Deliverables

| File | Description |
|------|-------------|
| `ledger_transcription_v2.5_latest.xlsx` | Complete extracted dataset (7,592 rows) |
| `currency_issues_v2.5_*.csv` | Rows with currency violations (177 rows) |
| `extraction_errors_v2.5_*.csv` | Error log (all recovered) |
| `chart_v25_diagnostic_accuracy.png` | Gold standard accuracy comparison |
| `chart_v25_version_comparison.png` | V2.2 vs V2.4 vs V2.5 metrics |
| `chart_v25_complexity_analysis.png` | Error rates by page complexity |
| `chart_v25_page_recovery.png` | Failed page recovery results |
| `chart_v25_investigation_process.png` | Investigation process flowchart |

**Repository:** https://github.com/HamidOstadi/ledger-extraction-v2.1

---

## Recommendations

### For This Dataset

**Use V2.4** if currency accuracy is the priority (1.69% vs 2.33% error rate).

**Use V2.5** if completeness is the priority (7,592 rows vs 7,454 rows).

### For Future Development

1. **Hybrid Approach**
   - Use V2.4 prompt for complex pages (better column alignment)
   - Use V2.5 prompt for simple pages (fewer row alignment issues)

2. **Row Alignment Verification**
   - Add post-processing to detect row count mismatches
   - Flag pages where entry counts differ significantly between runs

3. **Ensemble Extraction**
   - Run extraction with both prompts
   - Merge results, preferring values where both agree

4. **Digit-Level Verification**
   - Investigate the 95% arithmetic mismatch rate
   - May require character-level OCR verification

---

## Conclusion

V2.5 successfully tested the hypothesis that the V2.2 prompt would improve digit accuracy. The investigation revealed:

- **V2.2 prompt does have better digit accuracy** on gold standard pages (36.8% vs 25.0% perfect matches)
- **However, V2.4's vertical line prompt has lower currency violations** at scale (1.69% vs 2.33%)
- **The root cause of regression** was row misalignment, not digit recognition
- **LLM variability** makes individual page comparisons unreliable; aggregate metrics are essential

V2.5 contributes the **most complete dataset** (7,592 rows from 271 pages) and the **best arithmetic matching** (12 pages), while V2.4 remains optimal for **currency accuracy**. Future work should explore hybrid approaches that combine the strengths of both versions.

---

*Report generated: January 2026*
