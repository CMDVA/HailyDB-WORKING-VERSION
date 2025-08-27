#!/usr/bin/env python3
"""
Direct Production Sync - Import complete development data to production
Execute this script in your production environment with production DATABASE_URL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_to_production():
    """Import the production_sync_data.sql file to production database"""
    
    # Check if we're in production environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL not found")
        return False
    
    # Check if the sync file exists
    if not os.path.exists('production_sync_data.sql'):
        logger.error("❌ production_sync_data.sql not found")
        logger.info("📋 Run production_data_bridge.py first to create the sync file")
        return False
    
    try:
        # Connect to production database
        conn = psycopg2.connect(database_url)
        logger.info("✅ Connected to production database")
        
        # Read and execute the sync file
        with open('production_sync_data.sql', 'r') as f:
            sql_content = f.read()
        
        logger.info("📥 Executing production data sync...")
        
        with conn.cursor() as cursor:
            cursor.execute(sql_content)
            conn.commit()
        
        logger.info("✅ Production sync completed")
        
        # Verify the sync
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = cursor.fetchone()['total']
            logger.info(f"📊 Production database now has {total:,} alerts")
            
            # Test the specific failing alert
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            
            result = cursor.fetchone()
            if result:
                logger.info(f"✅ Target alert found: {result['event']}")
                logger.info("🎯 Production sync successful - 404 errors should be resolved")
            else:
                logger.warning("⚠️ Target alert not found after sync")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Production sync failed: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = sync_to_production()
    if success:
        print("\n🎉 Production database sync completed!")
        print("🧪 Test the API: /api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1")
    else:
        print("\n❌ Sync failed - check the logs above")
        exit(1)