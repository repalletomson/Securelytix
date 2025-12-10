#!/usr/bin/env python3
"""
Command-line interface for OCR PII Pipeline.
Processes single images or batches with configurable options.
"""
import argparse
import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pipeline.ocr_pii_pipeline import OCRPIIPipeline


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_image_path(path: str) -> str:
    """Validate that the image path exists and is a JPEG."""
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Image file not found: {path}")
    
    if not path.lower().endswith(('.jpg', '.jpeg')):
        raise argparse.ArgumentTypeError(f"Invalid file format. Expected JPEG, got: {Path(path).suffix}")
    
    return path


def validate_output_dir(path: str) -> str:
    """Validate and create output directory if needed."""
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Cannot create output directory {path}: {e}")


def process_single_image(args):
    """Process a single image."""
    print(f"Processing image: {args.image}")
    
    try:
        pipeline = OCRPIIPipeline()
        
        result = pipeline.process_image(
            image_path=args.image,
            enable_redaction=args.redact,
            output_dir=args.output_dir,
            redaction_method=args.redaction_method
        )
        
        # Check if processing was successful
        if not result.processing_metadata.get('success', False):
            print(f"❌ Processing failed: {result.processing_metadata.get('error_message', 'Unknown error')}")
            return False
        
        # Print results summary
        print("✅ Processing completed successfully!")
        
        total_time = result.processing_metadata.get('total_duration_seconds', 0)
        print(f"   Total time: {total_time:.2f}s")
        
        pii_count = len(result.pii_matches)
        print(f"   PII matches found: {pii_count}")
        
        if pii_count > 0:
            pii_types = set(match.pii_type for match in result.pii_matches)
            print(f"   PII types: {', '.join(sorted(pii_types))}")
        
        # Save results if output directory specified
        if args.output_dir:
            base_filename = Path(args.image).stem
            saved_files = pipeline.save_results(result, args.output_dir, base_filename)
            print(f"   Results saved to: {args.output_dir}")
            
            for file_type, file_path in saved_files.items():
                print(f"     {file_type}: {file_path}")
        
        # Print JSON to stdout if requested
        if args.json_output:
            json_result = pipeline.generate_json_output(result)
            if args.output_dir:
                print("\n" + "="*50)
                print("JSON Output:")
                print("="*50)
            print(json_result)
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def process_batch(args):
    """Process multiple images."""
    image_paths = []
    
    # Collect all image paths
    for path in args.images:
        if os.path.isfile(path):
            if path.lower().endswith(('.jpg', '.jpeg')):
                image_paths.append(path)
            else:
                print(f"⚠️  Skipping non-JPEG file: {path}")
        elif os.path.isdir(path):
            # Find all JPEG files in directory
            for ext in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
                image_paths.extend(Path(path).glob(ext))
            image_paths = [str(p) for p in image_paths]
        else:
            print(f"⚠️  Path not found: {path}")
    
    if not image_paths:
        print("❌ No valid JPEG images found to process")
        return False
    
    print(f"Processing {len(image_paths)} images...")
    
    try:
        pipeline = OCRPIIPipeline()
        
        results = pipeline.process_batch(
            image_paths=image_paths,
            enable_redaction=args.redact,
            output_dir=args.output_dir,
            redaction_method=args.redaction_method
        )
        
        # Process results
        successful = 0
        failed = 0
        total_pii = 0
        
        for image_path, result in results.items():
            if result.processing_metadata.get('success', False):
                successful += 1
                total_pii += len(result.pii_matches)
                
                # Save individual results if output directory specified
                if args.output_dir:
                    base_filename = Path(image_path).stem
                    pipeline.save_results(result, args.output_dir, base_filename)
                
                print(f"✅ {Path(image_path).name}: {len(result.pii_matches)} PII matches")
            else:
                failed += 1
                error_msg = result.processing_metadata.get('error_message', 'Unknown error')
                print(f"❌ {Path(image_path).name}: {error_msg}")
        
        # Print summary
        print(f"\n📊 Batch Processing Summary:")
        print(f"   Total images: {len(image_paths)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Total PII matches: {total_pii}")
        
        if args.output_dir:
            print(f"   Results saved to: {args.output_dir}")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Error during batch processing: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="OCR PII Pipeline - Extract text and detect PII from handwritten documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single image
  python ocr_pii_cli.py single image.jpg
  
  # Process with redaction and save results
  python ocr_pii_cli.py single image.jpg --redact --output-dir results/
  
  # Process multiple images
  python ocr_pii_cli.py batch image1.jpg image2.jpg --output-dir results/
  
  # Process all images in a directory
  python ocr_pii_cli.py batch /path/to/images/ --redact
  
  # Get JSON output
  python ocr_pii_cli.py single image.jpg --json
        """
    )
    
    # Global options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--output-dir', '-o', type=validate_output_dir,
                       help='Directory to save results (JSON and redacted images)')
    parser.add_argument('--redact', '-r', action='store_true',
                       help='Generate redacted images with PII obscured')
    parser.add_argument('--redaction-method', choices=['black_box', 'blur', 'pixelate'],
                       default='black_box', help='Method for redacting PII (default: black_box)')
    parser.add_argument('--json', dest='json_output', action='store_true',
                       help='Output results as JSON to stdout')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single image processing
    single_parser = subparsers.add_parser('single', help='Process a single image')
    single_parser.add_argument('image', type=validate_image_path,
                              help='Path to JPEG image file')
    
    # Batch processing
    batch_parser = subparsers.add_parser('batch', help='Process multiple images')
    batch_parser.add_argument('images', nargs='+',
                             help='Paths to JPEG images or directories containing images')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        if args.command == 'single':
            success = process_single_image(args)
        elif args.command == 'batch':
            success = process_batch(args)
        else:
            parser.print_help()
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())