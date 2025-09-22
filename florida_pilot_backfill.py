#!/usr/bin/env python3
"""
Florida Pilot Backfill Script
Tests IEM historical weather alert ingestion for 2 months of Florida data

Target: September-October 2024, Florida (FL)
Purpose: Validate backfill approach before full-scale deployment
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'florida_pilot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Execute Florida 2-month pilot backfill
    """
    logger.info("="*60)
    logger.info("FLORIDA PILOT BACKFILL - Starting")
    logger.info("Target: September-October 2024, Florida")
    logger.info("="*60)
    
    try:
        # Initialize database connection
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
        
        logger.info(f"Connecting to database: {database_url[:50]}...")
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Import and initialize IEM backfill service
        from iem_backfill_service import IemBackfillService
        service = IemBackfillService(session)
        
        logger.info("IEM Backfill Service initialized successfully")
        
        # Pre-flight checks
        logger.info("Performing pre-flight checks...")
        if not pre_flight_checks(session):
            logger.error("Pre-flight checks failed")
            return False
        
        # Process target months
        target_months = [
            (2024, 9),   # September 2024
            (2024, 10)   # October 2024
        ]
        
        total_stats = {
            'months_processed': 0,
            'total_records_processed': 0,
            'total_records_inserted': 0,
            'total_records_updated': 0,
            'errors': []
        }
        
        for year, month in target_months:
            logger.info(f"\n{'='*50}")
            logger.info(f"PROCESSING: {year}-{month:02d} (Florida)")
            logger.info(f"{'='*50}")
            
            try:
                # Process the month
                stats = service.process_florida_month(year, month)
                
                # Update totals
                total_stats['months_processed'] += 1
                total_stats['total_records_processed'] += stats['records_processed']
                total_stats['total_records_inserted'] += stats['records_inserted']
                total_stats['total_records_updated'] += stats['records_updated']
                total_stats['errors'].extend(stats['errors'])
                
                # Log month results
                logger.info(f"✅ {year}-{month:02d} COMPLETED")
                logger.info(f"   Records processed: {stats['records_processed']}")
                logger.info(f"   Records inserted: {stats['records_inserted']}")
                logger.info(f"   Records updated: {stats['records_updated']}")
                if stats['errors']:
                    logger.warning(f"   Errors: {len(stats['errors'])}")
                    for error in stats['errors'][:3]:  # Show first 3 errors
                        logger.warning(f"     - {error}")
                
            except Exception as e:
                error_msg = f"Failed to process {year}-{month:02d}: {e}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
                continue
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("FLORIDA PILOT BACKFILL - COMPLETED")
        logger.info("="*60)
        logger.info(f"Months processed: {total_stats['months_processed']}/2")
        logger.info(f"Total records processed: {total_stats['total_records_processed']}")
        logger.info(f"Total records inserted: {total_stats['total_records_inserted']}")
        logger.info(f"Total records updated: {total_stats['total_records_updated']}")
        
        if total_stats['errors']:
            logger.warning(f"Total errors: {len(total_stats['errors'])}")
            logger.info("First few errors:")
            for error in total_stats['errors'][:5]:
                logger.warning(f"  - {error}")
        else:
            logger.info("✅ No errors encountered!")
        
        # Post-flight validation
        logger.info("\nPerforming post-flight validation...")
        validation_results = post_flight_validation(session, total_stats)
        
        if validation_results['success']:
            logger.info("✅ Florida pilot backfill completed successfully!")
            logger.info("System ready for larger-scale backfill operations.")
        else:
            logger.warning("⚠️ Pilot completed with issues - review before scaling")
        
        session.close()
        return validation_results['success']
        
    except Exception as e:
        logger.error(f"Critical error in pilot backfill: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def pre_flight_checks(session) -> bool:
    """
    Perform pre-flight checks before starting backfill
    """
    try:
        logger.info("1. Checking database connectivity...")
        result = session.execute("SELECT 1").scalar()
        if result != 1:
            logger.error("Database connectivity test failed")
            return False
        logger.info("   ✅ Database connected")
        
        logger.info("2. Checking PostGIS extension...")
        result = session.execute("SELECT PostGIS_Version()").scalar()
        logger.info(f"   ✅ PostGIS version: {result}")
        
        logger.info("3. Checking alerts table schema...")
        result = session.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'alerts' AND column_name IN ('geom', 'vtec_key', 'data_source')
        """).scalar()
        if result != 3:
            logger.error(f"Missing required columns in alerts table (found {result}/3)")
            return False
        logger.info("   ✅ Required columns present")
        
        logger.info("4. Checking backfill_progress table...")
        result = session.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'backfill_progress'
        """).scalar()
        if result != 1:
            logger.error("backfill_progress table not found")
            return False
        logger.info("   ✅ Progress tracking table ready")
        
        logger.info("5. Checking for existing IEM data...")
        result = session.execute("""
            SELECT COUNT(*) FROM alerts WHERE data_source = 'iem_watchwarn'
        """).scalar()
        logger.info(f"   ℹ️ Found {result} existing IEM records")
        
        logger.info("6. Checking current alerts count...")
        result = session.execute("SELECT COUNT(*) FROM alerts").scalar()
        logger.info(f"   ℹ️ Total alerts in database: {result}")
        
        logger.info("✅ All pre-flight checks passed")
        return True
        
    except Exception as e:
        logger.error(f"Pre-flight check failed: {e}")
        return False

