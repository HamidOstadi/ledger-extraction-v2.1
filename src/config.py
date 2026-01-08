"""
Configuration settings for the Ledger OCR Project V2
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o"

# Directory paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
IMAGES_DIR = PROJECT_ROOT / "images"

# Ensure output directories exist
OUTPUTS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Master column schema (21 columns + 1 new confidence score)
COLUMNS = [
    "file_id",
    "page_number",
    "page_type",
    "page_title",
    "row_index",
    "row_type",
    "date_raw",
    "description",
    "amount_pounds",
    "amount_shillings",
    "amount_pence_whole",
    "amount_pence_fraction",
    "is_total_row",
    "group_brace_id",
    "transaction_type",      # NEW: Credit/Debit for balance sheets
    "num_col_1",
    "num_col_2",
    "num_col_3",
    "num_col_4",
    "num_col_5",
    "num_col_6",
    "confidence_score",      # NEW: Computed 0.0-1.0 score
    "entry_confidence",
    "notes",
]

# Valid values for categorical fields
VALID_ROW_TYPES = ["entry", "section_header", "total", "title"]
VALID_PAGE_TYPES = ["ledger", "balance_sheet"]
VALID_PENCE_FRACTIONS = ["", "1/4", "1/2", "3/4"]
VALID_TRANSACTION_TYPES = ["", "credit", "debit", "income", "expenditure"]

# PDF processing settings
PDF_ZOOM = 2.0  # Resolution multiplier for image conversion