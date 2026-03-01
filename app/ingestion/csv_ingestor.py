# app/ingestion/csv_ingestor.py
"""
CSV Document Ingestor
Converts CSV data to readable text format using pandas.
Preserves column headers and row structure.
"""

import pandas as pd
from .base import BaseIngestor
from .utils import clean_text


class CSVIngestor(BaseIngestor):
    """
    Ingestor for CSV files.
    
    Converts tabular data to text format suitable for AI processing.
    Multi-tenant: organization_id will be linked when saving Document record.
    """
    
    def load(self, source: str) -> str:
        """
        Read and convert CSV file to text format.
        
        Args:
            source (str): Path to the CSV file
            
        Returns:
            str: Text representation of CSV data with headers and rows
            
        Raises:
            Exception: If CSV cannot be read or parsed
        """
        try:
            # Read CSV file
            df = pd.read_csv(source)
            
            # Convert to text format optimized for RAG chunking
            text_parts = []
            
            # Add header information
            filename = source.split('/')[-1].split('\\')[-1]
            text_parts.append(f"DOCUMENT INFO: CSV File Name: {filename}")
            text_parts.append(f"Dataset contains {len(df)} rows. Columns: {', '.join(df.columns.tolist())}")
            text_parts.append("\n" + "="*80 + "\n")
            
            # Add data in highly semantic format so if a chunk breaks here, context is preserved
            for idx, row in df.iterrows():
                row_data = []
                for col in df.columns:
                    val = row[col]
                    if not pd.isna(val) and str(val).strip():
                        # We use structured inline format: [ColumnName: Value]
                        row_data.append(f"[{col}: {val}]")
                
                # Combine into a single paragraph per row.
                # Example: "Data Row 1: [Name: Alice] [Age: 30] [City: NY]"
                if row_data:
                    text_parts.append(f"Row {idx + 1} Data: " + " ".join(row_data))
            
            # Join with double newlines so RecursiveCharacterTextSplitter naturally breaks exactly at row boundaries
            full_text = "\n\n".join(text_parts)
            
            return clean_text(full_text)
            
        except Exception as e:
            raise Exception(f"Failed to process CSV file '{source}': {str(e)}")
