#!/usr/bin/env python
"""Smoke test to run get_record_for_gg on all GG files in the inputs directory"""

import os
import sys
import glob
import logging
from pathlib import Path
from src.ongoing_convo_with_bronn_2025_06_10.utils import get_record_for_gg, Record

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Find all GG PDF files in the inputs directory
input_dir = Path("inputs")
gg_files = sorted([f.name for f in input_dir.glob("gg*.pdf")])

logger.info(f"Found {len(gg_files)} GG files to process")
logger.info("-" * 80)

# Track successes and failures
successful = []
failed = []

# Process each file
for i, filename in enumerate(gg_files, 1):
    logger.info(f"[{i}/{len(gg_files)}] Processing: {filename}")
    
    try:
        record = get_record_for_gg(filename)
        successful.append((filename, record))
        
        # Log basic info about the record
        logger.info(f"✓ Success!")
        logger.info(f"  - GG Number: {record.gg_num}")
        logger.info(f"  - Gen Number: {record.gen_n_num}")
        logger.info(f"  - Date: {record.monthday_num} {record.month_name} {record.year}")
        logger.info(f"  - Type: {record.type_major.value} - {record.type_minor}")
        text_preview = record.text[:80] + "..." if len(record.text) > 80 else record.text
        logger.info(f"  - Text: {text_preview}")
        
    except Exception as e:
        failed.append((filename, str(e)))
        logger.exception(f"✗ Failed: {type(e).__name__}: {str(e)}")
        raise

# Log summary
logger.info("=" * 80)
logger.info("SUMMARY:")
logger.info(f"  Total files: {len(gg_files)}")
logger.info(f"  Successful: {len(successful)} ({len(successful)/len(gg_files)*100:.1f}%)")
logger.info(f"  Failed: {len(failed)} ({len(failed)/len(gg_files)*100:.1f}%)")

if failed:
    logger.warning(f"Failed files ({len(failed)}):")
    for filename, error in failed:
        logger.warning(f"  - {filename}: {error}")
        
logger.info("=" * 80)
