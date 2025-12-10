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
            r'\b(?:Mr|Mrs|Ms|Dr|Doctor|Patient)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\bName:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\bPatient:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b(?=\s*(?:DOB|Age|Born))',  # Name before DOB/Age
        ]
        
        # Address patterns
        self.address_patterns = [
            r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b',
            r'\bAddress:\s*(.+?)(?:\n|$)',
            r'\b\d+\s+[A-Z][a-z]+\s+[A-Z][a-z]+,\s*[A-Z][a-z]+\s+\d{5}\b',  # Street address with ZIP
        ]
        
        # Phone number patterns
        self.phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            r'\bPhone:\s*([0-9\-\.\s\(\)]+)\b',
            r'\bTel:\s*([0-9\-\.\s\(\)]+)\b',
            r'\bMobile:\s*([0-9\-\.\s\(\)]+)\b',
        ]
        
        # Medical ID patterns
        self.medical_id_patterns = [
            r'\b(?:MRN|Medical Record|Patient ID|ID):\s*([A-Z0-9\-]+)\b',
            r'\b[A-Z]{2,3}\d{6,10}\b',  # Common medical ID format
            r'\bNHS\s*(?:Number|No):\s*(\d{3}\s*\d{3}\s*\d{4})\b',  # NHS number
            r'\b\d{8,12}\b(?=\s*(?:medical|patient|record))',  # Numbers near medical terms
        ]
        
        # SSN patterns
        self.ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # Standard SSN format
            r'\bSSN:\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
            r'\bSocial Security:\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
        ]
        
        # Date patterns (for DOB detection)
        self.date_patterns = [
            r'\b(?:DOB|Date of Birth|Born):\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
            r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b(?=\s*(?:DOB|Birth))',
        ]
        
        # Common first names for name validation
        self.common_first_names = {
            'james', 'mary', 'john', 'patricia', 'robert', 'jennifer', 'michael', 'linda',
            'william', 'elizabeth', 'david', 'barbara', 'richard', 'susan', 'joseph', 'jessica',
            'thomas', 'sarah', 'christopher', 'karen', 'charles', 'nancy', 'daniel', 'lisa',
            'matthew', 'betty', 'anthony', 'helen', 'mark', 'sandra', 'donald', 'donna',
            'steven', 'carol', 'paul', 'ruth', 'andrew', 'sharon', 'joshua', 'michelle',
            'kenneth', 'laura', 'kevin', 'sarah', 'brian', 'kimberly', 'george', 'deborah',
            'edward', 'dorothy', 'ronald', 'lisa', 'timothy', 'nancy', 'jason', 'karen'
        }
    
    def _calculate_confidence(self, match_text: str, pattern_type: str, context: str = "") -> float:
        """Calculate confidence score for a PII match."""
        base_confidence = 0.5
        
        # Pattern-specific confidence adjustments
        if pattern_type == 'name':
            # Higher confidence if it's a common name
            first_name = match_text.split()[0].lower()
            if first_name in self.common_first_names:
                base_confidence += 0.3
            
            # Higher confidence if preceded by title or label
            if re.search(r'(?:Mr|Mrs|Ms|Dr|Patient|Name):\s*$', context):
                base_confidence += 0.2
                
        elif pattern_type == 'phone':
            # Higher confidence for properly formatted numbers
            if re.match(r'\(\d{3}\)\s*\d{3}-\d{4}', match_text):
                base_confidence += 0.3
            elif re.match(r'\d{3}-\d{3}-\d{4}', match_text):
                base_confidence += 0.2
                
        elif pattern_type == 'ssn':
            # SSN patterns are usually high confidence
            base_confidence += 0.4
            
        elif pattern_type == 'medical_id':
            # Medical IDs with labels are high confidence
            if 'MRN' in context or 'Medical Record' in context:
                base_confidence += 0.3
                
        elif pattern_type == 'address':
            # Addresses with street indicators are higher confidence
            if re.search(r'(?:Street|Avenue|Road|Drive)', match_text, re.IGNORECASE):
                base_confidence += 0.2
        
        return min(1.0, base_confidence)
    
    def detect_names(self, text: str) -> List[PIIMatch]:
        """Detect person names in text."""
        matches = []
        
        for pattern in self.name_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1) if match.groups() else match.group(0)
                
                # Skip if it looks like a medication or medical term
                if re.search(r'(?:mg|ml|tablet|capsule|dose|daily|twice)', name, re.IGNORECASE):
                    continue
                
                # Get context for confidence calculation
                start_context = text[max(0, match.start()-20):match.start()]
                
                confidence = self._calculate_confidence(name, 'name', start_context)
                
                pii_match = PIIMatch(
                    text=name,
                    pii_type='name',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def detect_addresses(self, text: str) -> List[PIIMatch]:
        """Detect addresses in text."""
        matches = []
        
        for pattern in self.address_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                address = match.group(1) if match.groups() else match.group(0)
                
                confidence = self._calculate_confidence(address, 'address')
                
                pii_match = PIIMatch(
                    text=address.strip(),
                    pii_type='address',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def detect_phone_numbers(self, text: str) -> List[PIIMatch]:
        """Detect phone numbers in text."""
        matches = []
        
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                phone = match.group(1) if match.groups() else match.group(0)
                
                # Skip if it's clearly not a phone number (too short, etc.)
                digits_only = re.sub(r'[^\d]', '', phone)
                if len(digits_only) < 10 or len(digits_only) > 11:
                    continue
                
                confidence = self._calculate_confidence(phone, 'phone')
                
                pii_match = PIIMatch(
                    text=phone,
                    pii_type='phone',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def detect_medical_ids(self, text: str) -> List[PIIMatch]:
        """Detect medical record numbers and IDs."""
        matches = []
        
        for pattern in self.medical_id_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                medical_id = match.group(1) if match.groups() else match.group(0)
                
                # Get context for confidence calculation
                start_context = text[max(0, match.start()-20):match.start()]
                end_context = text[match.end():match.end()+20]
                context = start_context + end_context
                
                confidence = self._calculate_confidence(medical_id, 'medical_id', context)
                
                pii_match = PIIMatch(
                    text=medical_id,
                    pii_type='medical_id',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def detect_ssns(self, text: str) -> List[PIIMatch]:
        """Detect Social Security Numbers."""
        matches = []
        
        for pattern in self.ssn_patterns:
            for match in re.finditer(pattern, text):
                ssn = match.group(1) if match.groups() else match.group(0)
                
                # Validate SSN format
                digits_only = re.sub(r'[^\d]', '', ssn)
                if len(digits_only) != 9:
                    continue
                
                # Skip obviously invalid SSNs
                if digits_only.startswith('000') or digits_only[3:5] == '00' or digits_only[5:] == '0000':
                    continue
                
                confidence = self._calculate_confidence(ssn, 'ssn')
                
                pii_match = PIIMatch(
                    text=ssn,
                    pii_type='ssn',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def detect_dates_of_birth(self, text: str) -> List[PIIMatch]:
        """Detect dates of birth (treated as PII)."""
        matches = []
        
        for pattern in self.date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dob = match.group(1) if match.groups() else match.group(0)
                
                confidence = 0.8  # DOB patterns are usually high confidence
                
                pii_match = PIIMatch(
                    text=dob,
                    pii_type='dob',
                    confidence=confidence,
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                matches.append(pii_match)
        
        return matches
    
    def _remove_overlapping_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping PII matches, keeping the highest confidence ones."""
        if not matches:
            return matches
        
        # Sort by start position
        sorted_matches = sorted(matches, key=lambda x: x.start_pos)
        
        filtered_matches = []
        for match in sorted_matches:
            # Check if this match overlaps with any existing match
            overlaps = False
            for existing in filtered_matches:
                if (match.start_pos < existing.end_pos and match.end_pos > existing.start_pos):
                    # There's an overlap - keep the higher confidence match
                    if match.confidence > existing.confidence:
                        filtered_matches.remove(existing)
                        filtered_matches.append(match)
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_matches.append(match)
        
        return filtered_matches
    
    def detect_all_pii(self, text: str) -> List[PIIMatch]:
        """
        Detect all types of PII in text.
        
        Returns:
            List of PIIMatch objects sorted by position
        """
        if not text:
            return []
        
        all_matches = []
        
        # Detect each type of PII
        all_matches.extend(self.detect_names(text))
        all_matches.extend(self.detect_addresses(text))
        all_matches.extend(self.detect_phone_numbers(text))
        all_matches.extend(self.detect_medical_ids(text))
        all_matches.extend(self.detect_ssns(text))
        all_matches.extend(self.detect_dates_of_birth(text))
        
        # Remove overlapping matches
        filtered_matches = self._remove_overlapping_matches(all_matches)
        
        # Sort by position
        filtered_matches.sort(key=lambda x: x.start_pos)
        
        logger.info(f"Detected {len(filtered_matches)} PII elements in text")
        
        return filtered_matches
    
    def get_pii_summary(self, matches: List[PIIMatch]) -> Dict[str, int]:
        """Get a summary of detected PII types."""
        summary = {}
        for match in matches:
            pii_type = match.pii_type
            summary[pii_type] = summary.get(pii_type, 0) + 1
        
        return summary