def post_flight_validation(session, stats: dict) -> dict:
    """
    Validate the backfill results
    """
    validation = {
        'success': True,
        'issues': []
    }
    
    try:
        logger.info("1. Checking inserted records...")
        iem_count = session.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE data_source = 'iem_watchwarn' 
            AND vtec_key IS NOT NULL
        """).scalar()
        
        if iem_count != stats['total_records_inserted']:
            issue = f"Record count mismatch: expected {stats['total_records_inserted']}, found {iem_count}"
            logger.warning(f"   ⚠️ {issue}")
            validation['issues'].append(issue)
        else:
            logger.info(f"   ✅ Record count verified: {iem_count}")
        
        logger.info("2. Checking PostGIS geometries...")
        geom_count = session.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE data_source = 'iem_watchwarn' AND geom IS NOT NULL
        """).scalar()
        
        if geom_count != stats['total_records_inserted']:
            issue = f"Geometry count mismatch: expected {stats['total_records_inserted']}, found {geom_count}"
            logger.warning(f"   ⚠️ {issue}")
            validation['issues'].append(issue)
        else:
            logger.info(f"   ✅ All records have PostGIS geometries: {geom_count}")
        
        logger.info("3. Testing sample spatial query...")
        result = session.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE data_source = 'iem_watchwarn' 
            AND ST_IsValid(geom) = true
            LIMIT 10
        """).scalar()
        logger.info(f"   ✅ Sample spatial query successful: {result} valid geometries")
        
        logger.info("4. Checking VTEC key uniqueness...")
        duplicate_count = session.execute("""
            SELECT COUNT(*) FROM (
                SELECT vtec_key FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND vtec_key IS NOT NULL
                GROUP BY vtec_key HAVING COUNT(*) > 1
            ) duplicates
        """).scalar()
        
        if duplicate_count > 0:
            issue = f"Found {duplicate_count} duplicate VTEC keys"
            logger.warning(f"   ⚠️ {issue}")
            validation['issues'].append(issue)
        else:
            logger.info("   ✅ All VTEC keys are unique")
        
        logger.info("5. Checking progress tracking...")
        completed_steps = session.execute("""
            SELECT COUNT(*) FROM backfill_progress 
            WHERE state = 'FL' AND step = 'completed' AND completed_at IS NOT NULL
        """).scalar()
        logger.info(f"   ℹ️ Completed processing steps: {completed_steps}")
        
        # Final assessment
        if len(validation['issues']) == 0:
            logger.info("✅ All validation checks passed!")
        else:
            logger.warning(f"⚠️ Validation completed with {len(validation['issues'])} issues")
            validation['success'] = len(validation['issues']) <= 2  # Allow minor issues
        
        return validation
        
    except Exception as e:
        logger.error(f"Post-flight validation failed: {e}")
        validation['success'] = False
        validation['issues'].append(f"Validation error: {e}")
        return validation

if __name__ == "__main__":
    logger.info("Florida Pilot Backfill Script Starting...")
    
    # Check if running in correct environment
    if not os.environ.get('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable required")
        sys.exit(1)
    
    success = main()
    
    if success:
        logger.info("🎉 Florida pilot backfill completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Florida pilot backfill failed")
        sys.exit(1)