# test_ingestion.py
"""
Test script for RheXa document ingestion system.

This script tests all ingestors (PDF, TXT, CSV, Excel) by loading sample files
and displaying the first 300 characters of extracted text.

HOW TO RUN:
-----------
1. Create a 'test_files' directory in the project root
2. Add sample files: sample.pdf, sample.txt, sample.csv, sample.xlsx
3. Run: python test_ingestion.py

REQUIREMENTS:
-------------
Make sure all dependencies are installed:
pip install PyMuPDF pandas openpyxl

MULTI-TENANT NOTE:
------------------
In production, organization_id will be passed to load_file() and linked
to the Document model when saving to the database.
"""

import os
from app.ingestion import load_file, get_supported_extensions
from app.ingestion.utils import truncate_text


def test_ingestion():
    """Test all document ingestors with sample files."""
    
    print("="*80)
    print("RheXa Document Ingestion System - Test Suite")
    print("="*80)
    print(f"\nSupported file types: {', '.join(get_supported_extensions())}\n")
    
    # Define test files
    test_files = {
        'PDF': 'test_files/sample.pdf',
        'TXT': 'test_files/sample.txt',
        'CSV': 'test_files/sample.csv',
        'Excel': 'test_files/sample.xlsx',
    }
    
    # Test each file type
    for file_type, file_path in test_files.items():
        print(f"\n{'='*80}")
        print(f"Testing {file_type} Ingestor")
        print(f"{'='*80}")
        
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            print(f"   Please create this file to test {file_type} ingestion.")
            continue
        
        try:
            # Load file (in production, pass organization_id here)
            # Example: text = load_file(file_path, organization_id=123)
            text = load_file(file_path)
            
            # Display results
            print(f"✅ Successfully loaded: {file_path}")
            print(f"📊 Total characters: {len(text)}")
            print(f"\n📄 First 300 characters:\n")
            print("-" * 80)
            print(truncate_text(text, 300))
            print("-" * 80)
            
        except Exception as e:
            print(f"❌ Error loading {file_path}: {str(e)}")
    
    print(f"\n{'='*80}")
    print("Test Complete!")
    print("="*80)


def create_sample_files():
    """
    Helper function to create sample test files.
    Run this once to generate test data.
    """
    import pandas as pd
    
    # Create test_files directory
    os.makedirs('test_files', exist_ok=True)
    
    # Create sample TXT file
    with open('test_files/sample.txt', 'w') as f:
        f.write("""RheXa Knowledge Base Platform
        
This is a sample text document for testing the ingestion system.
RheXa is an AI-powered knowledge base platform that allows organizations
to upload documents and chat with their data.

Key Features:
- Multi-tenant architecture
- Support for PDF, CSV, Excel, and text files
- AI-powered chat interface
- Embeddable chatbot widget
- Subscription-based pricing ($49-$199/month)
""")
    
    # Create sample CSV file
    df_csv = pd.DataFrame({
        'Product': ['Basic Plan', 'Pro Plan', 'Enterprise Plan'],
        'Price': [49, 99, 199],
        'Features': ['5GB Storage', '50GB Storage', 'Unlimited Storage'],
        'Users': [5, 25, 'Unlimited']
    })
    df_csv.to_csv('test_files/sample.csv', index=False)
    
    # Create sample Excel file
    with pd.ExcelWriter('test_files/sample.xlsx', engine='openpyxl') as writer:
        # Sheet 1: Pricing
        df_csv.to_excel(writer, sheet_name='Pricing', index=False)
        
        # Sheet 2: Usage Stats
        df_stats = pd.DataFrame({
            'Month': ['January', 'February', 'March'],
            'Documents': [120, 145, 189],
            'Queries': [1500, 2100, 2800],
            'Active_Users': [45, 52, 68]
        })
        df_stats.to_excel(writer, sheet_name='Usage Stats', index=False)
    
    print("✅ Sample files created in 'test_files/' directory")
    print("   - sample.txt")
    print("   - sample.csv")
    print("   - sample.xlsx")
    print("\n⚠️  Note: You need to manually add a sample.pdf file for PDF testing")


if __name__ == "__main__":
    # Uncomment the line below to create sample files first
    # create_sample_files()
    
    # Run the ingestion tests
    test_ingestion()
