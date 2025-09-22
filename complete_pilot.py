#!/usr/bin/env python3
"""
Complete the Florida 2-month pilot: September + October 2024
"""
import sys
import logging

sys.path.append('.')

from real_florida_backfill import RealIemBackfill
from app import app, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Complete September + October 2024 Florida pilot"""
    logger.info("=== COMPLETING FLORIDA 2-MONTH PILOT ===")
    
    with app.app_context():
        service = RealIemBackfill(db)
        
        total_inserted = 0
        total_processed = 0
        
        # Process October 2024 (September already done)
        logger.info("Processing October 2024...")
        oct_stats = service.process_month(2024, 10)
        
        total_processed += oct_stats['records_processed']
        total_inserted += oct_stats['records_inserted']
        
        logger.info("=== COMPLETE PILOT RESULTS ===")
        logger.info(f"October records processed: {oct_stats['records_processed']}")
        logger.info(f"October new alerts inserted: {oct_stats['records_inserted']}")
        logger.info(f"Total 2-month pilot: {total_processed} processed, {total_inserted} new 2024 alerts")
        
        return True

if __name__ == '__main__':
    main()