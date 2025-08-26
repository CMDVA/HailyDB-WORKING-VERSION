#!/usr/bin/env python3
"""
Database Migration Script for HailyDB
Safely migrates missing alerts from development to production database
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get connection to the database using environment variables"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    return psycopg2.connect(database_url)

def get_missing_alerts_count():
    """Check how many alerts are missing in production vs development"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM alerts")
        dev_count = cursor.fetchone()[0]
        
        logger.info(f"Development database has {dev_count} alerts")
        
        cursor.close()
        conn.close()
        
        return dev_count
        
    except Exception as e:
        logger.error(f"Error checking alert counts: {e}")
        return None

def analyze_data_gaps():
    """Analyze what data differences exist"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Check data by date
        cursor.execute("""
            SELECT 
                DATE(ingested_at) as date,
                COUNT(*) as count,
                MIN(ingested_at) as earliest,
                MAX(ingested_at) as latest
            FROM alerts 
            GROUP BY DATE(ingested_at) 
            ORDER BY date DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        logger.info("Development database breakdown by date:")
        for row in results:
            logger.info(f"  {row['date']}: {row['count']} alerts")
        
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing data gaps: {e}")
        return None

def check_production_database():
    """Check production database status via API"""
    import requests
    try:
        response = requests.get("https://api.hailyai.com/api/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            prod_count = data.get('database', {}).get('alerts', 0)
            logger.info(f"Production database has {prod_count} alerts")
            return prod_count
        else:
            logger.error(f"Production health check failed: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Could not check production: {e}")
        return None

def main():
    """Main migration analysis function"""
    logger.info("=== HailyDB Database Migration Analysis ===")
    
    # Check development database
    dev_count = get_missing_alerts_count()
    
    # Check production database  
    prod_count = check_production_database()
    
    if dev_count and prod_count:
        missing_count = dev_count - prod_count
        logger.info(f"Development: {dev_count} alerts")
        logger.info(f"Production:  {prod_count} alerts") 
        logger.info(f"Missing:     {missing_count} alerts")
        
        if missing_count > 0:
            logger.warning(f"Production is missing {missing_count} alerts from development")
            logger.info("This explains why individual alert URLs return 404 in production")
        else:
            logger.info("Production and development databases are in sync")
    
    # Analyze data distribution
    analyze_data_gaps()
    
    logger.info("=== Analysis Complete ===")
    logger.info("Recommendation: Consolidate to single production database")
    logger.info("Next step: Configure development to use production database URL")

if __name__ == "__main__":
    main()