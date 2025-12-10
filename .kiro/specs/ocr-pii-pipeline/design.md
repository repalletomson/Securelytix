# OCR PII Pipeline Design Document

## Overview

The OCR PII Pipeline is a Python-based system that processes handwritten document images to extract text and identify Personally Identifiable Information (PII). The pipeline consists of four main stages: image preprocessing, OCR text extraction, text cleaning, and PII detection. The system is designed to handle various handwriting styles, image orientations, and quality levels while maintaining high accuracy in both text extraction and PII identification.

## Architecture

The system follows a modular pipeline architecture with clear separation of concerns:

```
Input JPEG → Image Preprocessing → OCR Engine → Text Cleaning → PII Detection → Output (JSON + Optional Redacted Image)
```

### Core Components:
- **ImagePreprocessor**: Handles image enhancement, orientation correction, and noise reduction
- **OCREngine**: Manages text extraction using multiple OCR backends (Tesseract, EasyOCR)
- **TextCleaner**: Post-processes extracted text to improve accuracy and consistency
- **PIIDetector**: Identifies and classifies sensitive information using pattern matching and NLP
- **OutputGenerator**: Formats results and optionally generates redacted images
- **PipelineOrchestrator**: Coordinates the entire processing workflow

## Components and Interfaces

### ImagePreprocessor
```python
class ImagePreprocessor:
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray
    def reduce_noise(self, image: np.ndarray) -> np.ndarray
    def correct_orientation(self, image: np.ndarray) -> np.ndarray
    def preprocess(self, image_path: str) -> np.ndarray
```

### OCREngine
```python
class OCREngine:
    def extract_text_tesseract(self, image: np.ndarray) -> str
    def extract_text_easyocr(self, image: np.ndarray) -> str
    def extract_with_confidence(self, image: np.ndarray) -> Tuple[str, float]
```

### PIIDetector
```python
class PIIDetector:
    def detect_names(self, text: str) -> List[PIIMatch]
    def detect_addresses(self, text: str) -> List[PIIMatch]
    def detect_phone_numbers(self, text: str) -> List[PIIMatch]
    def detect_medical_ids(self, text: str) -> List[PIIMatch]
    def detect_all_pii(self, text: str) -> List[PIIMatch]
```

### PipelineOrchestrator
```python
class OCRPIIPipeline:
    def process_image(self, image_path: str, enable_redaction: bool = False) -> PIIResult
```

## Data Models

### PIIMatch
```python
@dataclass
class PIIMatch:
    text: str
    pii_type: str  # 'name', 'address', 'phone', 'medical_id', 'ssn'
    confidence: float
    start_pos: int
    end_pos: int
```

### PIIResult
```python
@dataclass
class PIIResult:
    original_text: str
    pii_matches: List[PIIMatch]
    processing_metadata: Dict[str, Any]
    redacted_image_path: Optional[str] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all testable properties from the prework analysis, several redundancies were identified:
- Properties 1.3 and 3.3 both test orientation correction - combined into Property 3
- Properties 3.1, 3.2, and 3.4 all test preprocessing improvements - combined into Property 4  
- Properties 2.1-2.5 all test PII detection for different types - can be tested together in Property 5
- Properties 4.1, 4.2, 4.3, 4.4 all test output structure - combined into Property 6

### Core Properties

**Property 1: JPEG Input Acceptance**
*For any* valid JPEG image file, the OCR_Pipeline should accept and begin processing without throwing format-related errors
**Validates: Requirements 1.1**

**Property 2: Text Extraction Capability**  
*For any* image containing visible text, the OCR_Pipeline should extract non-empty text content
**Validates: Requirements 1.2, 1.4**

**Property 3: Orientation Correction**
*For any* image with text, applying random rotation and then processing through the pipeline should still extract recognizable text content
**Validates: Requirements 1.3, 3.3**

**Property 4: Image Enhancement Preservation**
*For any* image, preprocessing operations should not decrease OCR text extraction accuracy compared to the original image
**Validates: Requirements 3.1, 3.2, 3.4**

**Property 5: PII Detection Completeness**
*For any* text containing known PII patterns (names, addresses, phone numbers, medical IDs, SSNs), the OCR_Pipeline should detect and correctly classify each PII type
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

**Property 6: Output Structure Consistency**
*For any* successful pipeline execution, the output should conform to the PIIResult schema with original text, PII matches including type/confidence/position, and processing metadata
**Validates: Requirements 1.5, 4.1, 4.2, 4.3, 4.4**

**Property 7: Redaction Generation**
*For any* image processed with redaction enabled and containing detected PII, a redacted image file should be generated
**Validates: Requirements 4.5**

**Property 8: Error Handling Robustness**
*For any* invalid input file or processing failure, the OCR_Pipeline should return structured error information without crashing
**Validates: Requirements 5.1, 5.2, 5.4**

**Property 9: JSON Output Validity**
*For any* successful pipeline execution, the output should be valid JSON that can be parsed and conforms to the expected schema
**Validates: Requirements 5.5**

## Error Handling

The system implements comprehensive error handling at each stage:

### Input Validation Errors
- Invalid file formats (non-JPEG)
- Corrupted or unreadable image files
- Missing or inaccessible file paths

### Processing Errors
- OCR engine failures or timeouts
- Image preprocessing failures
- Memory or resource constraints

### Output Errors
- File system errors when generating redacted images
- JSON serialization failures

### Error Response Format
```python
@dataclass
class ErrorResult:
    error_type: str
    error_message: str
    stage: str  # 'input', 'preprocessing', 'ocr', 'pii_detection', 'output'
    diagnostic_info: Dict[str, Any]
```

## Testing Strategy

The testing approach combines unit testing for individual components with property-based testing for system-wide correctness guarantees.

### Unit Testing Approach
- Component isolation testing for ImagePreprocessor, OCREngine, PIIDetector
- Mock-based testing for external dependencies (file system, OCR libraries)
- Edge case testing for boundary conditions and error scenarios
- Integration testing for component interactions

### Property-Based Testing Approach
- **Framework**: Hypothesis for Python will be used for property-based testing
- **Test Configuration**: Each property-based test will run a minimum of 100 iterations
- **Test Tagging**: Each property-based test will include a comment with the format: `**Feature: ocr-pii-pipeline, Property {number}: {property_text}**`
- **Generator Strategy**: Smart generators will create realistic test data including:
  - Valid JPEG images with various text content
  - Text samples with embedded PII patterns
  - Images with different orientations, noise levels, and quality
  - Invalid inputs for error condition testing

### Test Coverage Requirements
- Unit tests verify specific examples and component behavior
- Property tests verify universal correctness properties across all inputs
- Both approaches are complementary and required for comprehensive validation
- Each correctness property must be implemented by a single property-based test
- Property-based tests must reference their corresponding design document property

### Testing Dependencies
- pytest for unit testing framework
- Hypothesis for property-based testing
- PIL/Pillow for image generation and manipulation in tests
- Mock libraries for external dependency isolation