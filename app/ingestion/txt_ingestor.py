# app/ingestion/txt_ingestor.py
"""
Plain Text Ingestor
Handles .txt files with automatic encoding detection.
Supports UTF-8, Latin-1, and other common encodings.
"""

from .base import BaseIngestor
from .utils import clean_text


class TXTIngestor(BaseIngestor):
    """
    Ingestor for plain text files (.txt).
    
    Attempts multiple encodings to handle various text formats.
    Multi-tenant: organization_id will be linked when saving Document record.
    """
    
    def load(self, source: str) -> str:
        """
        Read and extract text from a plain text file.
        
        Args:
            source (str): Path to the text file
            
        Returns:
            str: Cleaned text content
            
        Raises:
            Exception: If file cannot be read with any supported encoding
        """
        # Try multiple encodings in order of likelihood
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(source, 'r', encoding=encoding) as f:
                    text = f.read()
                return clean_text(text)
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise Exception(f"Failed to read text file '{source}': {str(e)}")
        
        # If all encodings fail
        raise Exception(f"Failed to decode text file '{source}' with supported encodings: {encodings}")
