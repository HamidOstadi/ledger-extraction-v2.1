# Historical Ledger Transcription using Multimodal AI

## Project Overview
This project automates the transcription of 18th–19th century hand-written parish ledgers using
vision-language models. The system extracts structured financial data from high-resolution PDF
scans into machine-readable Excel format.

The workflow includes:
- PDF page rendering with PyMuPDF
- Multimodal AI handwriting transcription
- Rule-based post-processing for currency fields
- Manual ground-truth validation and error-analysis
- Scalable batch processing across 30+ books

---

## Repository Contents
| File / Folder | Description |
|--------------|-------------|
| `main.ipynb` | Full notebook: code, evaluation, and embedded report |
| `main.pdf` | Final report PDF (submitted deliverable) |
| `ledger_transcription.xlsx` | Final structured dataset |
| `images/` | Extracted figures for report |
| `data/` | Source PDFs (if included) |

---

## Key Results
- **~200 scanned pages processed** (years 1704–1900)
- **7,344 ledger rows** extracted and structured
- Pence fractions normalized (`1/4`, `1/2`, `3/4`)
- Section headers identified and separated from entries

---

## Requirements
Install dependencies:

```bash
pip install openai pymupdf pillow pandas matplotlib
```
Launch:

```bash
jupyter notebook main.ipynb
```

### Author
**Hamid Ostadi**
Project developed as part of a multimodal AI transcription assessment guided by Dr. Kejia Hu.

---
