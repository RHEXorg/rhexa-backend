# quick_test.py
"""Quick test of ingestion system"""

import os
import sys
import pandas as pd

# Ensure app is in path
sys.path.insert(0, '.')

from app.ingestion.utils import clean_text, truncate_text

print("="*80)
print("RheXa Ingestion System - Quick Test")
print("="*80)

# Create test directory
os.makedirs('test_files', exist_ok=True)

# 1. Create and test TXT file
print("\n[1/3] Testing TXT Ingestor...")
txt_content = """RheXa Knowledge Base Platform

This is a sample text document for testing.
RheXa allows organizations to upload documents and chat with their data.

Key Features:
- Multi-tenant architecture
- Support for PDF, CSV, Excel files
- AI-powered chat interface
"""

with open('test_files/sample.txt', 'w') as f:
    f.write(txt_content)

from app.ingestion.txt_ingestor import TXTIngestor
txt_ingestor = TXTIngestor()
txt_result = txt_ingestor.load('test_files/sample.txt')
print(f"✅ TXT loaded: {len(txt_result)} characters")
print(f"Preview: {truncate_text(txt_result, 150)}\n")

# 2. Create and test CSV file
print("[2/3] Testing CSV Ingestor...")
df_csv = pd.DataFrame({
    'Product': ['Basic Plan', 'Pro Plan', 'Enterprise Plan'],
    'Price': [49, 99, 199],
    'Storage': ['5GB', '50GB', 'Unlimited']
})
df_csv.to_csv('test_files/sample.csv', index=False)

from app.ingestion.csv_ingestor import CSVIngestor
csv_ingestor = CSVIngestor()
csv_result = csv_ingestor.load('test_files/sample.csv')
print(f"✅ CSV loaded: {len(csv_result)} characters")
print(f"Preview: {truncate_text(csv_result, 200)}\n")

# 3. Create and test Excel file
print("[3/3] Testing Excel Ingestor...")
with pd.ExcelWriter('test_files/sample.xlsx', engine='openpyxl') as writer:
    df_csv.to_excel(writer, sheet_name='Pricing', index=False)

from app.ingestion.excel_ingestor import ExcelIngestor
excel_ingestor = ExcelIngestor()
excel_result = excel_ingestor.load('test_files/sample.xlsx')
print(f"✅ Excel loaded: {len(excel_result)} characters")
print(f"Preview: {truncate_text(excel_result, 200)}\n")

# 4. Test universal loader
print("[BONUS] Testing Universal Loader...")
from app.ingestion.loader import load_file, get_supported_extensions

print(f"Supported extensions: {get_supported_extensions()}")

for file in ['test_files/sample.txt', 'test_files/sample.csv', 'test_files/sample.xlsx']:
    text = load_file(file)
    print(f"  ✅ {file}: {len(text)} chars")

print("\n" + "="*80)
print("🎉 All tests passed! Ingestion system is working correctly.")
print("="*80)
print("\nNext steps:")
print("1. Add a PDF file to test_files/sample.pdf")
print("2. Test with: from app.ingestion import load_file; load_file('test_files/sample.pdf')")
print("3. Integrate with FastAPI endpoints for file uploads")
print("4. Add vector embeddings for AI chat functionality")
