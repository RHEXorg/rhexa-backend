# app/ingestion/loader.py
"""
Universal File Loader
Automatically detects file type and routes to appropriate ingestor.
Main entry point for document ingestion in RheXa.
"""

import os
from typing import Optional
from .pdf_ingestor import PDFIngestor
from .txt_ingestor import TXTIngestor
from .csv_ingestor import CSVIngestor
from .excel_ingestor import ExcelIngestor


# Mapping of file extensions to ingestor classes
INGESTOR_MAP = {
    '.pdf': PDFIngestor,
    '.txt': TXTIngestor,
    '.csv': CSVIngestor,
    '.xlsx': ExcelIngestor,
    '.xls': ExcelIngestor,
}


def load_file(file_path: str, organization_id: Optional[int] = None) -> str:
    """
    Universal file loader that detects file type and extracts text.
    
    This is the main entry point for document ingestion in RheXa.
    It automatically selects the appropriate ingestor based on file extension.
    
    Args:
        file_path (str): Path to the file to ingest
        organization_id (Optional[int]): Organization ID for multi-tenant context
                                         (will be used when saving to database)
    
    Returns:
        str: Extracted and cleaned text content
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is not supported
        Exception: If ingestion fails
        
    Example:
        >>> text = load_file("documents/report.pdf", organization_id=123)
        >>> print(text[:100])
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # Check if file type is supported
    if ext not in INGESTOR_MAP:
        supported = ', '.join(INGESTOR_MAP.keys())
        raise ValueError(f"Unsupported file type '{ext}'. Supported types: {supported}")
    
    # Get appropriate ingestor class
    ingestor_class = INGESTOR_MAP[ext]
    
    # Create ingestor instance and load file
    ingestor = ingestor_class()
    
    try:
        text = ingestor.load(file_path)
        
        # TODO: When implementing database storage, use organization_id here
        # Example: save_document(text, file_path, organization_id)
        
        return text
    except Exception as e:
        raise Exception(f"Failed to load file '{file_path}': {str(e)}")


def get_supported_extensions() -> list[str]:
    """
    Get list of supported file extensions.
    
    Returns:
        list[str]: List of supported file extensions
    """
    return list(INGESTOR_MAP.keys())
