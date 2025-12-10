"""
Text cleaning and post-processing utilities for OCR output.
Handles normalization, error correction, and quality assessment.
"""
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """Handles post-OCR text cleaning and normalization."""
    
    def __init__(self):
        # Common OCR error patterns and corrections
        self.ocr_corrections = {
            # Character substitutions
            r'\b0(?=[A-Za-z])': 'O',  # 0 -> O at word start
            r'(?<=[A-Za-z])0\b': 'o',  # 0 -> o at word end
            r'\b1(?=[A-Za-z])': 'I',  # 1 -> I at word start
            r'(?<=[A-Za-z])1(?=[A-Za-z])': 'l',  # 1 -> l in middle of words
            r'\b5(?=[A-Za-z])': 'S',  # 5 -> S at word start
            r'(?<=[A-Za-z])5(?=[A-Za-z])': 's',  # 5 -> s in middle of words
            r'\|': 'I',  # | -> I
            r'(?<=[a-z])rn(?=[a-z])': 'm',  # Common OCR error: rn -> m (in middle of words)
            r'vv': 'w',  # Common OCR error: vv -> w
            
            # Medical/pharmaceutical specific corrections
            r'\bmg\b': 'mg',  # Ensure mg is lowercase
            r'\bMG\b': 'mg',  # MG -> mg
            r'\bml\b': 'ml',  # Ensure ml is lowercase
            r'\bML\b': 'ml',  # ML -> ml
            r'\btab\b': 'tab',  # Ensure tab is lowercase
            r'\bTAB\b': 'tab',  # TAB -> tab
        }
        
        # Medical terms dictionary for spell checking
        self.medical_terms = {
            'paracetamol', 'ibuprofen', 'aspirin', 'amoxicillin', 'metformin',
            'atorvastatin', 'omeprazole', 'simvastatin', 'ramipril', 'amlodipine',
            'levothyroxine', 'lansoprazole', 'bendroflumethiazide', 'salbutamol',
            'prednisolone', 'warfarin', 'furosemide', 'bisoprolol', 'clopidogrel',
            'dose', 'dosage', 'tablet', 'capsule', 'syrup', 'injection', 'cream',
            'ointment', 'drops', 'spray', 'inhaler', 'patch', 'suppository',
            'morning', 'evening', 'night', 'daily', 'twice', 'thrice', 'weekly',
            'monthly', 'before', 'after', 'meals', 'food', 'empty', 'stomach',
            'patient', 'doctor', 'physician', 'nurse', 'clinic', 'hospital',
            'prescription', 'medication', 'treatment', 'therapy', 'diagnosis'
        }
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized
    
    def fix_common_ocr_errors(self, text: str) -> str:
        """Fix common OCR character recognition errors."""
        if not text:
            return ""
        
        corrected = text
        
        # Apply OCR corrections
        for pattern, replacement in self.ocr_corrections.items():
            corrected = re.sub(pattern, replacement, corrected)
        
        return corrected
    
    def clean_medical_text(self, text: str) -> str:
        """Apply medical document specific cleaning."""
        if not text:
            return ""
        
        cleaned = text
        
        # Fix common medical abbreviation patterns
        medical_patterns = {
            r'\b(\d+)\s*mg\b': r'\1mg',  # Ensure no space between number and mg
            r'\b(\d+)\s*ml\b': r'\1ml',  # Ensure no space between number and ml
            r'\b(\d+)\s*tab\b': r'\1 tab',  # Ensure space between number and tab
            r'\b(\d+)\s*x\s*(\d+)\b': r'\1x\2',  # Fix dosage format like "2 x 3" -> "2x3"
            r'\b(\d+)/(\d+)\b': r'\1/\2',  # Ensure no spaces in fractions
            
            # Fix time patterns
            r'\b(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)\b': r'\1:\2\3',  # Fix time format with am/pm
            r'\b(\d{1,2})\s*:\s*(\d{2})\b': r'\1:\2',  # Fix time format without am/pm
            r'\b(\d{1,2})\s+(am|pm)\b': r'\1\2',  # Fix am/pm format
        }
        
        for pattern, replacement in medical_patterns.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def remove_artifacts(self, text: str) -> str:
        """Remove OCR artifacts and noise."""
        if not text:
            return ""
        
        cleaned = text
        
        # Remove isolated single characters that are likely artifacts
        # But preserve meaningful single characters like dosages
        artifact_patterns = [
            r'\s[^\w\s]\s',  # Remove isolated punctuation with spaces around
            r'\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\b',  # Remove spaced single letters
            r'_{2,}',  # Remove multiple underscores
            r'-{3,}',  # Remove multiple dashes
            r'\.{3,}',  # Remove multiple dots (but keep ellipsis)
        ]
        
        for pattern in artifact_patterns:
            cleaned = re.sub(pattern, ' ', cleaned)
        
        # Clean up resulting multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def extract_structured_info(self, text: str) -> Dict[str, List[str]]:
        """Extract structured information from medical text."""
        if not text:
            return {}
        
        structured_info = {
            'medications': [],
            'dosages': [],
            'times': [],
            'dates': [],
            'quantities': []
        }
        
        # Extract medications (words that might be drug names)
        medication_pattern = r'\b[A-Z][a-z]{3,}(?:in|ol|am|ide|ine|ate)\b'
        medications = re.findall(medication_pattern, text)
        structured_info['medications'] = list(set(medications))
        
        # Extract dosages
        dosage_patterns = [
            r'\b\d+\s*mg\b',
            r'\b\d+\s*ml\b',
            r'\b\d+\s*tab\b',
            r'\b\d+\s*capsule\b',
            r'\b\d+\s*tablet\b'
        ]
        
        for pattern in dosage_patterns:
            dosages = re.findall(pattern, text, re.IGNORECASE)
            structured_info['dosages'].extend(dosages)
        
        # Extract times
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:am|pm)?\b',
            r'\b(?:morning|evening|night|noon)\b',
            r'\b(?:daily|twice|thrice)\s*(?:daily|a day)?\b'
        ]
        
        for pattern in time_patterns:
            times = re.findall(pattern, text, re.IGNORECASE)
            structured_info['times'].extend(times)
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}\b'
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, text, re.IGNORECASE)
            structured_info['dates'].extend(dates)
        
        # Extract quantities
        quantity_patterns = [
            r'\b\d+\s*x\s*\d+\b',
            r'\b\d+\s*pack\b',
            r'\b\d+\s*bottle\b',
            r'\b\d+\s*box\b'
        ]
        
        for pattern in quantity_patterns:
            quantities = re.findall(pattern, text, re.IGNORECASE)
            structured_info['quantities'].extend(quantities)
        
        # Remove duplicates and clean up
        for key in structured_info:
            structured_info[key] = list(set(structured_info[key]))
        
        return structured_info
    
    def assess_text_quality(self, original_text: str, cleaned_text: str) -> Dict[str, float]:
        """Assess the quality of text cleaning."""
        if not original_text and not cleaned_text:
            return {'quality_score': 0.0}
        
        if not original_text:
            return {'quality_score': 0.0}
        
        if not cleaned_text:
            return {'quality_score': 0.0}
        
        # Calculate various quality metrics
        original_words = len(original_text.split())
        cleaned_words = len(cleaned_text.split())
        
        # Word retention ratio
        word_retention = cleaned_words / original_words if original_words > 0 else 0
        
        # Character cleaning ratio
        char_reduction = 1 - (len(cleaned_text) / len(original_text)) if len(original_text) > 0 else 0
        
        # Medical term recognition
        medical_terms_found = sum(1 for term in self.medical_terms 
                                if term.lower() in cleaned_text.lower())
        medical_score = min(1.0, medical_terms_found / 10.0)  # Normalize to 0-1
        
        # Structure score (presence of numbers, dates, etc.)
        structure_patterns = [
            r'\d+mg', r'\d+ml', r'\d+tab', r'\d{1,2}:\d{2}', r'\d{1,2}/\d{1,2}'
        ]
        structure_matches = sum(1 for pattern in structure_patterns 
                              if re.search(pattern, cleaned_text, re.IGNORECASE))
        structure_score = min(1.0, structure_matches / len(structure_patterns))
        
        # Overall quality score
        quality_score = (word_retention * 0.3 + 
                        (1 - char_reduction) * 0.2 + 
                        medical_score * 0.3 + 
                        structure_score * 0.2)
        
        return {
            'quality_score': quality_score,
            'word_retention': word_retention,
            'char_reduction': char_reduction,
            'medical_score': medical_score,
            'structure_score': structure_score,
            'medical_terms_found': medical_terms_found
        }
    
    def clean_text(self, text: str) -> Tuple[str, Dict[str, any]]:
        """
        Complete text cleaning pipeline.
        
        Returns:
            Tuple of (cleaned_text, cleaning_metadata)
        """
        if not text:
            return "", {'steps': [], 'quality': {'quality_score': 0.0}}
        
        original_text = text
        cleaning_steps = []
        
        # Step 1: Normalize whitespace
        text = self.normalize_whitespace(text)
        cleaning_steps.append('whitespace_normalization')
        
        # Step 2: Fix common OCR errors
        text = self.fix_common_ocr_errors(text)
        cleaning_steps.append('ocr_error_correction')
        
        # Step 3: Apply medical-specific cleaning
        text = self.clean_medical_text(text)
        cleaning_steps.append('medical_text_cleaning')
        
        # Step 4: Remove artifacts
        text = self.remove_artifacts(text)
        cleaning_steps.append('artifact_removal')
        
        # Step 5: Final normalization
        text = self.normalize_whitespace(text)
        
        # Assess quality
        quality_metrics = self.assess_text_quality(original_text, text)
        
        # Extract structured information
        structured_info = self.extract_structured_info(text)
        
        metadata = {
            'steps': cleaning_steps,
            'quality': quality_metrics,
            'structured_info': structured_info,
            'original_length': len(original_text),
            'cleaned_length': len(text)
        }
        
        logger.info(f"Text cleaning completed. Quality score: {quality_metrics['quality_score']:.3f}")
        
        return text, metadata