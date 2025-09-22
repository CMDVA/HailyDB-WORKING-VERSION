#!/usr/bin/env python3
"""
Test real IEM historical data download and ingestion
Verify we can actually retrieve and process thousands of 2024 alerts
"""
import sys
import logging

sys.path.append('.')

from app import app, db
from iem_backfill_service import IemBackfillService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test actual IEM download for September 2024 Florida"""
    logger.info("=== TESTING REAL IEM HISTORICAL DATA DOWNLOAD ===")
    
    with app.app_context():
        service = IemBackfillService(db)
        
        # Test URL generation
        url = service.get_florida_url("2024-09-01", "2024-09-30")
        logger.info(f"Generated URL: {url}")
        
        # Test actual download
        logger.info("Downloading historical shapefile...")
        zip_data = service.download_shapefile(url)
        
        if not zip_data:
            logger.error("Failed to download data")
            return False
        
        logger.info(f"Downloaded {len(zip_data)} bytes")
        
        # Test parsing
        logger.info("Parsing shapefile data...")
        alerts = service.parse_shapefile(zip_data)
        
        if not alerts:
            logger.error("No alerts parsed from shapefile")
            return False
        
        logger.info(f"Parsed {len(alerts)} historical alerts")
        
        # Show sample alert
        if alerts:
            sample = alerts[0]
            logger.info("Sample alert attributes:")
            for key, value in sample.get('attributes', {}).items():
                logger.info(f"  {key}: {value}")
        
        logger.info(f"✅ Successfully retrieved {len(alerts)} historical alerts for Sep 2024 FL")
        return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)