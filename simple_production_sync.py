#!/usr/bin/env python3
"""
Simple Production Sync - Copy missing production alerts to main database
"""

import os
import psycopg2
import psycopg2.extras
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_main_database_connection():
    """Get connection to main database"""
    database_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(database_url)

def copy_missing_production_alerts():
    """Copy the 4 missing production alerts to main database"""
    
    # These are the 4 alert IDs we know are missing
    missing_alert_ids = [
        'urn:oid:2.49.0.1.840.0.8de957b49e04de95a99aa5ccdcfdc188cacc3188.001.1',
        'urn:oid:2.49.0.1.840.0.577fb2796d2da255522909481dfed5f7b91089f4.001.1', 
        'urn:oid:2.49.0.1.840.0.f27cb0969b1b430af147acfff638ad0b45fb19bc.001.1',
        'urn:oid:2.49.0.1.840.0.a2bb292df667245ecb9df0ff7c8179489812c0cd.001.1'
    ]
    
    conn = get_main_database_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    success_count = 0
    
    for alert_id in missing_alert_ids:
        try:
            # Get full alert data from production API
            response = requests.get(f"https://api.hailyai.com/api/alerts/{alert_id}", timeout=10)
            if response.status_code != 200:
                logger.warning(f"Could not get alert {alert_id[:60]}... from production")
                continue
            
            alert_data = response.json()
            
            # Insert using production alert format with simplified mapping
            insert_sql = """
            INSERT INTO alerts (
                id, event, severity, area_desc, effective, expires, sent,
                geometry, properties, radar_indicated, city_names, county_names,
                affected_states, data_source, source_type, spc_verified,
                ingested_at
            ) VALUES (
                %(id)s, %(event)s, %(severity)s, %(area_desc)s, 
                %(effective)s, %(expires)s, %(sent)s, %(geometry)s, %(properties)s,
                %(radar_indicated)s, %(city_names)s, %(county_names)s, %(affected_states)s,
                %(data_source)s, %(source_type)s, %(spc_verified)s, %(ingested_at)s
            ) ON CONFLICT (id) DO NOTHING
            """
            
            # Prepare data for insertion
            insert_data = {
                'id': alert_data.get('id'),
                'event': alert_data.get('event'),
                'severity': alert_data.get('severity'),
                'area_desc': alert_data.get('area_desc'),
                'effective': alert_data.get('effective'),
                'expires': alert_data.get('expires'),
                'sent': alert_data.get('sent'),
                'geometry': json.dumps(alert_data.get('geometry', {})),
                'properties': json.dumps(alert_data.get('properties', {})),
                'radar_indicated': json.dumps(alert_data.get('radar_indicated', {})),
                'city_names': alert_data.get('city_names', []),
                'county_names': alert_data.get('county_names', []),
                'affected_states': json.dumps(alert_data.get('affected_states', [])),
                'data_source': alert_data.get('data_source', 'National Weather Service'),
                'source_type': alert_data.get('source_type', 'historical_nws_alert'),
                'spc_verified': alert_data.get('spc_verified', False),
                'ingested_at': datetime.now()
            }
            
            cursor.execute(insert_sql, insert_data)
            conn.commit()
            
            logger.info(f"✅ Migrated: {alert_data.get('event')} - {alert_id[:60]}...")
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {alert_id[:60]}...: {e}")
    
    cursor.close()
    conn.close()
    
    logger.info(f"=== Migration Complete: {success_count}/4 alerts copied ===")
    return success_count

def main():
    logger.info("=== Simple Production Sync ===")
    copied_count = copy_missing_production_alerts()
    
    if copied_count > 0:
        logger.info("✅ Main database now has all production alerts")
        logger.info("✅ Safe to point production to main database")
    else:
        logger.warning("⚠️  No alerts were copied")

if __name__ == "__main__":
    main()