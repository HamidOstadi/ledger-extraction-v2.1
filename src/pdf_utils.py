"""
PDF processing utilities for the Ledger OCR Project V2
"""

import io
import base64
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path

from src.config import PDF_ZOOM


def pdf_page_to_image(pdf_path: str | Path, page_number: int, zoom: float = PDF_ZOOM) -> Image.Image:
    """
    Convert a specific page in a PDF to a PIL Image.
    
    Args:
        pdf_path: Path to the PDF file
        page_number: 1-based page number (1 = first page)
        zoom: Resolution multiplier for better OCR quality
    
    Returns:
        PIL Image object
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]  # PyMuPDF uses 0-based indexing
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    doc.close()
    return img


def pil_image_to_base64(img: Image.Image) -> str:
    """
    Convert PIL Image to base64-encoded PNG string.
    
    Args:
        img: PIL Image object
    
    Returns:
        Base64-encoded string (without data URL header)
    """
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")


def get_pdf_page_count(pdf_path: str | Path) -> int:
    """
    Get the number of pages in a PDF.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Number of pages
    """
    doc = fitz.open(pdf_path)
    count = doc.page_count
    doc.close()
    return count


def list_pdf_files(data_dir: Path) -> list[Path]:
    """
    List all PDF files in a directory, sorted alphabetically.
    
    Args:
        data_dir: Path to directory containing PDFs
    
    Returns:
        List of Path objects for each PDF
    """
    return sorted(data_dir.glob("*.pdf"))