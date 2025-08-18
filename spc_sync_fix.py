#!/usr/bin/env python3
"""
SPC Data Sync Fix - Corrects mismatch by re-ingesting missing reports
"""

import sys
sys.path.append('/home/runner/workspace')

from datetime import date, datetime
from models import db, SPCReport
from spc_verification import SPCVerificationService
from spc_ingest import SPCIngestService
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_missing_reports():
    """Fix SPC mismatches by re-ingesting missing data"""
    
    # Create database session
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        # Initialize services
        verifier = SPCVerificationService(session)
        ingest_service = SPCIngestService(session)
        
        # Check recent dates for mismatches
        mismatched_dates = []
        for day in range(12, 19):  # Aug 12-18
            test_date = date(2025, 8, day)
            result = verifier.verify_single_date(test_date)
            
            if result['match_status'] == 'MISMATCH':
                mismatched_dates.append({
                    'date': test_date,
                    'hailydb': result['hailydb_count'],
                    'spc_live': result['spc_live_count'],
                    'difference': result['difference']
                })
                logger.info(f"MISMATCH: {test_date} - HailyDB: {result['hailydb_count']}, SPC: {result['spc_live_count']}")
        
        if not mismatched_dates:
            logger.info("No mismatches found - all data is synchronized!")
            return
        
        # Fix mismatches by clearing and re-ingesting
        logger.info(f"Found {len(mismatched_dates)} mismatched dates. Re-ingesting...")
        
        for mismatch in mismatched_dates:
            target_date = mismatch['date']
            logger.info(f"Re-syncing {target_date}...")
            
            # Delete existing records for this date
            deleted_count = session.query(SPCReport).filter(
                SPCReport.report_date == target_date
            ).delete()
            session.commit()
            logger.info(f"Deleted {deleted_count} existing records for {target_date}")
            
            # Re-ingest fresh data
            try:
                ingest_service.ingest_date(target_date)
                logger.info(f"Successfully re-ingested {target_date}")
            except Exception as e:
                logger.error(f"Failed to re-ingest {target_date}: {e}")
                session.rollback()
                continue
        
        # Verify fixes
        logger.info("\n=== POST-SYNC VERIFICATION ===")
        for day in range(12, 19):
            test_date = date(2025, 8, day)
            result = verifier.verify_single_date(test_date)
            status = "✓ FIXED" if result['match_status'] == 'MATCH' else "✗ STILL BROKEN"
            logger.info(f"{test_date}: {status} - HailyDB: {result['hailydb_count']}, SPC: {result['spc_live_count']}")
    
    finally:
        session.close()

if __name__ == "__main__":
    sync_missing_reports()