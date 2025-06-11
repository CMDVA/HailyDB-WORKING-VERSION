"""
Historical NWS Alert Data Ingestion for HailyDB
Retrieves historical severe weather alerts from archive sources
"""

import logging
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import and_

from app import db
from models import Alert, IngestionLog

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalDataIngester:
    """
    Ingests historical NWS alert data from archive sources
    """
    
    def __init__(self):
        self.processed_count = 0
        self.new_count = 0
        self.updated_count = 0
        self.failed_count = 0
        self.errors = []
        
    def check_available_sources(self) -> Dict[str, Any]:
        """
        Check what historical data sources are available
        """
        sources = {
            'nws_cap_archive': {
                'description': 'NWS Common Alerting Protocol Archive',
                'url_template': 'https://alerts.weather.gov/cap/archives/{year}/{month:02d}/{day:02d}/',
                'coverage': '2010-present',
                'format': 'CAP XML',
                'available': False
            },
            'iowa_mesonet': {
                'description': 'Iowa Environmental Mesonet Archive',
                'url_template': 'https://mesonet.agron.iastate.edu/request/gis/watchwarn.phtml',
                'coverage': '2005-present', 
                'format': 'Shapefile/GeoJSON',
                'available': False
            },
            'ncdc_storm_events': {
                'description': 'NCDC Storm Events Database',
                'url_template': 'https://www.ncdc.noaa.gov/stormevents/ftp.jsp',
                'coverage': '1950-present',
                'format': 'CSV',
                'available': False
            }
        }
        
        # Test Iowa Environmental Mesonet availability
        try:
            response = requests.head('https://mesonet.agron.iastate.edu/request/gis/watchwarn.phtml', timeout=10)
            if response.status_code == 200:
                sources['iowa_mesonet']['available'] = True
                logger.info("Iowa Environmental Mesonet archive is accessible")
        except Exception as e:
            logger.warning(f"Iowa Environmental Mesonet not accessible: {e}")
            
        # Test NWS CAP Archive availability  
        try:
            test_url = 'https://alerts.weather.gov/cap/archives/2024/06/01/'
            response = requests.head(test_url, timeout=10)
            if response.status_code == 200:
                sources['nws_cap_archive']['available'] = True
                logger.info("NWS CAP Archive is accessible")
        except Exception as e:
            logger.warning(f"NWS CAP Archive not accessible: {e}")
            
        return sources
    
    def ingest_iowa_mesonet_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Ingest historical alert data from Iowa Environmental Mesonet
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Processing statistics
        """
        logger.info(f"Starting Iowa Mesonet historical data ingest from {start_date} to {end_date}")
        
        # Iowa Mesonet parameters for severe weather warnings
        params = {
            'year1': start_date[:4],
            'month1': start_date[5:7], 
            'day1': start_date[8:10],
            'year2': end_date[:4],
            'month2': end_date[5:7],
            'day2': end_date[8:10],
            'phenomena[]': ['SV'],  # Severe Thunderstorm
            'lsrtype[]': ['ALL'],
            'format': 'geojson',
            'limit': '10000'
        }
        
        try:
            response = requests.get(
                'https://mesonet.agron.iastate.edu/request/gis/watchwarn.phtml',
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
            data = response.json()
            
            if 'features' not in data:
                logger.warning("No features found in Iowa Mesonet response")
                return self._get_stats()
                
            logger.info(f"Retrieved {len(data['features'])} historical alerts from Iowa Mesonet")
            
            # Process each alert
            for feature in data['features']:
                try:
                    self._process_iowa_mesonet_alert(feature)
                    self.processed_count += 1
                    
                    if self.processed_count % 100 == 0:
                        logger.info(f"Processed {self.processed_count} historical alerts")
                        
                except Exception as e:
                    self.failed_count += 1
                    error_msg = f"Failed to process alert: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    
            # Commit changes
            db.session.commit()
            logger.info(f"Historical data ingest complete: {self.new_count} new, {self.updated_count} updated")
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Iowa Mesonet ingest failed: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
        return self._get_stats()
    
    def _process_iowa_mesonet_alert(self, feature: Dict[str, Any]):
        """Process a single alert from Iowa Mesonet format"""
        properties = feature.get('properties', {})
        geometry = feature.get('geometry')
        
        # Extract alert metadata
        phenomena = properties.get('phenomena')
        if phenomena != 'SV':  # Only process Severe Thunderstorm warnings
            return
            
        # Generate alert ID from Iowa Mesonet data
        issued_time = properties.get('issue')
        expired_time = properties.get('expire') 
        polygon_hash = str(hash(str(geometry))) if geometry else 'no-geo'
        alert_id = f"iem-{phenomena}-{issued_time}-{polygon_hash}"
        
        # Check if alert already exists
        existing = db.session.query(Alert).filter_by(id=alert_id).first()
        
        if existing:
            # Update existing alert
            self._update_alert_from_iowa_mesonet(existing, feature)
            self.updated_count += 1
        else:
            # Create new alert
            alert = self._create_alert_from_iowa_mesonet(feature, alert_id)
            if alert:
                db.session.add(alert)
                self.new_count += 1
    
    def _create_alert_from_iowa_mesonet(self, feature: Dict[str, Any], alert_id: str) -> Optional[Alert]:
        """Create new Alert from Iowa Mesonet data"""
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry')
            
            # Parse timestamps
            issued_str = properties.get('issue')
            expired_str = properties.get('expire')
            
            issued_dt = self._parse_iowa_timestamp(issued_str) if issued_str else None
            expired_dt = self._parse_iowa_timestamp(expired_str) if expired_str else None
            
            # Build alert object
            alert = Alert(
                id=alert_id,
                event='Severe Thunderstorm Warning',
                headline=f"Severe Thunderstorm Warning issued by {properties.get('wfo', 'NWS')}",
                description=f"Historical severe thunderstorm warning from {issued_str}",
                instruction=properties.get('text', ''),
                area_desc=properties.get('text', ''),
                urgency='Immediate',
                severity='Severe', 
                certainty='Observed',
                effective=issued_dt,
                expires=expired_dt,
                sent=issued_dt,
                status='Past',
                msg_type='Alert',
                category='Met',
                geometry=json.dumps(geometry) if geometry else None,
                raw=json.dumps(feature)
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert from Iowa Mesonet data: {e}")
            return None
    
    def _update_alert_from_iowa_mesonet(self, alert: Alert, feature: Dict[str, Any]):
        """Update existing alert with Iowa Mesonet data"""
        properties = feature.get('properties', {})
        
        # Update description with Iowa Mesonet source info
        if not alert.description or 'Iowa Mesonet' not in alert.description:
            alert.description = f"{alert.description or ''}\n[Source: Iowa Environmental Mesonet Archive]"
            
        # Update raw data
        alert.raw = json.dumps(feature)
    
    def _parse_iowa_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse Iowa Mesonet timestamp format"""
        try:
            # Iowa Mesonet uses format: 2024-06-01T12:34:00Z
            if 'T' in timestamp_str and timestamp_str.endswith('Z'):
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
            elif 'T' in timestamp_str:
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
            else:
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
            return None
    
    def _get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processed': self.processed_count,
            'new_alerts': self.new_count,
            'updated_alerts': self.updated_count,
            'failed': self.failed_count,
            'errors': self.errors
        }


def check_historical_data_sources() -> Dict[str, Any]:
    """Check what historical data sources are available"""
    ingester = HistoricalDataIngester()
    return ingester.check_available_sources()


def ingest_historical_data(start_date: str, end_date: str, source: str = 'iowa_mesonet') -> Dict[str, Any]:
    """
    Ingest historical severe weather alert data
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD) 
        source: Data source ('iowa_mesonet', 'nws_cap_archive')
        
    Returns:
        Processing statistics
    """
    ingester = HistoricalDataIngester()
    
    if source == 'iowa_mesonet':
        return ingester.ingest_iowa_mesonet_data(start_date, end_date)
    else:
        raise ValueError(f"Unsupported data source: {source}")


if __name__ == "__main__":
    # Test historical data ingestion
    sources = check_historical_data_sources()
    print("Available historical data sources:")
    for name, info in sources.items():
        status = "✓ Available" if info['available'] else "✗ Not accessible"
        print(f"  {name}: {info['description']} - {status}")