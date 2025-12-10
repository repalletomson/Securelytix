"""
Main OCR PII Pipeline orchestrator.
Coordinates all pipeline components for end-to-end processing.
"""
import os
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from src.models import PIIResult, ErrorResult
from src.preprocessing.image_preprocessor import ImagePreprocessor
from src.ocr.ocr_engine import OCREngine
from src.utils.text_cleaner import TextCleaner
from src.pii_detection.pii_detector import PIIDetector
from src.output.output_generator import OutputGenerator

logger = logging.getLogger(__name__)


class OCRPIIPipeline:
    """
    Main pipeline orchestrator that coordinates all components for end-to-end processing.
    """
    
    def __init__(self):
        """Initialize the pipeline with all components."""
        try:
            self.preprocessor = ImagePreprocessor()
            self.ocr_engine = OCREngine()
            self.text_cleaner = TextCleaner()
            self.pii_detector = PIIDetector()
            self.output_generator = OutputGenerator()
            
            logger.info("OCR PII Pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise
    
    def process_image(self, 
                     image_path: str, 
                     enable_redaction: bool = False,
                     output_dir: Optional[str] = None,
                     redaction_method: str = 'black_box') -> PIIResult:
        """
        Process a single image through the complete OCR PII pipeline.
        
        Args:
            image_path: Path to the input image file
            enable_redaction: Whether to generate a redacted image
            output_dir: Directory to save outputs (optional)
            redaction_method: Method for redaction ('black_box', 'blur', 'pixelate')
            
        Returns:
            PIIResult containing extracted text, detected PII, and metadata
            
        Raises:
            FileNotFoundError: If input image doesn't exist
            ValueError: If input format is invalid
            Exception: For other processing errors
        """
        start_time = time.time()
        processing_metadata = {
            'input_file': image_path,
            'pipeline_version': '1.0.0',
            'processing_stages': []
        }
        
        try:
            # Validate input
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            
            if not image_path.lower().endswith(('.jpg', '.jpeg')):
                raise ValueError(f"Invalid file format. Expected JPEG, got: {Path(image_path).suffix}")
            
            logger.info(f"Starting pipeline processing for: {image_path}")
            
            # Stage 1: Image Preprocessing
            stage_start = time.time()
            try:
                preprocessed_image, preprocessing_meta = self.preprocessor.preprocess(image_path)
                stage_time = time.time() - stage_start
                processing_metadata['preprocessing'] = {
                    'duration_seconds': stage_time,
                    'operations_applied': preprocessing_meta.get('preprocessing_steps', []),
                    'skew_corrected': preprocessing_meta.get('skew_corrected', False),
                    'original_shape': preprocessing_meta.get('original_shape'),
                    'success': True
                }
                processing_metadata['processing_stages'].append('preprocessing')
                logger.info(f"Preprocessing completed in {stage_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Preprocessing failed: {e}")
                return self._create_error_result('preprocessing', str(e), processing_metadata)
            
            # Stage 2: OCR Text Extraction
            stage_start = time.time()
            try:
                extracted_text, ocr_confidence, ocr_metadata = self.ocr_engine.extract_with_confidence(preprocessed_image)
                stage_time = time.time() - stage_start
                processing_metadata['ocr'] = {
                    'duration_seconds': stage_time,
                    'engine_used': ocr_metadata.get('selected_engine', 'unknown'),
                    'engines_tried': ocr_metadata.get('engines_tried', []),
                    'fallback_used': ocr_metadata.get('fallback_used', False),
                    'confidence_score': ocr_confidence,
                    'text_length': len(extracted_text),
                    'success': True
                }
                processing_metadata['processing_stages'].append('ocr')
                logger.info(f"OCR completed in {stage_time:.2f}s, confidence: {ocr_confidence:.2f}")
                
            except Exception as e:
                logger.error(f"OCR failed: {e}")
                return self._create_error_result('ocr', str(e), processing_metadata)
            
            # Stage 3: Text Cleaning
            stage_start = time.time()
            try:
                cleaned_text, cleaning_metadata = self.text_cleaner.clean_text(extracted_text)
                text_quality_metrics = self.text_cleaner.assess_text_quality(extracted_text, cleaned_text)
                text_quality = text_quality_metrics.get('overall_quality', 0.0)
                stage_time = time.time() - stage_start
                processing_metadata['text_cleaning'] = {
                    'duration_seconds': stage_time,
                    'quality_metrics': text_quality_metrics,
                    'quality_score': text_quality,
                    'original_length': len(extracted_text),
                    'cleaned_length': len(cleaned_text),
                    'success': True
                }
                processing_metadata['processing_stages'].append('text_cleaning')
                logger.info(f"Text cleaning completed in {stage_time:.2f}s, quality: {text_quality:.2f}")
                
            except Exception as e:
                logger.error(f"Text cleaning failed: {e}")
                return self._create_error_result('text_cleaning', str(e), processing_metadata)
            
            # Stage 4: PII Detection
            stage_start = time.time()
            try:
                pii_matches = self.pii_detector.detect_all_pii(cleaned_text)
                stage_time = time.time() - stage_start
                processing_metadata['pii_detection'] = {
                    'duration_seconds': stage_time,
                    'matches_found': len(pii_matches),
                    'types_detected': list(set(match.pii_type for match in pii_matches)),
                    'success': True
                }
                processing_metadata['processing_stages'].append('pii_detection')
                logger.info(f"PII detection completed in {stage_time:.2f}s, found {len(pii_matches)} matches")
                
            except Exception as e:
                logger.error(f"PII detection failed: {e}")
                return self._create_error_result('pii_detection', str(e), processing_metadata)
            
            # Stage 5: Output Generation (optional redaction)
            redacted_image_path = None
            if enable_redaction and pii_matches and output_dir:
                stage_start = time.time()
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    redacted_filename = f"redacted_{Path(image_path).stem}.jpg"
                    redacted_image_path = os.path.join(output_dir, redacted_filename)
                    
                    self.output_generator.generate_redacted_image(
                        original_image_path=image_path,
                        pii_matches=pii_matches,
                        output_path=redacted_image_path,
                        redaction_method=redaction_method
                    )
                    
                    stage_time = time.time() - stage_start
                    processing_metadata['redaction'] = {
                        'duration_seconds': stage_time,
                        'method': redaction_method,
                        'output_path': redacted_image_path,
                        'pii_redacted': len(pii_matches),
                        'success': True
                    }
                    processing_metadata['processing_stages'].append('redaction')
                    logger.info(f"Image redaction completed in {stage_time:.2f}s")
                    
                except Exception as e:
                    logger.warning(f"Image redaction failed: {e}")
                    processing_metadata['redaction'] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # Calculate total processing time
            total_time = time.time() - start_time
            processing_metadata['total_duration_seconds'] = total_time
            processing_metadata['success'] = True
            
            # Create result
            result = PIIResult(
                original_text=cleaned_text,
                pii_matches=pii_matches,
                processing_metadata=processing_metadata,
                redacted_image_path=redacted_image_path
            )
            
            logger.info(f"Pipeline processing completed successfully in {total_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return self._create_error_result('pipeline', str(e), processing_metadata)
    
    def process_batch(self, 
                     image_paths: list[str], 
                     enable_redaction: bool = False,
                     output_dir: Optional[str] = None,
                     redaction_method: str = 'black_box') -> Dict[str, PIIResult]:
        """
        Process multiple images through the pipeline.
        
        Args:
            image_paths: List of paths to input images
            enable_redaction: Whether to generate redacted images
            output_dir: Directory to save outputs (optional)
            redaction_method: Method for redaction
            
        Returns:
            Dictionary mapping image paths to PIIResult objects
        """
        results = {}
        
        logger.info(f"Starting batch processing of {len(image_paths)} images")
        
        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"Processing image {i}/{len(image_paths)}: {image_path}")
            
            try:
                result = self.process_image(
                    image_path=image_path,
                    enable_redaction=enable_redaction,
                    output_dir=output_dir,
                    redaction_method=redaction_method
                )
                results[image_path] = result
                
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                results[image_path] = self._create_error_result(
                    'batch_processing', 
                    str(e), 
                    {'input_file': image_path}
                )
        
        logger.info(f"Batch processing completed. {len(results)} results generated")
        return results
    
    def generate_json_output(self, result: PIIResult) -> str:
        """
        Generate JSON output from pipeline result.
        
        Args:
            result: PIIResult from pipeline processing
            
        Returns:
            JSON string containing structured results
        """
        return self.output_generator.generate_json_output(
            original_text=result.original_text,
            pii_matches=result.pii_matches,
            processing_metadata=result.processing_metadata,
            redacted_image_path=result.redacted_image_path
        )
    
    def save_results(self, 
                    result: PIIResult, 
                    output_dir: str, 
                    base_filename: str) -> Dict[str, str]:
        """
        Save pipeline results to files.
        
        Args:
            result: PIIResult from pipeline processing
            output_dir: Directory to save outputs
            base_filename: Base filename (without extension)
            
        Returns:
            Dictionary mapping output types to file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_files = {}
        
        try:
            # Save JSON output
            json_output = self.generate_json_output(result)
            json_path = os.path.join(output_dir, f"{base_filename}_results.json")
            self.output_generator.save_output_to_file(json_output, json_path)
            saved_files['json'] = json_path
            
            # Include redacted image if available
            if result.redacted_image_path:
                saved_files['redacted_image'] = result.redacted_image_path
            
            logger.info(f"Results saved to {output_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    def _create_error_result(self, 
                           stage: str, 
                           error_message: str, 
                           metadata: Dict[str, Any]) -> PIIResult:
        """Create a PIIResult with error information."""
        error_metadata = metadata.copy()
        error_metadata.update({
            'success': False,
            'error_stage': stage,
            'error_message': error_message
        })
        
        return PIIResult(
            original_text="",
            pii_matches=[],
            processing_metadata=error_metadata,
            redacted_image_path=None
        )