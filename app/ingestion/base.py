# app/ingestion/base.py
"""
Base Ingestor Abstract Class
All document ingestors must inherit from this class and implement the load() method.
This ensures a consistent interface across all ingestion types.
"""

from abc import ABC, abstractmethod


class BaseIngestor(ABC):
    """
    Abstract base class for all document ingestors.
    
    Each ingestor processes a specific file type and returns cleaned text.
    Multi-tenant context (organization_id) will be passed when saving to DB.
    """
    
    @abstractmethod
    def load(self, source: str) -> str:
        """
        Load and process a document from the given source.
        
        Args:
            source (str): File path or URL to the document
            
        Returns:
            str: Extracted and cleaned text content
            
        Raises:
            Exception: If file cannot be read or processed
        """
        pass
    
    def get_file_type(self) -> str:
        """
        Returns the file type this ingestor handles.
        Useful for logging and debugging.
        """
        return self.__class__.__name__.replace("Ingestor", "").upper()
