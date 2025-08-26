#!/usr/bin/env python3
"""
Migrate Missing Production Alerts to Main Database
Safely copies production alerts that don't exist in main database
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

def get_production_alerts_missing_from_main():
    """Get production alerts that don't exist in main database"""
    try:
        # Get all recent production alerts
        response = requests.get("https://api.hailyai.com/api/alerts?limit=500&sort=newest", timeout=30)
        if response.status_code != 200:
            logger.error(f"Could not get production alerts: {response.status_code}")
            return []
        
        prod_data = response.json()
        prod_alerts = prod_data.get('events', [])
        
        if not prod_alerts:
            logger.warning("No production alerts found")
            return []
        
        logger.info(f"Checking {len(prod_alerts)} production alerts against main database")
        
        conn = get_main_database_connection()
        cursor = conn.cursor()
        
        missing_alerts = []
        
        for alert in prod_alerts:
            alert_id = alert.get('id')
            if not alert_id:
                continue
                
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE id = %s", (alert_id,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                missing_alerts.append(alert)
                logger.info(f"Found missing alert: {alert.get('event', 'Unknown')} - {alert_id[:60]}...")
        
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(missing_alerts)} alerts to migrate from production")
        return missing_alerts
        
    except Exception as e:
        logger.error(f"Error finding missing alerts: {e}")
        return []

def migrate_alert_to_main(alert_data):
    """Migrate a single alert to main database"""
    try:
        conn = get_main_database_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Convert the API response back to database format
        insert_sql = """
        INSERT INTO alerts (
            id, event, headline, description, instruction, urgency, severity, certainty,
            areas, geometry, ingested_at, expires, onset, effective, sent, status,
            message_type, category, response, radar_indicated, city_names, location_enrichment,
            city_names_confidence_score, data_source, source_type
        ) VALUES (
            %(id)s, %(event)s, %(headline)s, %(description)s, %(instruction)s, 
            %(urgency)s, %(severity)s, %(certainty)s, %(areas)s, %(geometry)s,
            %(ingested_at)s, %(expires)s, %(onset)s, %(effective)s, %(sent)s,
            %(status)s, %(message_type)s, %(category)s, %(response)s, 
            %(radar_indicated)s, %(city_names)s, %(location_enrichment)s,
            %(city_names_confidence_score)s, %(data_source)s, %(source_type)s
        ) ON CONFLICT (id) DO NOTHING
        """
        
        # Prepare data for insertion
        alert_data['ingested_at'] = datetime.now()
        alert_data['data_source'] = 'NWS API'
        alert_data['source_type'] = 'nws_alert'
        
        # Handle JSON fields
        if isinstance(alert_data.get('areas'), list):
            alert_data['areas'] = json.dumps(alert_data['areas'])
        if isinstance(alert_data.get('geometry'), dict):
            alert_data['geometry'] = json.dumps(alert_data['geometry'])
        if isinstance(alert_data.get('radar_indicated'), dict):
            alert_data['radar_indicated'] = json.dumps(alert_data['radar_indicated'])
        if isinstance(alert_data.get('location_enrichment'), dict):
            alert_data['location_enrichment'] = json.dumps(alert_data['location_enrichment'])
        
        cursor.execute(insert_sql, alert_data)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully migrated alert: {alert_data.get('id', 'Unknown')[:60]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating alert: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("=== Production Alert Migration ===")
    
    # Find missing alerts
    missing_alerts = get_production_alerts_missing_from_main()
    
    if not missing_alerts:
        logger.info("✅ No missing alerts found - main database is up to date")
        return
    
    # Migrate each missing alert
    success_count = 0
    fail_count = 0
    
    for alert in missing_alerts:
        if migrate_alert_to_main(alert):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"=== Migration Complete ===")
    logger.info(f"✅ Successfully migrated: {success_count} alerts")
    if fail_count > 0:
        logger.warning(f"❌ Failed to migrate: {fail_count} alerts")
    
    if success_count > 0:
        logger.info("Main database now contains all production alerts")
        logger.info("Ready to point production to main database")

if __name__ == "__main__":
    main()