#!/usr/bin/env python3
"""
Florida Pilot Backfill Script
Runs 2-month historical backfill for September-October 2024
Integrates with SchedulerService for ingestion success tracking
"""
import os
import sys
import logging
from datetime import datetime

# Add app to path for imports
sys.path.append('.')

from app import app, db
from iem_backfill_service import IemBackfillService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Execute Florida pilot backfill for Sep-Oct 2024"""
    logger.info("=== FLORIDA PILOT BACKFILL STARTING ===")
    logger.info("Target: September-October 2024 historical NWS alerts")
    logger.info("Source: Iowa Environmental Mesonet (IEM)")
    
    with app.app_context():
        # Initialize backfill service with database session
        backfill_service = IemBackfillService(db)
        
        # Define pilot months
        pilot_months = [
            (2024, 9),   # September 2024
            (2024, 10)   # October 2024
        ]
        
        total_stats = {
            'months_processed': 0,
            'total_records': 0,
            'total_inserted': 0,
            'total_updated': 0,
            'months_failed': 0,
            'errors': []
        }
        
        # Process each month
        for year, month in pilot_months:
            try:
                logger.info(f"Processing {year}-{month:02d}...")
                
                # Process month (this will log to SchedulerService automatically)
                month_stats = backfill_service.process_florida_month(year, month)
                
                # Aggregate statistics
                total_stats['months_processed'] += 1
                total_stats['total_records'] += month_stats['records_processed']
                total_stats['total_inserted'] += month_stats['records_inserted']
                total_stats['total_updated'] += month_stats['records_updated']
                
                if month_stats['errors']:
                    total_stats['errors'].extend(month_stats['errors'])
                
                logger.info(f"Month {year}-{month:02d} completed: {month_stats['records_inserted']} new alerts")
                
            except Exception as e:
                error_msg = f"Failed to process {year}-{month:02d}: {e}"
                logger.error(error_msg)
                total_stats['months_failed'] += 1
                total_stats['errors'].append(error_msg)
                continue
        
        # Final summary
        logger.info("=== FLORIDA PILOT BACKFILL COMPLETED ===")
        logger.info(f"Months processed: {total_stats['months_processed']}/2")
        logger.info(f"Total records processed: {total_stats['total_records']}")
        logger.info(f"New alerts inserted: {total_stats['total_inserted']}")
        logger.info(f"Alerts updated: {total_stats['total_updated']}")
        
        if total_stats['months_failed'] > 0:
            logger.warning(f"Failed months: {total_stats['months_failed']}")
        
        if total_stats['errors']:
            logger.error(f"Errors encountered: {len(total_stats['errors'])}")
            for error in total_stats['errors'][:5]:  # Show first 5 errors
                logger.error(f"  - {error}")
        
        logger.info("Check /ingestion-logs for detailed success tracking!")
        
        return total_stats

if __name__ == '__main__':
    results = main()
    sys.exit(0 if results['months_failed'] == 0 else 1)