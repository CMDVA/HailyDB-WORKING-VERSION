#!/usr/bin/env python3
"""
Direct Database Sync - Connect to both dev and production databases and transfer data
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_production_database_url():
    """Try to determine production database URL"""
    # Check common production environment variables
    prod_vars = [
        'PRODUCTION_DATABASE_URL',
        'PROD_DATABASE_URL', 
        'DATABASE_URL_PROD',
        'NEON_DATABASE_URL',
        'POSTGRES_URL_PROD'
    ]
    
    for var in prod_vars:
        url = os.environ.get(var)
        if url:
            logger.info(f"Found production database URL in {var}")
            return url
    
    # If not found, ask user to provide it
    logger.error("❌ Production database URL not found")
    logger.info("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'DATABASE' in key or 'POSTGRES' in key or 'NEON' in key:
            logger.info(f"  {key}: {os.environ[key][:50]}...")
    
    return None

def connect_to_databases():
    """Connect to both development and production databases"""
    try:
        # Development database
        dev_url = os.environ.get('DATABASE_URL')
        if not dev_url:
            raise ValueError("Development DATABASE_URL not found")
        
        dev_conn = psycopg2.connect(dev_url)
        logger.info("✅ Connected to development database")
        
        # Production database
        prod_url = get_production_database_url()
        if not prod_url:
            return dev_conn, None
        
        prod_conn = psycopg2.connect(prod_url)
        logger.info("✅ Connected to production database")
        
        return dev_conn, prod_conn
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

def check_database_contents(conn, name):
    """Check what's in a database"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1'
                LIMIT 1;
            """)
            target_alert = cursor.fetchone()
            
            logger.info(f"📊 {name} database: {total:,} alerts")
            if target_alert:
                logger.info(f"✅ Target alert found: {target_alert['event']}")
            else:
                logger.info("❌ Target alert missing")
            
            return total, target_alert is not None
            
    except Exception as e:
        logger.error(f"❌ Failed to check {name} database: {e}")
        return 0, False

def sync_alerts_batch(dev_conn, prod_conn, batch_size=100):
    """Sync alerts from development to production in batches"""
    try:
        with dev_conn.cursor(cursor_factory=RealDictCursor) as dev_cursor:
            dev_cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = dev_cursor.fetchone()['total']
            logger.info(f"📊 Starting sync of {total:,} alerts")
            
            synced = 0
            batch_num = 0
            
            while synced < total:
                offset = batch_num * batch_size
                
                # Get batch from development
                dev_cursor.execute("""
                    SELECT * FROM alerts 
                    ORDER BY id 
                    LIMIT %s OFFSET %s;
                """, (batch_size, offset))
                
                batch = dev_cursor.fetchall()
                if not batch:
                    break
                
                # Prepare insert data for production
                with prod_conn.cursor() as prod_cursor:
                    for alert in batch:
                        # Convert row to dict and handle special types
                        values = []
                        placeholders = []
                        
                        for key, value in alert.items():
                            placeholders.append('%s')
                            if isinstance(value, (dict, list)):
                                values.append(json.dumps(value))
                            else:
                                values.append(value)
                        
                        # Build INSERT statement with conflict handling
                        columns = ', '.join(alert.keys())
                        placeholder_str = ', '.join(placeholders)
                        
                        insert_sql = f"""
                            INSERT INTO alerts ({columns}) 
                            VALUES ({placeholder_str}) 
                            ON CONFLICT (id) DO NOTHING;
                        """
                        
                        try:
                            prod_cursor.execute(insert_sql, values)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to insert alert {alert.get('id', 'unknown')}: {e}")
                
                prod_conn.commit()
                synced += len(batch)
                batch_num += 1
                
                if batch_num % 10 == 0:
                    logger.info(f"📈 Synced {synced:,}/{total:,} alerts ({synced/total*100:.1f}%)")
            
            logger.info(f"✅ Sync complete: {synced:,} alerts processed")
            return synced
            
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        raise

def verify_sync(prod_conn):
    """Verify the sync was successful"""
    try:
        with prod_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target = cursor.fetchone()
            
            logger.info(f"🔍 Production verification: {total:,} alerts")
            if target:
                logger.info(f"✅ Target alert synced: {target['event']}")
                return True
            else:
                logger.error("❌ Target alert still missing")
                return False
                
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main sync function"""
    logger.info("🔄 Starting direct database sync")
    
    try:
        # Connect to both databases
        dev_conn, prod_conn = connect_to_databases()
        
        if not prod_conn:
            logger.error("❌ Cannot connect to production database")
            logger.info("💡 Set PRODUCTION_DATABASE_URL environment variable")
            return False
        
        # Check current state
        logger.info("📊 Checking database contents...")
        dev_total, dev_has_target = check_database_contents(dev_conn, "Development")
        prod_total, prod_has_target = check_database_contents(prod_conn, "Production")
        
        # If production is missing data, sync it
        if dev_total > prod_total or not prod_has_target:
            logger.info("🔄 Starting data sync...")
            synced = sync_alerts_batch(dev_conn, prod_conn)
            
            # Verify sync
            if verify_sync(prod_conn):
                logger.info("🎉 Sync successful!")
                return True
            else:
                logger.error("❌ Sync verification failed")
                return False
        else:
            logger.info("✅ Production database already up to date")
            return True
            
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        return False
    
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()
        if 'prod_conn' in locals():
            prod_conn.close()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)