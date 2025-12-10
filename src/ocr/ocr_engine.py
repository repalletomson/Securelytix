"""
OCR engine module with multiple backend support.
Supports Tesseract and EasyOCR with fallback mechanisms.
"""
import cv2
import numpy as np
import pytesseract
import easyocr
from typing import Tuple, List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine with multiple backend support and confidence scoring."""
    
    def __init__(self, preferred_engine: str = 'tesseract'):
        """
        Initialize OCR engine.
        
        Args:
            preferred_engine: 'tesseract' or 'easyocr'
        """
        self.preferred_engine = preferred_engine
        self.easyocr_reader = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize OCR engines."""
        try:
            # Test Tesseract availability
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR initialized successfully")
        except Exception as e:
            logger.warning(f"Tesseract initialization failed: {e}")
        
        try:
            # Initialize EasyOCR (lazy loading)
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.warning(f"EasyOCR initialization failed: {e}")
            self.easyocr_reader = None
    
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Additional preprocessing specifically for OCR."""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply adaptive thresholding for better text recognition
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Apply morphological operations to clean up text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
        except Exception as e:
            logger.warning(f"OCR preprocessing failed: {e}")
            return image
    
    def extract_text_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Extract text using Tesseract OCR.
        
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            # Preprocess image for OCR
            processed_image = self._preprocess_for_ocr(image)
            
            # Configure Tesseract for handwritten text
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?@#$%^&*()_+-=[]{}|;:\'\"<>/\\ '
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(processed_image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Filter out low-confidence words and combine text
            text_parts = []
            confidences = []
            
            for i in range(len(data['text'])):
                word = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if word and conf > 30:  # Filter low-confidence words
                    text_parts.append(word)
                    confidences.append(conf)
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            logger.info(f"Tesseract extracted {len(text_parts)} words with avg confidence {avg_confidence:.2f}")
            
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return "", 0.0
    
    def extract_text_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Extract text using EasyOCR.
        
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            if self.easyocr_reader is None:
                logger.error("EasyOCR not available")
                return "", 0.0
            
            # EasyOCR works better with original color image
            results = self.easyocr_reader.readtext(image)
            
            text_parts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Filter low-confidence detections
                    text_parts.append(text)
                    confidences.append(confidence)
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            logger.info(f"EasyOCR extracted {len(text_parts)} text blocks with avg confidence {avg_confidence:.2f}")
            
            return extracted_text, avg_confidence
            
        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return "", 0.0
    
    def extract_with_confidence(self, image: np.ndarray) -> Tuple[str, float, Dict[str, any]]:
        """
        Extract text using preferred engine with fallback.
        
        Returns:
            Tuple of (extracted_text, confidence_score, metadata)
        """
        metadata = {
            'engines_tried': [],
            'primary_engine': self.preferred_engine,
            'fallback_used': False
        }
        
        # Try preferred engine first
        if self.preferred_engine == 'tesseract':
            text, confidence = self.extract_text_tesseract(image)
            metadata['engines_tried'].append('tesseract')
            
            # Fallback to EasyOCR if Tesseract fails or gives low confidence
            if (not text or confidence < 0.3) and self.easyocr_reader is not None:
                logger.info("Falling back to EasyOCR")
                fallback_text, fallback_conf = self.extract_text_easyocr(image)
                metadata['engines_tried'].append('easyocr')
                metadata['fallback_used'] = True
                
                # Use fallback result if it's better
                if fallback_conf > confidence:
                    text, confidence = fallback_text, fallback_conf
                    metadata['selected_engine'] = 'easyocr'
                else:
                    metadata['selected_engine'] = 'tesseract'
            else:
                metadata['selected_engine'] = 'tesseract'
        
        else:  # preferred_engine == 'easyocr'
            text, confidence = self.extract_text_easyocr(image)
            metadata['engines_tried'].append('easyocr')
            
            # Fallback to Tesseract if EasyOCR fails or gives low confidence
            if not text or confidence < 0.3:
                logger.info("Falling back to Tesseract")
                fallback_text, fallback_conf = self.extract_text_tesseract(image)
                metadata['engines_tried'].append('tesseract')
                metadata['fallback_used'] = True
                
                # Use fallback result if it's better
                if fallback_conf > confidence:
                    text, confidence = fallback_text, fallback_conf
                    metadata['selected_engine'] = 'tesseract'
                else:
                    metadata['selected_engine'] = 'easyocr'
            else:
                metadata['selected_engine'] = 'easyocr'
        
        # Clean up extracted text
        cleaned_text = self._clean_extracted_text(text)
        
        metadata['original_length'] = len(text)
        metadata['cleaned_length'] = len(cleaned_text)
        
        return cleaned_text, confidence, metadata
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common OCR errors
        replacements = {
            '|': 'I',  # Common misread
            '0': 'O',  # In names/words context
            '5': 'S',  # In words context
            '1': 'l',  # In words context
        }
        
        # Apply replacements cautiously (only in word contexts)
        words = cleaned.split()
        corrected_words = []
        
        for word in words:
            # Only apply letter corrections to words that look like names/text
            if re.match(r'^[A-Za-z0-9|]+$', word) and len(word) > 1:
                corrected_word = word
                for old, new in replacements.items():
                    # Only replace if it makes the word more letter-like
                    if old in corrected_word and not corrected_word.isdigit():
                        corrected_word = corrected_word.replace(old, new)
                corrected_words.append(corrected_word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def extract_text(self, image: np.ndarray) -> str:
        """
        Simple text extraction interface.
        
        Returns:
            Extracted text string
        """
        text, _, _ = self.extract_with_confidence(image)
        return text