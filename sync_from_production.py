#!/usr/bin/env python3
"""
Sync FROM Production - Pull complete data from production to development
Production has 95.98MB with full SPC reports dataset
"""

import os
import requests
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def pull_production_alerts():
    """Pull all alerts from production API"""
    try:
        all_alerts = []
        page = 1
        limit = 1000
        
        while True:
            url = f"https://api.hailyai.com/api/alerts?page={page}&limit={limit}"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch page {page}: {response.status_code}")
                break
            
            data = response.json()
            alerts = data.get('alerts', [])
            
            if not alerts:
                logger.info(f"No more alerts found at page {page}")
                break
            
            all_alerts.extend(alerts)
            logger.info(f"Fetched page {page}: {len(alerts)} alerts ({len(all_alerts)} total)")
            
            # Check if this is the last page
            pagination = data.get('pagination', {})
            if pagination.get('page', 0) >= pagination.get('total_pages', 0):
                break
                
            page += 1
        
        logger.info(f"Total alerts pulled from production: {len(all_alerts)}")
        return all_alerts
        
    except Exception as e:
        logger.error(f"Failed to pull production alerts: {e}")
        return []

def pull_production_spc_reports():
    """Pull all SPC reports from production API"""
    try:
        url = "https://api.hailyai.com/api/spc/reports?limit=50000"  # Get all reports
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            reports = data.get('reports', [])
            logger.info(f"Pulled {len(reports)} SPC reports from production")
            return reports
        else:
            logger.warning(f"Failed to fetch SPC reports: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Failed to pull SPC reports: {e}")
        return []

def insert_alerts_to_dev(alerts):
    """Insert production alerts into development database"""
    if not alerts:
        return 0
    
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Clear existing alerts
            cursor.execute("DELETE FROM alerts;")
            logger.info("Cleared development alerts table")
            
            inserted_count = 0
            for alert in alerts:
                try:
                    # Insert alert with all fields
                    columns = []
                    values = []
                    
                    for key, value in alert.items():
                        if value is not None:
                            columns.append(key)
                            if isinstance(value, (dict, list)):
                                values.append(json.dumps(value))
                            else:
                                values.append(value)
                    
                    if columns:
                        placeholders = ['%s'] * len(columns)
                        insert_sql = f"""
                            INSERT INTO alerts ({', '.join(columns)}) 
                            VALUES ({', '.join(placeholders)});
                        """
                        cursor.execute(insert_sql, values)
                        inserted_count += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to insert alert {alert.get('id', 'unknown')}: {e}")
            
            conn.commit()
            logger.info(f"✅ Inserted {inserted_count} alerts into development")
            
        conn.close()
        return inserted_count
        
    except Exception as e:
        logger.error(f"Failed to insert alerts: {e}")
        return 0

def insert_spc_reports_to_dev(reports):
    """Insert production SPC reports into development database"""
    if not reports:
        return 0
    
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Clear existing SPC reports
            cursor.execute("DELETE FROM spc_reports;")
            logger.info("Cleared development spc_reports table")
            
            inserted_count = 0
            for report in reports:
                try:
                    # Insert SPC report with all fields
                    columns = []
                    values = []
                    
                    for key, value in report.items():
                        if value is not None:
                            columns.append(key)
                            if isinstance(value, (dict, list)):
                                values.append(json.dumps(value))
                            else:
                                values.append(value)
                    
                    if columns:
                        placeholders = ['%s'] * len(columns)
                        insert_sql = f"""
                            INSERT INTO spc_reports ({', '.join(columns)}) 
                            VALUES ({', '.join(placeholders)});
                        """
                        cursor.execute(insert_sql, values)
                        inserted_count += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to insert SPC report: {e}")
            
            conn.commit()
            logger.info(f"✅ Inserted {inserted_count} SPC reports into development")
            
        conn.close()
        return inserted_count
        
    except Exception as e:
        logger.error(f"Failed to insert SPC reports: {e}")
        return 0

def verify_development_sync():
    """Verify development now matches production"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Check alerts
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            alert_count = cursor.fetchone()[0]
            
            # Check SPC reports
            try:
                cursor.execute("SELECT COUNT(*) FROM spc_reports;")
                spc_count = cursor.fetchone()[0]
            except:
                spc_count = 0
            
            # Check target alert
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target_present = cursor.fetchone()[0]
            
        conn.close()
        
        logger.info("✅ Development database verification:")
        logger.info(f"  Alerts: {alert_count:,}")
        logger.info(f"  SPC Reports: {spc_count:,}")
        logger.info(f"  Target Alert: {'✅ Present' if target_present else '❌ Missing'}")
        
        return alert_count > 0
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

def main():
    """Sync complete production data to development"""
    logger.info("🔄 Syncing FROM production TO development")
    logger.info("Production: 95.98MB with 5,771 alerts + 46,088 SPC reports")
    logger.info("Development: 24.17MB with 9,547 alerts + 0 SPC reports")
    
    # Step 1: Pull alerts from production
    logger.info("Step 1: Pulling alerts from production...")
    alerts = pull_production_alerts()
    
    if not alerts:
        logger.error("No alerts pulled from production - API may be returning 0 results")
        logger.info("This confirms the production API disconnect issue")
        return False
    
    # Step 2: Pull SPC reports from production  
    logger.info("Step 2: Pulling SPC reports from production...")
    spc_reports = pull_production_spc_reports()
    
    # Step 3: Insert into development
    logger.info("Step 3: Inserting production data into development...")
    alert_count = insert_alerts_to_dev(alerts)
    spc_count = insert_spc_reports_to_dev(spc_reports)
    
    # Step 4: Verify
    logger.info("Step 4: Verifying sync...")
    if verify_development_sync():
        logger.info("🎉 Development now has complete production dataset")
        logger.info("Development can now be deployed to fix production API")
        return True
    else:
        logger.error("❌ Sync verification failed")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ Ready to deploy development (with complete data) to fix production")
    else:
        logger.info("❌ Production sync failed - production API disconnect confirmed")