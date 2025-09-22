#!/usr/bin/env python3
"""
REAL Florida Pilot Backfill - Process actual historical CSV data from IEM
This will ingest real 2024 NWS alerts into the database
"""
import sys
import logging
import requests
import zipfile
import tempfile
import csv
from datetime import datetime
from io import BytesIO

sys.path.append('.')

from app import app, db
from scheduler_service import SchedulerService
from models import Alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealIemBackfill:
    """Real backfill service using CSV data from IEM"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.scheduler_service = SchedulerService(db_session)
        self.base_url = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/watchwarn.py"
        self.headers = {
            'User-Agent': 'HailyDB-Real-Backfill/1.0 (contact@hailydb.com)',
            'Accept': 'application/zip'
        }
    
    def get_florida_url(self, start_date: str, end_date: str) -> str:
        """Build IEM URL for Florida historical data"""
        params = {
            'location_group': 'states',
            'states': 'FL',
            'sts': f'{start_date}T00:00Z',
            'ets': f'{end_date}T23:59Z',
            'accept': 'shapefile',
            'limit1': 'yes',
            'limitps': 'yes'
        }
        
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?{param_str}"
    
    def download_and_parse_csv(self, url: str):
        """Download IEM ZIP and extract CSV data"""
        try:
            logger.info(f"Downloading historical data from: {url}")
            response = requests.get(url, headers=self.headers, timeout=60)
            response.raise_for_status()
            
            logger.info(f"Downloaded {len(response.content)} bytes")
            
            # Extract CSV from ZIP
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                csv_files = [f for f in zip_file.filelist if f.filename.endswith('.csv')]
                
                if not csv_files:
                    logger.error("No CSV file found in ZIP")
                    return []
                
                csv_filename = csv_files[0].filename
                logger.info(f"Found CSV file: {csv_filename}")
                
                # Read CSV content
                with zip_file.open(csv_filename) as csv_file:
                    csv_content = csv_file.read().decode('utf-8')
                    
                # Parse CSV
                alerts = []
                csv_reader = csv.DictReader(csv_content.splitlines())
                
                for row in csv_reader:
                    try:
                        # Convert to our alert format
                        alert_data = self.convert_csv_to_alert(row)
                        if alert_data:
                            alerts.append(alert_data)
                    except Exception as e:
                        logger.warning(f"Error processing CSV row: {e}")
                        continue
                
                logger.info(f"Parsed {len(alerts)} alerts from CSV")
                return alerts
                
        except Exception as e:
            logger.error(f"Error downloading/parsing data: {e}")
            return []
    
    def convert_csv_to_alert(self, row):
        """Convert CSV row to Alert model format"""
        try:
            # Build alert data from CSV columns
            # IEM CSV typically has columns like: ISSUED, EXPIRED, EVENT, SIGNIFICANCE, etc.
            
            alert_data = {
                'id': row.get('VTEC_PS_ID', f"IEM_{row.get('ISSUED', '')}_{row.get('EVENT', '')}").replace(' ', '_'),
                'event': row.get('EVENT', ''),
                'headline': row.get('HEADLINE', ''),
                'description': row.get('DESCRIPTION', ''),
                'severity': row.get('SEVERITY', ''),
                'certainty': row.get('CERTAINTY', ''),
                'urgency': row.get('URGENCY', ''),
                'areas': row.get('AREAS', ''),
                'status': 'Actual',
                'message_type': 'Alert',
                'category': 'Met',
                'sender': row.get('WFO', 'IEM-Historical'),
                'data_source': 'IEM-Historical',
                'vtec_key': row.get('VTEC_PS_ID', ''),
                'properties_data': row  # Store full CSV row
            }
            
            # Parse dates
            for date_field in ['sent', 'effective', 'expires']:
                csv_date_field = date_field.upper() if date_field != 'sent' else 'ISSUED'
                date_str = row.get(csv_date_field, '')
                if date_str:
                    try:
                        # Try different date formats
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M']:
                            try:
                                alert_data[date_field] = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        pass
            
            return alert_data
            
        except Exception as e:
            logger.error(f"Error converting CSV row: {e}")
            return None
    
    def upsert_alert(self, alert_data):
        """Insert or update alert in database"""
        try:
            existing = Alert.query.filter_by(id=alert_data['id']).first()
            
            if existing:
                # Update existing
                for key, value in alert_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                db.session.commit()
                return 'updated'
            else:
                # Create new
                new_alert = Alert()
                for key, value in alert_data.items():
                    if hasattr(new_alert, key):
                        setattr(new_alert, key, value)
                
                db.session.add(new_alert)
                db.session.commit()
                return 'inserted'
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error upserting alert: {e}")
            return 'error'
    
    def process_month(self, year: int, month: int):
        """Process real historical data for a month"""
        logger.info(f"Processing REAL historical data for {year}-{month:02d}")
        
        # Start SchedulerService logging
        log_entry = self.scheduler_service.log_operation_start(
            operation_type='iem_backfill',
            trigger_method='manual',
            metadata={
                'year': year,
                'month': month,
                'state': 'FL',
                'source': 'IEM-Historical-CSV',
                'operation_type': 'real_historical_backfill'
            }
        )
        
        # Build date range
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        stats = {
            'records_processed': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'errors': []
        }
        
        try:
            # Get historical data
            url = self.get_florida_url(start_date, end_date)
            alerts = self.download_and_parse_csv(url)
            
            if not alerts:
                logger.warning(f"No historical alerts found for {year}-{month:02d}")
                self.scheduler_service.log_operation_complete(
                    log_entry, success=True, records_processed=0, records_new=0
                )
                return stats
            
            stats['records_processed'] = len(alerts)
            logger.info(f"Processing {len(alerts)} real historical alerts...")
            
            # Insert alerts
            inserted = 0
            updated = 0
            
            for alert_data in alerts:
                result = self.upsert_alert(alert_data)
                if result == 'inserted':
                    inserted += 1
                elif result == 'updated':
                    updated += 1
                elif result == 'error':
                    stats['errors'].append(f"Failed to upsert alert {alert_data.get('id')}")
            
            stats['records_inserted'] = inserted
            stats['records_updated'] = updated
            
            # Log completion
            self.scheduler_service.log_operation_complete(
                log_entry,
                success=True,
                records_processed=len(alerts),
                records_new=inserted
            )
            
            logger.info(f"✅ Completed {year}-{month:02d}: {inserted} inserted, {updated} updated")
            
        except Exception as e:
            error_msg = f"Error processing {year}-{month:02d}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            self.scheduler_service.log_operation_complete(
                log_entry, success=False, error_message=error_msg
            )
        
        return stats

def main():
    """Execute REAL Florida pilot backfill"""
    logger.info("=== REAL FLORIDA PILOT BACKFILL ===")
    logger.info("Processing actual historical 2024 NWS alerts from IEM")
    
    with app.app_context():
        service = RealIemBackfill(db)
        
        # Process September 2024 (we know it has 65 records)
        month_stats = service.process_month(2024, 9)
        
        logger.info("=== REAL BACKFILL RESULTS ===")
        logger.info(f"Records processed: {month_stats['records_processed']}")
        logger.info(f"New 2024 alerts inserted: {month_stats['records_inserted']}")
        logger.info(f"Alerts updated: {month_stats['records_updated']}")
        
        if month_stats['errors']:
            logger.error(f"Errors: {month_stats['errors']}")
        
        return month_stats['records_inserted'] > 0

if __name__ == '__main__':
    success = main()