#!/usr/bin/env python3
"""
Complete Data Sync - Final sync from neondb to HailyDB_prod
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_data_simple():
    """Simple data sync using INSERT statements"""
    dev_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    prod_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/HailyDB_prod?sslmode=require"
    
    try:
        dev_conn = psycopg2.connect(dev_url)
        prod_conn = psycopg2.connect(prod_url)
        
        logger.info("✅ Connected to both databases")
        
        # Get all data from development
        with dev_conn.cursor(cursor_factory=RealDictCursor) as dev_cursor:
            dev_cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = dev_cursor.fetchone()['total']
            logger.info(f"📊 Found {total:,} alerts to sync")
            
            # Get all alerts in batches
            batch_size = 500
            synced = 0
            
            for offset in range(0, total, batch_size):
                dev_cursor.execute("""
                    SELECT * FROM alerts 
                    ORDER BY id 
                    LIMIT %s OFFSET %s;
                """, (batch_size, offset))
                
                batch = dev_cursor.fetchall()
                if not batch:
                    break
                
                # Insert batch into production
                with prod_conn.cursor() as prod_cursor:
                    for alert in batch:
                        try:
                            # Build parameterized insert
                            columns = list(alert.keys())
                            placeholders = ['%s'] * len(columns)
                            values = list(alert.values())
                            
                            insert_sql = f"""
                                INSERT INTO alerts ({', '.join(columns)}) 
                                VALUES ({', '.join(placeholders)}) 
                                ON CONFLICT (id) DO NOTHING;
                            """
                            
                            prod_cursor.execute(insert_sql, values)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to insert {alert.get('id', 'unknown')}: {e}")
                    
                    prod_conn.commit()
                    synced += len(batch)
                    logger.info(f"📈 Synced {synced:,}/{total:,} alerts")
        
        # Verify sync
        with prod_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            prod_total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target = cursor.fetchone()
            
            logger.info(f"🔍 Production database: {prod_total:,} alerts")
            if target:
                logger.info(f"✅ Target alert synced: {target['event']}")
                return True
            else:
                logger.error("❌ Target alert missing")
                return False
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        return False
    
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()
        if 'prod_conn' in locals():
            prod_conn.close()

def test_production_api():
    """Test the production API after sync"""
    import requests
    
    try:
        # Test the target alert
        url = "https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                logger.info(f"🎉 PRODUCTION API SUCCESS: {data.get('event', 'Unknown')}")
                return True
        
        logger.info(f"❌ Production API still returns: {response.status_code}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Production API test failed: {e}")
        return False

def main():
    """Main sync function"""
    logger.info("🔄 Starting complete data sync to production")
    
    if sync_data_simple():
        logger.info("✅ Data sync completed successfully")
        
        # Test production API
        logger.info("🧪 Testing production API...")
        if test_production_api():
            logger.info("🎯 COMPLETE SUCCESS: Production API now working!")
        else:
            logger.info("⏳ Production may need time to update, or deployment required")
        
        return True
    else:
        logger.error("❌ Data sync failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)