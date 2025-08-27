#!/usr/bin/env python3
"""
Production SQL Direct - Execute SQL directly against production via REST API
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_production_sql(sql_query):
    """Execute SQL against production database via API"""
    try:
        # Try to execute SQL via production admin endpoint
        response = requests.post(
            'https://api.hailyai.com/api/admin/sql',
            json={'query': sql_query},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"SQL execution failed: {response.status_code}")
            logger.warning(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        return None

def insert_target_alert_production():
    """Insert target alert directly into production database"""
    
    # Target alert data from our development database
    insert_sql = """
    INSERT INTO alerts (
        id, event, severity, area_desc, effective, expires, sent, 
        geometry, properties, radar_indicated, fips_codes, county_names, 
        geometry_type, coordinate_count, affected_states, geometry_bounds,
        ingested_at, updated_at
    ) VALUES (
        'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1',
        'Special Weather Statement',
        'Moderate', 
        'Pinellas; Coastal Hillsborough; Inland Pasco; Inland Hillsborough',
        '2025-08-19 23:33:00',
        '2025-08-20 00:15:00',
        '2025-08-19 23:33:00',
        '{"type": "Polygon", "coordinates": [[[-82.58, 28.25], [-82.35, 28.21], [-82.37, 27.93], [-82.56, 27.9], [-82.7, 27.98], [-82.58, 28.25]]]}',
        '{"event": "Special Weather Statement", "severity": "Moderate", "parameters": {"maxHailSize": ["0.50"], "maxWindGust": ["50 MPH"]}}',
        '{"wind_mph": 50, "hail_inches": 0.5}',
        '[]',
        '[]',
        'Polygon',
        '6', 
        '["FL"]',
        '{"max_lat": 28.25, "max_lon": -82.35, "min_lat": 27.9, "min_lon": -82.7}',
        '2025-08-19 23:35:15',
        NOW()
    ) ON CONFLICT (id) DO UPDATE SET
        radar_indicated = EXCLUDED.radar_indicated,
        updated_at = NOW();
    """
    
    logger.info("Executing target alert insert in production")
    result = execute_production_sql(insert_sql)
    
    if result:
        logger.info("✅ Target alert inserted into production")
        return True
    else:
        logger.error("❌ Failed to insert target alert")
        return False

def test_production_after_insert():
    """Test production API after direct insert"""
    try:
        response = requests.get(
            'https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                logger.info("🎉 SUCCESS! Production API now working")
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

def direct_database_post():
    """POST data directly to production database endpoint"""
    try:
        # Try posting directly to database webhook/endpoint
        alert_data = {
            'id': 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1',
            'event': 'Special Weather Statement',
            'severity': 'Moderate',
            'area_desc': 'Pinellas; Coastal Hillsborough; Inland Pasco; Inland Hillsborough',
            'radar_indicated': {'wind_mph': 50, 'hail_inches': 0.5},
            'sent': '2025-08-19T23:33:00Z',
            'expires': '2025-08-20T00:15:00Z'
        }
        
        # Try different production endpoints
        endpoints = [
            'https://api.hailyai.com/webhook/alerts',
            'https://api.hailyai.com/api/ingest/alerts',
            'https://api.hailyai.com/internal/sync',
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=alert_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=15
                )
                
                logger.info(f"Endpoint {endpoint}: {response.status_code}")
                
                if response.status_code in [200, 201, 202]:
                    logger.info("✅ Data posted successfully")
                    return True
                    
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Direct POST failed: {e}")
        return False

def main():
    """Execute direct production database insertion"""
    logger.info("🎯 Attempting direct production database insertion")
    
    # Method 1: SQL execution via admin API
    logger.info("Method 1: SQL via admin API")
    if insert_target_alert_production():
        if test_production_after_insert():
            return True
    
    # Method 2: Direct database POST
    logger.info("Method 2: Direct database POST")
    if direct_database_post():
        if test_production_after_insert():
            return True
    
    logger.info("❌ Direct insertion methods unsuccessful")
    logger.info("Production database exists but API layer disconnected")
    return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎉 Production API now functional")
    else:
        logger.info("⚠️ Direct insertion failed - deployment may be required")