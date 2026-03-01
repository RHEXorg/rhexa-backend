# app/ingestion/utils.py
"""
Utility functions for text processing and cleaning.
Used across all ingestors to ensure consistent text quality.
"""

import re


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.
    
    Removes:
    - Extra whitespace and newlines
    - Multiple consecutive spaces
    - Leading/trailing whitespace
    
    Args:
        text (str): Raw text to clean
        
    Returns:
        str: Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Replace multiple newlines with double newline (preserve paragraphs)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove spaces at the beginning and end of lines
    text = '\n'.join(line.strip() for line in text.split('\n'))
    
    # Remove multiple consecutive blank lines
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # Strip leading and trailing whitespace
    text = text.strip()
    
    return text


def truncate_text(text: str, max_length: int = 300) -> str:
    """
    Truncate text to a maximum length for preview purposes.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length (default: 300)
        
    Returns:
        str: Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
