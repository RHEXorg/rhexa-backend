# app/ingestion/excel_ingestor.py
"""
Excel Document Ingestor
Handles .xlsx and .xls files using pandas and openpyxl.
Processes all sheets in the workbook.
"""

import pandas as pd
from .base import BaseIngestor
from .utils import clean_text


class ExcelIngestor(BaseIngestor):
    """
    Ingestor for Excel files (.xlsx, .xls).
    
    Processes all sheets in the workbook and converts to text format.
    Multi-tenant: organization_id will be linked when saving Document record.
    """
    
    def load(self, source: str) -> str:
        """
        Read and convert Excel file to text format.
        
        Args:
            source (str): Path to the Excel file
            
        Returns:
            str: Text representation of all sheets with headers and data
            
        Raises:
            Exception: If Excel file cannot be read or parsed
        """
        try:
            # Read all sheets from Excel file
            excel_file = pd.ExcelFile(source)
            sheet_names = excel_file.sheet_names
            
            text_parts = []
            
            # Add file header
            text_parts.append(f"Excel File: {source}")
            text_parts.append(f"Total Sheets: {len(sheet_names)}")
            text_parts.append("\n" + "="*80 + "\n")
            
            # Process each sheet
            for sheet_name in sheet_names:
                df = pd.read_excel(source, sheet_name=sheet_name)
                
                # Add sheet header
                text_parts.append(f"\n{'='*80}")
                text_parts.append(f"SHEET: {sheet_name}")
                text_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
                text_parts.append(f"Total Rows: {len(df)}")
                text_parts.append("="*80 + "\n")
                
                # Add data in highly semantic format
                for idx, row in df.iterrows():
                    row_data = []
                    for col in df.columns:
                        val = row[col]
                        if not pd.isna(val) and str(val).strip():
                            row_data.append(f"[{col}: {val}]")
                    
                    if row_data:
                        text_parts.append(f"Sheet '{sheet_name}' Row {idx + 1} Data: " + " ".join(row_data))
                        
                text_parts.append("\n" + "="*80 + "\n")
            
            # Use double newline to respect RecursiveCharacterTextSplitter chunking
            full_text = "\n\n".join(text_parts)
            
            return clean_text(full_text)
            
        except Exception as e:
            raise Exception(f"Failed to process Excel file '{source}': {str(e)}")
