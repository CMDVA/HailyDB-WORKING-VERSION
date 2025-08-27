#!/usr/bin/env python3
"""
Force Production Sync - Direct SQL export and manual import approach
Since API deployment hasn't resolved the issue, we need to force sync data to whatever database production is using
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_target_alert_sql():
    """Export the specific target alert as SQL INSERT statements"""
    dev_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(dev_url)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get the specific target alert
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            
            alert = cursor.fetchone()
            if not alert:
                logger.error("Target alert not found in development database")
                return None
            
            # Generate SQL INSERT statement
            columns = list(alert.keys())
            values = []
            
            for key, value in alert.items():
                if value is None:
                    values.append('NULL')
                elif isinstance(value, (dict, list)):
                    # Escape JSON properly
                    json_str = json.dumps(value).replace("'", "''")
                    values.append(f"'{json_str}'::jsonb")
                elif isinstance(value, str):
                    # Escape strings properly
                    escaped = value.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(f"'{value}'")
            
            insert_sql = f"""
INSERT INTO alerts ({', '.join(columns)}) 
VALUES ({', '.join(values)}) 
ON CONFLICT (id) DO UPDATE SET
    event = EXCLUDED.event,
    radar_indicated = EXCLUDED.radar_indicated,
    properties = EXCLUDED.properties,
    geometry = EXCLUDED.geometry,
    updated_at = NOW();
"""
            
            logger.info("Generated SQL INSERT for target alert")
            return insert_sql
            
    except Exception as e:
        logger.error(f"Failed to export target alert: {e}")
        return None
    
    finally:
        if 'conn' in locals():
            conn.close()

def get_sample_alerts_sql():
    """Get a few sample alerts as SQL"""
    dev_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(dev_url)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get 5 radar-detected alerts
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE radar_indicated IS NOT NULL 
                AND radar_indicated != '{}'::jsonb
                ORDER BY sent DESC
                LIMIT 5;
            """)
            
            alerts = cursor.fetchall()
            sql_statements = []
            
            for alert in alerts:
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
                
                insert_sql = f"""
INSERT INTO alerts ({', '.join(columns)}) 
VALUES ({', '.join(values)}) 
ON CONFLICT (id) DO NOTHING;
"""
                sql_statements.append(insert_sql)
            
            return sql_statements
            
    except Exception as e:
        logger.error(f"Failed to export sample alerts: {e}")
        return []
    
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Generate SQL files for manual import"""
    logger.info("Generating SQL files for production sync")
    
    # Export target alert
    target_sql = export_target_alert_sql()
    if target_sql:
        with open('target_alert_sync.sql', 'w') as f:
            f.write("-- Target Alert Sync SQL\n")
            f.write("-- Run this against your production database\n\n")
            f.write(target_sql)
        logger.info("✅ Created target_alert_sync.sql")
    
    # Export sample alerts
    sample_sqls = get_sample_alerts_sql()
    if sample_sqls:
        with open('sample_alerts_sync.sql', 'w') as f:
            f.write("-- Sample Alerts Sync SQL\n")
            f.write("-- Run this against your production database\n\n")
            for sql in sample_sqls:
                f.write(sql + "\n")
        logger.info(f"✅ Created sample_alerts_sync.sql with {len(sample_sqls)} alerts")
    
    logger.info("SQL files generated for manual production sync")
    logger.info("These can be run directly against whatever database production is using")
    
    return True

if __name__ == "__main__":
    main()