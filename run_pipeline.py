#!/usr/bin/env python3
"""
Simple wrapper script for running the OCR PII Pipeline.
"""
import subprocess
import sys
import os

def main():
    """Run the CLI with all arguments passed through."""
    script_path = os.path.join(os.path.dirname(__file__), 'ocr_pii_cli.py')
    cmd = [sys.executable, script_path] + sys.argv[1:]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())