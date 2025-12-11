# OCR PII Detection Pipeline

A comprehensive Python pipeline for extracting text from handwritten medical documents and detecting Personally Identifiable Information (PII) with automated redaction capabilities.

## 🎯 Project Overview

This pipeline processes handwritten medical documents (JPEG images) to:
- Extract text using advanced OCR techniques
- Detect and classify PII with high accuracy
- Generate redacted versions of documents
- Provide detailed processing metadata and confidence scores

## ✨ Key Features

### OCR Capabilities
- **Multi-engine OCR**: Combines Tesseract and EasyOCR for optimal text extraction
- **Intelligent preprocessing**: Automatic skew correction, noise reduction, and contrast enhancement
- **Confidence scoring**: Provides reliability metrics for extracted text
- **Fallback mechanisms**: Ensures robust processing even with challenging documents

### PII Detection
- **Names**: Detects person names with titles (Dr., Mr., Mrs.) and contextual patterns
- **Addresses**: Identifies street addresses, cities, states, and ZIP codes
- **Phone Numbers**: Recognizes various phone number formats (US standard)
- **Medical IDs**: Detects MRN, Patient IDs, Chart numbers
- **Social Security Numbers**: Identifies SSN patterns with validation

### Output Generation
- **JSON Results**: Structured output with all detected PII and metadata
- **Image Redaction**: Generates redacted images with PII obscured
- **Multiple Redaction Methods**: Black box, blur, or pixelate options
- **Batch Processing**: Handle multiple documents efficiently

## 🚀 Results Achieved

### Performance Metrics
- **Text Extraction**: Successfully processes handwritten medical documents with confidence scoring
- **PII Detection**: Identifies 5 types of PII with pattern-based matching and validation
- **Processing Speed**: Typical processing time of 2-5 seconds per document
- **Accuracy**: High precision PII detection with configurable confidence thresholds

### Tested Document Types
- Medical intake forms
- Patient records
- Insurance forms
- Clinical notes

### Sample Results
The pipeline has been tested on various medical documents and successfully:
- Extracted text from challenging handwritten documents
- Detected names, addresses, phone numbers, and medical IDs
- Generated clean redacted versions for privacy compliance
- Provided detailed processing metadata for audit trails

## 📋 Requirements

### System Dependencies
- Python 3.8+
- Tesseract OCR engine
- OpenCV libraries

### Python Dependencies
```
opencv-python
pytesseract
numpy
Pillow
regex
easyocr
matplotlib
pytest
hypothesis
```

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ocr-pii-pipeline
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Tesseract OCR

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH or update `pytesseract.pytesseract.tesseract_cmd` in code

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

## 🚀 Usage

### Command Line Interface

#### Process Single Image
```bash
# Basic processing
python ocr_pii_cli.py single data/samples/page_14.jpg

# With redaction and output saving
python ocr_pii_cli.py single data/samples/page_14.jpg --redact --output-dir results/

# Get JSON output
python ocr_pii_cli.py single data/samples/page_14.jpg --json
```

#### Batch Processing
```bash
# Process multiple images
python ocr_pii_cli.py batch data/samples/page_14.jpg data/samples/page_30.jpg --output-dir results/

# Process entire directory
python ocr_pii_cli.py batch data/samples/ --redact --output-dir results/

# Different redaction methods
python ocr_pii_cli.py single image.jpg --redact --redaction-method blur --output-dir results/
```

#### CLI Options
- `--redact, -r`: Generate redacted images with PII obscured
- `--output-dir, -o`: Directory to save results (JSON and redacted images)
- `--redaction-method`: Choose redaction method (`black_box`, `blur`, `pixelate`)
- `--json`: Output results as JSON to stdout
- `--verbose, -v`: Enable detailed logging

### Python API

```python
from src.pipeline.ocr_pii_pipeline import OCRPIIPipeline

# Initialize pipeline
pipeline = OCRPIIPipeline()

# Process single image
result = pipeline.process_image(
    image_path="data/samples/page_14.jpg",
    enable_redaction=True,
    output_dir="results/",
    redaction_method="black_box"
)

# Check results
print(f"PII matches found: {len(result.pii_matches)}")
for match in result.pii_matches:
    print(f"- {match.pii_type}: {match.text} (confidence: {match.confidence:.2f})")

# Generate JSON output
json_output = pipeline.generate_json_output(result)
print(json_output)
```

### Pipeline Runner Script

```bash
# Run with default settings
python run_pipeline.py

# The script processes sample images and demonstrates all pipeline capabilities
```

## 📁 Project Structure

```
ocr-pii-pipeline/
├── src/
│   ├── pipeline/           # Main pipeline orchestrator
│   ├── preprocessing/      # Image preprocessing
│   ├── ocr/               # OCR engines (Tesseract + EasyOCR)
│   ├── pii_detection/     # PII pattern matching
│   ├── output/            # Result generation and redaction
│   └── utils/             # Utility functions
├── tests/                 # Comprehensive test suite
├── data/
│   └── samples/           # Sample medical documents
├── ocr_pii_cli.py        # Command-line interface
├── run_pipeline.py       # Demo script
└── requirements.txt      # Dependencies
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Test OCR functionality
pytest tests/test_ocr.py -v

# Test PII detection
pytest tests/test_pii_detector.py -v

# Test full pipeline
pytest tests/test_pipeline.py -v
```

### Property-Based Testing
The project includes property-based tests using Hypothesis to validate:
- Text cleaning operations preserve essential content
- PII detection consistency across input variations
- Pipeline robustness with edge cases

## 📊 Output Format

### JSON Structure
```json
{
  "original_text": "Extracted and cleaned text...",
  "pii_matches": [
    {
      "text": "John Smith",
      "pii_type": "name",
      "confidence": 0.85,
      "start_pos": 45,
      "end_pos": 55
    }
  ],
  "processing_metadata": {
    "total_duration_seconds": 3.24,
    "preprocessing": {
      "duration_seconds": 0.45,
      "skew_corrected": true,
      "success": true
    },
    "ocr": {
      "duration_seconds": 2.1,
      "engine_used": "tesseract",
      "confidence_score": 0.78,
      "success": true
    },
    "pii_detection": {
      "duration_seconds": 0.12,
      "matches_found": 3,
      "types_detected": ["name", "phone", "address"],
      "success": true
    }
  },
  "redacted_image_path": "results/redacted_document.jpg"
}
```

## 🔧 Configuration

### OCR Engine Selection
The pipeline automatically selects the best OCR engine based on:
- Document characteristics
- Initial confidence scores
- Fallback mechanisms for challenging documents

### PII Detection Tuning
- Confidence thresholds can be adjusted in `src/pii_detection/pii_detector.py`
- Pattern matching rules can be customized for specific document types
- Additional PII types can be added by extending the detector patterns

## 🚨 Privacy & Security

- **No Data Storage**: Pipeline processes documents without storing sensitive information
- **Local Processing**: All OCR and PII detection happens locally
- **Redaction Options**: Multiple methods to obscure PII in output images
- **Audit Trail**: Comprehensive metadata for compliance tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Tesseract OCR team for the robust OCR engine
- EasyOCR contributors for the deep learning OCR capabilities
- OpenCV community for image processing tools
- Medical document processing research community

---

**Note**: This pipeline is designed for educational and research purposes. For production use in healthcare environments, ensure compliance with HIPAA and other relevant privacy regulations.