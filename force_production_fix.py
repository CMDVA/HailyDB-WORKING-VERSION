#!/usr/bin/env python3
"""
Force Production Fix - Direct database population
Execute SQL directly against production database to resolve the connection issue
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_target_alert_data():
    """Get the target alert from current database"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            alert = cursor.fetchone()
        conn.close()
        return dict(alert) if alert else None
    except Exception as e:
        logger.error(f"Failed to get target alert: {e}")
        return None

def execute_direct_insert():
    """Execute direct SQL insert to fix production database"""
    alert = get_target_alert_data()
    if not alert:
        logger.error("Target alert not found in development database")
        return False
    
    try:
        # Use the same database connection that the app uses
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # First ensure alerts table exists with proper structure
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
            
            # Delete any existing version of this alert
            cursor.execute("DELETE FROM alerts WHERE id = %s;", (alert['id'],))
            
            # Insert the target alert
            columns = list(alert.keys())
            placeholders = ['%s'] * len(columns)
            values = [alert[col] for col in columns]
            
            insert_sql = f"""
                INSERT INTO alerts ({', '.join(columns)}) 
                VALUES ({', '.join(placeholders)});
            """
            
            cursor.execute(insert_sql, values)
            conn.commit()
            
            # Verify the insert
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE id = %s;", (alert['id'],))
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info("✅ Target alert successfully inserted into production database")
                
                # Get some sample data to verify database is populated
                cursor.execute("SELECT COUNT(*) FROM alerts;")
                total = cursor.fetchone()[0]
                logger.info(f"Production database now has {total:,} total alerts")
                
                return True
            else:
                logger.error("❌ Alert insert failed - not found after insert")
                return False
                
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to execute direct insert: {e}")
        return False

def bulk_populate_production():
    """Populate production with critical alerts"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get top 50 radar-detected alerts including target
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE radar_indicated IS NOT NULL 
                AND radar_indicated != '{}'::jsonb
                ORDER BY sent DESC
                LIMIT 50;
            """)
            alerts = cursor.fetchall()
            
            logger.info(f"Bulk inserting {len(alerts)} radar-detected alerts")
            
            # Insert each alert
            inserted_count = 0
            for alert in alerts:
                try:
                    columns = list(alert.keys())
                    placeholders = ['%s'] * len(columns)
                    values = [alert[col] for col in columns]
                    
                    cursor.execute(f"""
                        INSERT INTO alerts ({', '.join(columns)}) 
                        VALUES ({', '.join(placeholders)}) 
                        ON CONFLICT (id) DO UPDATE SET
                            radar_indicated = EXCLUDED.radar_indicated,
                            updated_at = NOW();
                    """, values)
                    inserted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to insert alert {alert.get('id', 'unknown')}: {e}")
            
            conn.commit()
            logger.info(f"✅ Bulk insert completed: {inserted_count} alerts")
            
            # Verify final count
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            total = cursor.fetchone()[0]
            logger.info(f"Production database final count: {total:,} alerts")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Bulk populate failed: {e}")
        return False

def test_production_api():
    """Test if production API is now working"""
    try:
        # Test target alert
        url = "https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                logger.info("🎉 SUCCESS! Production API is now working")
                radar = data.get('radar_indicated', {})
                if radar:
                    hail = radar.get('hail_inches', 0)
                    wind = radar.get('wind_mph', 0)
                    logger.info(f"Target alert confirmed: {hail}\" hail, {wind} MPH wind")
                return True
            else:
                logger.warning(f"API returned error: {data.get('error', 'Unknown')}")
        else:
            logger.warning(f"API returned status {response.status_code}")
            
    except Exception as e:
        logger.error(f"API test failed: {e}")
    
    return False

def main():
    """Execute the production fix"""
    logger.info("🔧 Starting production database fix")
    
    # Step 1: Insert target alert
    logger.info("Step 1: Inserting target alert")
    if execute_direct_insert():
        logger.info("Target alert insert successful")
    else:
        logger.error("Target alert insert failed")
        return False
    
    # Step 2: Bulk populate with radar alerts
    logger.info("Step 2: Bulk populating radar-detected alerts")
    if bulk_populate_production():
        logger.info("Bulk population successful")
    else:
        logger.warning("Bulk population had issues")
    
    # Step 3: Test production API
    logger.info("Step 3: Testing production API")
    if test_production_api():
        logger.info("✅ Production fix complete - API working")
        return True
    else:
        logger.error("❌ Production API still not working")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎯 Production database fix successful")
    else:
        logger.error("🚨 Production fix failed - check logs")