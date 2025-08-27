#!/usr/bin/env python3
"""
Import CSV to Production Database
Import alerts from CSV file directly to production, skipping exact duplicates
"""

import csv
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_csv_value(value):
    """Parse CSV value handling JSON fields and null values"""
    if value is None or value == '' or value == 'null':
        return None
    
    # Handle JSON fields
    if value.startswith('{') or value.startswith('['):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    # Handle quoted strings
    if value.startswith('"""') and value.endswith('"""'):
        return value[3:-3]
    
    return value

def import_csv_to_production(csv_file_path):
    """Import CSV file to production database"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            # Read CSV
            csv_reader = csv.DictReader(file)
            alerts = list(csv_reader)
        
        logger.info(f"Loaded {len(alerts)} alerts from CSV")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check existing alerts to avoid duplicates
            cursor.execute("SELECT id FROM alerts;")
            existing_ids = {row['id'] for row in cursor.fetchall()}
            logger.info(f"Found {len(existing_ids)} existing alerts in production")
            
            # Process alerts
            inserted_count = 0
            skipped_count = 0
            
            for alert_data in alerts:
                alert_id = alert_data.get('id')
                
                # Skip if already exists
                if alert_id in existing_ids:
                    skipped_count += 1
                    continue
                
                try:
                    # Parse all fields
                    parsed_alert = {}
                    for key, value in alert_data.items():
                        parsed_value = parse_csv_value(value)
                        if parsed_value is not None:
                            parsed_alert[key] = parsed_value
                    
                    # Ensure required fields exist
                    if not parsed_alert.get('id'):
                        continue
                    
                    # Insert alert
                    columns = list(parsed_alert.keys())
                    placeholders = ['%s'] * len(columns)
                    values = [parsed_alert[col] for col in columns]
                    
                    insert_sql = f"""
                        INSERT INTO alerts ({', '.join(columns)}) 
                        VALUES ({', '.join(placeholders)});
                    """
                    
                    cursor.execute(insert_sql, values)
                    inserted_count += 1
                    
                    if inserted_count % 100 == 0:
                        logger.info(f"Inserted {inserted_count} alerts...")
                    
                except Exception as e:
                    logger.debug(f"Failed to insert alert {alert_id}: {e}")
                    continue
            
            # Commit all changes
            conn.commit()
            
            logger.info(f"Import complete:")
            logger.info(f"  - Inserted: {inserted_count:,} new alerts")
            logger.info(f"  - Skipped: {skipped_count:,} duplicates")
            logger.info(f"  - Total processed: {len(alerts):,}")
            
            # Verify final count
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            total_alerts = cursor.fetchone()['count']
            logger.info(f"Production database now has {total_alerts:,} total alerts")
            
        conn.close()
        return inserted_count, skipped_count
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return 0, 0

def verify_target_alert():
    """Check if target alert is now in production"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, event, radar_indicated 
                FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            logger.info("✅ Target alert found in production database")
            return True
        else:
            logger.warning("❌ Target alert not found in production")
            return False
            
    except Exception as e:
        logger.error(f"Target alert verification failed: {e}")
        return False

def main():
    """Execute CSV import to production"""
    csv_file = 'attached_assets/alerts_1756304626210.csv'
    
    logger.info("🚀 Starting CSV import to production database")
    logger.info(f"Source file: {csv_file}")
    
    # Import CSV data
    inserted, skipped = import_csv_to_production(csv_file)
    
    if inserted > 0:
        logger.info(f"✅ Successfully imported {inserted:,} alerts")
        
        # Verify target alert
        if verify_target_alert():
            logger.info("🎯 Target alert confirmed in production")
        else:
            logger.warning("Target alert may not have been in CSV file")
        
        logger.info("Production database update complete")
        return True
    else:
        logger.error("❌ No alerts were imported")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ CSV import to production successful")
    else:
        logger.error("❌ CSV import failed")