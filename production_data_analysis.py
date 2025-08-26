#!/usr/bin/env python3
"""
Production Data Analysis Script
Checks if production environment has any unique data not in main database
"""

import os
import psycopg2
import psycopg2.extras
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_main_database_connection():
    """Get connection to main database"""
    database_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(database_url)

def check_production_alerts_in_main():
    """Check if production alerts exist in main database"""
    try:
        # Get sample production alerts
        response = requests.get("https://api.hailyai.com/api/alerts?limit=20&sort=newest", timeout=10)
        if response.status_code != 200:
            logger.error(f"Could not get production alerts: {response.status_code}")
            return
        
        prod_data = response.json()
        prod_alerts = prod_data.get('events', [])
        
        if not prod_alerts:
            logger.warning("No production alerts found")
            return
        
        logger.info(f"Checking {len(prod_alerts)} production alerts in main database")
        
        # Check each alert in main database
        conn = get_main_database_connection()
        cursor = conn.cursor()
        
        found_count = 0
        missing_count = 0
        
        for alert in prod_alerts:
            alert_id = alert.get('id')
            if not alert_id:
                continue
                
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE id = %s", (alert_id,))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                found_count += 1
            else:
                missing_count += 1
                logger.warning(f"Production alert NOT in main: {alert_id[:60]}...")
        
        logger.info(f"Results: {found_count} found, {missing_count} missing from main database")
        
        if missing_count == 0:
            logger.info("✅ ALL production alerts exist in main database")
            logger.info("✅ Safe to point production to main database")
        else:
            logger.warning(f"⚠️  {missing_count} production alerts missing from main")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error checking production alerts: {e}")

def main():
    logger.info("=== Production Data Analysis ===")
    check_production_alerts_in_main()
    logger.info("=== Analysis Complete ===")

if __name__ == "__main__":
    main()