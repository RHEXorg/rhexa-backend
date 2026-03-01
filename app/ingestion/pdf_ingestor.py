# app/ingestion/pdf_ingestor.py
"""
PDF Document Ingestor
Extracts text from PDF files using PyMuPDF (fitz).
Handles multi-page PDFs and preserves text structure.
"""

import fitz  # PyMuPDF
from .base import BaseIngestor
from .utils import clean_text


class PDFIngestor(BaseIngestor):
    """
    Ingestor for PDF documents.
    
    Uses PyMuPDF for fast and accurate text extraction.
    Multi-tenant: organization_id will be linked when saving Document record.
    """
    
    def load(self, source: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            source (str): Path to the PDF file
            
        Returns:
            str: Extracted and cleaned text from all pages
            
        Raises:
            Exception: If PDF cannot be opened or read
        """
        try:
            # Open the PDF file
            doc = fitz.open(source)
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(text)
            
            # Close the document
            doc.close()
            
            # Combine all pages with double newline separator
            full_text = "\n\n".join(text_parts)
            
            # Clean and return
            return clean_text(full_text)
            
        except Exception as e:
            raise Exception(f"Failed to process PDF file '{source}': {str(e)}")
