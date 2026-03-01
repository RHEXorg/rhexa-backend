# app/ingestion/__init__.py
"""
RheXa Ingestion Module
Handles document ingestion for multi-tenant knowledge base platform.
Supports PDF, TXT, CSV, Excel with pluggable architecture.
"""

from .base import BaseIngestor
from .pdf_ingestor import PDFIngestor
from .txt_ingestor import TXTIngestor
from .csv_ingestor import CSVIngestor
from .excel_ingestor import ExcelIngestor
from .loader import load_file, get_supported_extensions
from .utils import clean_text

__all__ = [
    "BaseIngestor",
    "PDFIngestor",
    "TXTIngestor",
    "CSVIngestor",
    "ExcelIngestor",
    "load_file",
    "get_supported_extensions",
    "clean_text",
]
