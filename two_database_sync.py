#!/usr/bin/env python3
"""
Two Database Sync - Sync from neondb (dev) to HailyDB_prod (production)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_connections():
    """Get connections to both databases"""
    base_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech"
    
    # Development database (current)
    dev_url = f"{base_url}/neondb?sslmode=require"
    
    # Production database (target)
    prod_url = f"{base_url}/HailyDB_prod?sslmode=require"
    
    try:
        dev_conn = psycopg2.connect(dev_url)
        logger.info("✅ Connected to development database (neondb)")
        
        prod_conn = psycopg2.connect(prod_url)
        logger.info("✅ Connected to production database (HailyDB_prod)")
        
        return dev_conn, prod_conn
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

def check_database_status(conn, name):
    """Check database contents"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if alerts table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alerts'
                );
            """)
            table_exists = cursor.fetchone()['exists']
            
            if not table_exists:
                logger.info(f"📊 {name}: alerts table does not exist")
                return 0, False
            
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = cursor.fetchone()['total']
            
            # Check for target alert
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1'
                LIMIT 1;
            """)
            target_alert = cursor.fetchone()
            
            logger.info(f"📊 {name}: {total:,} alerts")
            if target_alert:
                logger.info(f"✅ Target alert found: {target_alert['event']}")
            else:
                logger.info("❌ Target alert missing")
            
            return total, target_alert is not None
            
    except Exception as e:
        logger.error(f"❌ Failed to check {name}: {e}")
        return 0, False

def create_alerts_table(prod_conn):
    """Create alerts table in production if it doesn't exist"""
    try:
        with prod_conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id VARCHAR PRIMARY KEY,
                    event VARCHAR,
                    severity VARCHAR,
                    area_desc TEXT,
                    effective TIMESTAMP,
                    expires TIMESTAMP,
                    sent TIMESTAMP,
                    geometry JSONB,
                    properties JSONB,
                    raw JSONB,
                    ai_summary TEXT,
                    ai_tags JSONB,
                    spc_verified BOOLEAN DEFAULT FALSE,
                    spc_reports JSONB,
                    spc_confidence_score DOUBLE PRECISION,
                    spc_match_method VARCHAR,
                    spc_report_count INTEGER,
                    spc_ai_summary TEXT,
                    radar_indicated JSONB,
                    fips_codes JSONB,
                    county_names JSONB,
                    city_names VARCHAR[],
                    geometry_type VARCHAR,
                    coordinate_count INTEGER,
                    affected_states JSONB,
                    geometry_bounds JSONB,
                    ingested_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    location_confidence DOUBLE PRECISION
                );
            """)
            prod_conn.commit()
            logger.info("✅ Alerts table created/verified in production")
            
    except Exception as e:
        logger.error(f"❌ Failed to create alerts table: {e}")
        raise

def sync_all_alerts(dev_conn, prod_conn):
    """Sync all alerts from development to production"""
    try:
        with dev_conn.cursor(cursor_factory=RealDictCursor) as dev_cursor:
            dev_cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = dev_cursor.fetchone()['total']
            logger.info(f"🔄 Starting sync of {total:,} alerts")
            
            # Get all alerts from development
            dev_cursor.execute("SELECT * FROM alerts ORDER BY id;")
            alerts = dev_cursor.fetchall()
            
            # Clear production and insert all alerts
            with prod_conn.cursor() as prod_cursor:
                logger.info("🗑️ Clearing production database...")
                prod_cursor.execute("TRUNCATE TABLE alerts;")
                
                logger.info("📥 Inserting all alerts...")
                for i, alert in enumerate(alerts):
                    try:
                        # Build insert statement
                        columns = list(alert.keys())
                        placeholders = ['%s'] * len(columns)
                        values = [alert[col] for col in columns]
                        
                        # Handle JSON fields
                        for j, (col, val) in enumerate(zip(columns, values)):
                            if col in ['geometry', 'properties', 'raw', 'ai_tags', 'spc_reports', 
                                     'radar_indicated', 'fips_codes', 'county_names', 'affected_states', 'geometry_bounds']:
                                if val is not None and not isinstance(val, str):
                                    values[j] = json.dumps(val)
                        
                        insert_sql = f"""
                            INSERT INTO alerts ({', '.join(columns)}) 
                            VALUES ({', '.join(placeholders)});
                        """
                        
                        prod_cursor.execute(insert_sql, values)
                        
                        if (i + 1) % 1000 == 0:
                            logger.info(f"📈 Synced {i + 1:,}/{total:,} alerts")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to sync alert {alert.get('id', 'unknown')}: {e}")
                
                prod_conn.commit()
                logger.info(f"✅ Sync complete: {total:,} alerts synced")
                
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        raise

def verify_sync(prod_conn):
    """Verify production database has the data"""
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
    logger.info("🔄 Starting two-database sync: neondb → HailyDB_prod")
    
    try:
        # Connect to both databases
        dev_conn, prod_conn = get_database_connections()
        
        # Check current status
        logger.info("📊 Checking database status...")
        dev_total, dev_has_target = check_database_status(dev_conn, "Development (neondb)")
        prod_total, prod_has_target = check_database_status(prod_conn, "Production (HailyDB_prod)")
        
        # Create production table if needed
        create_alerts_table(prod_conn)
        
        # Sync all data
        sync_all_alerts(dev_conn, prod_conn)
        
        # Verify sync
        if verify_sync(prod_conn):
            logger.info("🎉 DATABASE SYNC SUCCESSFUL!")
            logger.info("🧪 Production should now have all alerts including the target alert")
            return True
        else:
            logger.error("❌ Sync verification failed")
            return False
            
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
    if success:
        print("\n🎯 SYNC COMPLETE!")
        print("Production database now has all development data")
        print("Test: https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1")
    else:
        print("\n❌ SYNC FAILED")
    exit(0 if success else 1)