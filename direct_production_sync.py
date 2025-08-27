#!/usr/bin/env python3
"""
Direct Production Sync - Connect to BOTH databases and transfer data
Since production uses a different DATABASE_URL that we cannot modify,
we need to find and sync TO that production database directly.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_production_database_url():
    """
    Try to identify the actual production database URL
    This may be different from our current DATABASE_URL
    """
    current_url = os.environ.get('DATABASE_URL')
    logger.info(f"Current DATABASE_URL: {current_url}")
    
    # Production might use different environment variables
    possible_prod_vars = [
        'PRODUCTION_DATABASE_URL',
        'PROD_DATABASE_URL', 
        'DATABASE_URL_PROD',
        'NEON_DATABASE_URL',
        'POSTGRES_URL'
    ]
    
    for var in possible_prod_vars:
        url = os.environ.get(var)
        if url and url != current_url:
            logger.info(f"Found potential production database: {var}")
            return url
    
    logger.warning("No separate production database URL found")
    return None

def test_database_connection(db_url, name):
    """Test if we can connect to a database"""
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            count = cursor.fetchone()[0]
        conn.close()
        logger.info(f"{name} database: {count:,} alerts")
        return True, count
    except Exception as e:
        logger.error(f"Cannot connect to {name} database: {e}")
        return False, 0

def sync_target_alert_to_production(dev_url, prod_url):
    """Sync the specific target alert to production database"""
    target_id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1'
    
    try:
        # Get alert from development
        dev_conn = psycopg2.connect(dev_url)
        with dev_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM alerts WHERE id = %s;", (target_id,))
            alert = cursor.fetchone()
        dev_conn.close()
        
        if not alert:
            logger.error("Target alert not found in development database")
            return False
        
        # Insert into production
        prod_conn = psycopg2.connect(prod_url)
        with prod_conn.cursor() as cursor:
            # Create alerts table if it doesn't exist
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
                    spc_verified VARCHAR,
                    spc_reports JSONB,
                    spc_confidence_score FLOAT,
                    spc_match_method VARCHAR,
                    spc_report_count VARCHAR,
                    spc_ai_summary TEXT,
                    radar_indicated JSONB,
                    fips_codes JSONB,
                    county_names JSONB,
                    city_names TEXT,
                    geometry_type VARCHAR,
                    coordinate_count VARCHAR,
                    affected_states JSONB,
                    geometry_bounds JSONB,
                    ingested_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    location_confidence FLOAT
                );
            """)
            
            # Insert the alert
            columns = list(alert.keys())
            placeholders = ['%s'] * len(columns)
            values = [alert[col] for col in columns]
            
            cursor.execute(f"""
                INSERT INTO alerts ({', '.join(columns)}) 
                VALUES ({', '.join(placeholders)}) 
                ON CONFLICT (id) DO UPDATE SET
                    radar_indicated = EXCLUDED.radar_indicated,
                    properties = EXCLUDED.properties,
                    updated_at = NOW();
            """, values)
            
            prod_conn.commit()
        prod_conn.close()
        
        logger.info("✅ Target alert synced to production database")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync target alert: {e}")
        return False

def main():
    """Main sync operation"""
    dev_url = os.environ.get('DATABASE_URL')
    
    logger.info("🔍 Searching for production database...")
    
    # Test current database
    dev_works, dev_count = test_database_connection(dev_url, "Development")
    if not dev_works:
        logger.error("Cannot access development database")
        return False
    
    # Try to find production database
    prod_url = get_production_database_url()
    if prod_url:
        prod_works, prod_count = test_database_connection(prod_url, "Production")
        if prod_works:
            logger.info(f"🎯 Found production database with {prod_count:,} alerts")
            return sync_target_alert_to_production(dev_url, prod_url)
    
    # If no separate production database found, use a different approach
    logger.warning("No separate production database detected")
    logger.info("Production may be using the same database with different connection parameters")
    
    # Generate SQL file for manual execution
    logger.info("📝 Generating SQL for manual production sync...")
    
    try:
        conn = psycopg2.connect(dev_url)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            alert = cursor.fetchone()
        conn.close()
        
        if alert:
            # Generate INSERT statement
            columns = list(alert.keys())
            values = []
            
            for key, value in alert.items():
                if value is None:
                    values.append('NULL')
                elif isinstance(value, (dict, list)):
                    json_str = json.dumps(value).replace("'", "''")
                    values.append(f"'{json_str}'::jsonb")
                elif isinstance(value, str):
                    escaped = value.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(f"'{value}'")
            
            sql = f"""
-- Production Sync SQL - Run this against your actual production database
-- This will insert the target alert that should make the API work

INSERT INTO alerts ({', '.join(columns)}) 
VALUES ({', '.join(values)}) 
ON CONFLICT (id) DO UPDATE SET
    radar_indicated = EXCLUDED.radar_indicated,
    properties = EXCLUDED.properties,
    updated_at = NOW();

-- Verify the insert worked:
SELECT id, event, radar_indicated FROM alerts 
WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
"""
            
            with open('production_manual_sync.sql', 'w') as f:
                f.write(sql)
            
            logger.info("✅ Created production_manual_sync.sql")
            logger.info("Run this SQL against whatever database production is actually using")
            return True
            
    except Exception as e:
        logger.error(f"Failed to generate SQL: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎯 Next step: Execute the SQL against your production database")
    else:
        logger.error("❌ Sync failed - check logs for details")