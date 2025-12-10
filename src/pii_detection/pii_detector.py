"""
PII (Personally Identifiable Information) detection module.
Detects names, addresses, phone numbers, medical IDs, and SSNs in text.
"""
import re
from typing import List, Dict, Tuple
import logging
from src.models import PIIMatch

logger = logging.getLogger(__name__)


class PIIDetector:
    """Detects and classifies PII in text using pattern matching and heuristics."""
    
    def __init__(self):
        # Common name patterns and indicators
        self.name_patterns = [
            r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Doctor)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            r'\bPatient:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            r'\bName:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b(?=\s*(?:DOB|Age|Born))',  # Name before DOB/Age
            r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b',  # General two-word capitalized names
        ]
        
        # Address patterns
        self.address_patterns = [
            r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b',
            r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)(?:\s*,?\s*[A-Z][a-z]+\s*,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?',
            r'Address:\s*(.+?)(?:\n|$)',
            r'\b[A-Z][a-z]+\s*,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b',  # City, State ZIP
        ]
        
        # Phone number patterns
        self.phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            r'\bPhone:\s*([0-9\-\.\(\)\s]+)\b',
            r'\bTel:\s*([0-9\-\.\(\)\s]+)\b',
            r'\bCell:\s*([0-9\-\.\(\)\s]+)\b',
        ]
        
        # Medical ID patterns
        self.medical_id_patterns = [
            r'\b(?:MRN|Medical Record|Patient ID|Chart):\s*([A-Z0-9\-]+)\b',
            r'\b(?:MR|MRN)#?\s*([A-Z0-9\-]{6,12})\b',
            r'\bPatient\s+ID:\s*([A-Z0-9\-]+)\b',
            r'\bChart\s+#:\s*([A-Z0-9\-]+)\b',
        ]
        
        # SSN patterns
        self.ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{3}\s\d{2}\s\d{4}\b',
            r'\bSSN:\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
            r'\bSocial Security:\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
        ]
    
    def detect_names(self, text: str) -> List[PIIMatch]:
        """Detect person names in text."""
        matches = []
        
        for pattern in self.name_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract the actual name from the capture group or full match
                if match.groups() and match.group(1):
                    name_text = match.group(1).strip()
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    name_text = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                
                # Skip if name is too short or invalid
                if len(name_text) < 2:
                    continue
                
                # Calculate confidence based on pattern type and context
                confidence = self._calculate_name_confidence(name_text, pattern, text, start_pos)
                
                matches.append(PIIMatch(
                    text=name_text,
                    pii_type='name',
                    confidence=confidence,
                    start_pos=start_pos,
                    end_pos=end_pos
                ))
        
        return self._deduplicate_matches(matches)
    
    def detect_addresses(self, text: str) -> List[PIIMatch]:
        """Detect addresses in text."""
        matches = []
        
        for pattern in self.address_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.groups():
                    address_text = match.group(1).strip()
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    address_text = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                
                confidence = self._calculate_address_confidence(address_text, pattern)
                
                matches.append(PIIMatch(
                    text=address_text,
                    pii_type='address',
                    confidence=confidence,
                    start_pos=start_pos,
                    end_pos=end_pos
                ))
        
        return self._deduplicate_matches(matches)
    
    def detect_phone_numbers(self, text: str) -> List[PIIMatch]:
        """Detect phone numbers in text."""
        matches = []
        
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.groups():
                    # For patterns with capture groups, use the first group
                    phone_text = match.group(1).strip() if len(match.groups()) == 1 else match.group(0).strip()
                    start_pos = match.start(1) if len(match.groups()) == 1 else match.start()
                    end_pos = match.end(1) if len(match.groups()) == 1 else match.end()
                else:
                    phone_text = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                
                # Validate phone number format
                if self._is_valid_phone_number(phone_text):
                    confidence = self._calculate_phone_confidence(phone_text, pattern)
                    
                    matches.append(PIIMatch(
                        text=phone_text,
                        pii_type='phone',
                        confidence=confidence,
                        start_pos=start_pos,
                        end_pos=end_pos
                    ))
        
        return self._deduplicate_matches(matches)
    
    def detect_medical_ids(self, text: str) -> List[PIIMatch]:
        """Detect medical record numbers and patient IDs."""
        matches = []
        
        for pattern in self.medical_id_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.groups():
                    med_id_text = match.group(1).strip()
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    med_id_text = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                
                confidence = self._calculate_medical_id_confidence(med_id_text, pattern)
                
                matches.append(PIIMatch(
                    text=med_id_text,
                    pii_type='medical_id',
                    confidence=confidence,
                    start_pos=start_pos,
                    end_pos=end_pos
                ))
        
        return self._deduplicate_matches(matches)
    
    def detect_ssns(self, text: str) -> List[PIIMatch]:
        """Detect Social Security Numbers."""
        matches = []
        
        for pattern in self.ssn_patterns:
            for match in re.finditer(pattern, text):
                if match.groups():
                    ssn_text = match.group(1).strip()
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    ssn_text = match.group(0).strip()
                    start_pos = match.start()
                    end_pos = match.end()
                
                # Validate SSN format
                if self._is_valid_ssn(ssn_text):
                    confidence = self._calculate_ssn_confidence(ssn_text, pattern)
                    
                    matches.append(PIIMatch(
                        text=ssn_text,
                        pii_type='ssn',
                        confidence=confidence,
                        start_pos=start_pos,
                        end_pos=end_pos
                    ))
        
        return self._deduplicate_matches(matches)
    
    def detect_all_pii(self, text: str) -> List[PIIMatch]:
        """Detect all types of PII in the given text."""
        all_matches = []
        
        try:
            all_matches.extend(self.detect_names(text))
            all_matches.extend(self.detect_addresses(text))
            all_matches.extend(self.detect_phone_numbers(text))
            all_matches.extend(self.detect_medical_ids(text))
            all_matches.extend(self.detect_ssns(text))
            
            # Sort by position in text
            all_matches.sort(key=lambda x: x.start_pos)
            
            logger.info(f"Detected {len(all_matches)} PII matches in text")
            
        except Exception as e:
            logger.error(f"Error during PII detection: {e}")
            raise
        
        return all_matches
    
    def _calculate_name_confidence(self, name_text: str, pattern: str, full_text: str, position: int) -> float:
        """Calculate confidence score for name detection."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for names with titles or labels
        if any(indicator in pattern for indicator in ['Mr|Mrs|Ms|Dr', 'Name:', 'Patient:']):
            confidence += 0.3
        
        # Higher confidence for names near medical context
        context_window = full_text[max(0, position-50):position+50]
        medical_keywords = ['patient', 'doctor', 'medical', 'chart', 'record', 'dob', 'age']
        if any(keyword in context_window.lower() for keyword in medical_keywords):
            confidence += 0.2
        
        # Adjust for name length and format
        if len(name_text.split()) >= 2:  # First and last name
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_address_confidence(self, address_text: str, pattern: str) -> float:
        """Calculate confidence score for address detection."""
        confidence = 0.6  # Base confidence
        
        # Higher confidence for complete addresses with street numbers
        if re.search(r'\d+', address_text):
            confidence += 0.2
        
        # Higher confidence for addresses with state/ZIP
        if re.search(r'[A-Z]{2}\s+\d{5}', address_text):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_phone_confidence(self, phone_text: str, pattern: str) -> float:
        """Calculate confidence score for phone number detection."""
        confidence = 0.7  # Base confidence
        
        # Higher confidence for labeled phone numbers
        if 'Phone:' in pattern or 'Tel:' in pattern:
            confidence += 0.2
        
        # Higher confidence for properly formatted numbers
        if re.match(r'\(\d{3}\)\s?\d{3}-\d{4}', phone_text):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_medical_id_confidence(self, med_id_text: str, pattern: str) -> float:
        """Calculate confidence score for medical ID detection."""
        confidence = 0.8  # Base confidence (medical IDs are usually well-labeled)
        
        # Higher confidence for explicit labels
        if any(label in pattern for label in ['MRN:', 'Medical Record', 'Patient ID']):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_ssn_confidence(self, ssn_text: str, pattern: str) -> float:
        """Calculate confidence score for SSN detection."""
        confidence = 0.9  # Base confidence (SSNs have distinctive format)
        
        # Higher confidence for labeled SSNs
        if 'SSN:' in pattern or 'Social Security' in pattern:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _is_valid_phone_number(self, phone_text: str) -> bool:
        """Validate phone number format."""
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', phone_text)
        
        # Valid US phone numbers have 10 or 11 digits (with country code)
        return len(digits_only) in [10, 11]
    
    def _is_valid_ssn(self, ssn_text: str) -> bool:
        """Validate SSN format."""
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', ssn_text)
        
        # Valid SSNs have exactly 9 digits and don't start with 000, 666, or 9xx
        if len(digits_only) != 9:
            return False
        
        area_number = digits_only[:3]
        if area_number in ['000', '666'] or area_number.startswith('9'):
            return False
        
        return True
    
    def _deduplicate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove duplicate matches based on position overlap."""
        if not matches:
            return matches
        
        # Sort by start position
        matches.sort(key=lambda x: x.start_pos)
        
        deduplicated = []
        for match in matches:
            # Check if this match overlaps with any existing match
            overlaps = False
            for existing in deduplicated:
                if (match.start_pos < existing.end_pos and 
                    match.end_pos > existing.start_pos):
                    # Keep the match with higher confidence
                    if match.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(match)
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(match)
        
        return deduplicated