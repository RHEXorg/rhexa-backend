# RheXa Ingestion System - Quick Reference

## 📁 File Structure

```
app/
├── ingestion/
│   ├── __init__.py          # Module exports
│   ├── base.py              # BaseIngestor abstract class
│   ├── utils.py             # Text cleaning utilities
│   ├── pdf_ingestor.py      # PDF document handler
│   ├── txt_ingestor.py      # Plain text handler
│   ├── csv_ingestor.py      # CSV data handler
│   ├── excel_ingestor.py    # Excel workbook handler
│   └── loader.py            # Universal file loader
└── db/
    └── session.py           # Database session (already exists)

test_ingestion.py            # Test script
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install PyMuPDF pandas openpyxl
```

### 2. Basic Usage
```python
from app.ingestion import load_file

# Load any supported file
text = load_file("path/to/document.pdf")
print(text[:300])  # Preview first 300 chars

# With multi-tenant context (for production)
text = load_file("path/to/document.pdf", organization_id=123)
```

### 3. Run Tests
```bash
# First, create sample files
python test_ingestion.py  # (uncomment create_sample_files() first)

# Then run tests
python test_ingestion.py
```

## 📚 Supported File Types

| Extension | Ingestor | Library Used |
|-----------|----------|--------------|
| `.pdf` | PDFIngestor | PyMuPDF (fitz) |
| `.txt` | TXTIngestor | Built-in |
| `.csv` | CSVIngestor | pandas |
| `.xlsx`, `.xls` | ExcelIngestor | pandas + openpyxl |

## 🔌 Adding New Ingestors

1. Create new ingestor class inheriting from `BaseIngestor`
2. Implement the `load(source: str) -> str` method
3. Add to `INGESTOR_MAP` in `loader.py`

Example:
```python
# app/ingestion/json_ingestor.py
from .base import BaseIngestor
from .utils import clean_text
import json

class JSONIngestor(BaseIngestor):
    def load(self, source: str) -> str:
        with open(source, 'r') as f:
            data = json.load(f)
        text = json.dumps(data, indent=2)
        return clean_text(text)
```

Then update `loader.py`:
```python
from .json_ingestor import JSONIngestor

INGESTOR_MAP = {
    # ... existing mappings
    '.json': JSONIngestor,
}
```

## 🏢 Multi-Tenant Integration

The ingestion system is designed for multi-tenant use. When saving documents:

```python
from app.ingestion import load_file
from app.models import Document
from app.db.session import SessionLocal

# Load file with organization context
text = load_file(file_path, organization_id=org_id)

# Save to database (example)
db = SessionLocal()
document = Document(
    filename=filename,
    organization_id=org_id,
    data_source_id=source_id,
    # content will be embedded and stored separately
)
db.add(document)
db.commit()
```

## 📦 Dependencies

```txt
PyMuPDF==1.23.8      # PDF processing
pandas==2.2.0        # CSV/Excel processing
openpyxl==3.1.2      # Excel file support
```

## 🎯 Next Steps (Phase 1.7+)

1. **Vector Embeddings**: Convert extracted text to embeddings
2. **Vector Database**: Store embeddings (Pinecone, Weaviate, or Chroma)
3. **API Endpoints**: Create upload endpoints in FastAPI
4. **File Storage**: Implement file upload handling
5. **Background Jobs**: Process large files asynchronously
6. **Web Scraping**: Add website ingestor
7. **Database Connector**: Add SQL database ingestor

## 💡 Usage Examples

### Example 1: Process PDF
```python
from app.ingestion import PDFIngestor

ingestor = PDFIngestor()
text = ingestor.load("reports/annual_report.pdf")
print(f"Extracted {len(text)} characters")
```

### Example 2: Process CSV
```python
from app.ingestion import CSVIngestor

ingestor = CSVIngestor()
text = ingestor.load("data/customers.csv")
# Text will be formatted with headers and row data
```

### Example 3: Universal Loader
```python
from app.ingestion import load_file, get_supported_extensions

# Check supported types
print(get_supported_extensions())
# ['.pdf', '.txt', '.csv', '.xlsx', '.xls']

# Auto-detect and load
files = ["doc.pdf", "data.csv", "report.xlsx"]
for file in files:
    text = load_file(file)
    print(f"{file}: {len(text)} chars")
```

## 🔧 Troubleshooting

### PDF not loading
- Ensure PyMuPDF is installed: `pip install PyMuPDF`
- Check if PDF is encrypted or corrupted

### CSV/Excel encoding issues
- CSV ingestor tries UTF-8 by default
- Excel files must be .xlsx or .xls format

### Memory issues with large files
- Consider chunking large documents
- Process files in background tasks
- Implement pagination for CSV/Excel

## 📝 Notes

- All text is automatically cleaned (extra spaces, newlines removed)
- CSV/Excel data is converted to readable text format for AI processing
- Multi-page PDFs are fully supported
- Excel files process all sheets
- Organization ID is optional but recommended for production use
