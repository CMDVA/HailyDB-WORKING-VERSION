import logging
import requests
import re
import os
from datetime import datetime
from typing import Optional, Dict, List, Iterator
from models import Alert, IngestionLog
from config import Config

logger = logging.getLogger(__name__)

def chunks(data: List, chunk_size: int) -> Iterator[List]:
    """Utility function to chunk data into batches"""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

class IngestService:
    """
    NWS Alert Ingestion Service
    Handles polling, pagination, deduplication, and storage
    """
    
    def __init__(self, db):
        self.db = db
        self.config = Config()
        self.db_write_batch_size = int(os.getenv("DB_WRITE_BATCH_SIZE", "500"))
        
    def poll_nws_alerts(self) -> int:
        """
        Main ingestion method - polls NWS API and stores alerts
        Returns number of new alerts ingested
        """
        log_entry = IngestionLog()
        self.db.session.add(log_entry)
        self.db.session.commit()
        
        # Initialize error tracking
        self._failed_alerts = []
        start_time = datetime.utcnow()
        http_status = None
        api_response_size = 0
        duplicate_count = 0
        
        try:
            logger.info("Starting NWS alert ingestion")
            
            total_processed = 0
            new_alerts = 0
            updated_alerts = 0
            alerts_to_process = []  # Collect alerts for batch processing
            
            url = self.config.NWS_ALERT_URL
            
            # Step 1: Collect all alerts from all pages (no processing limits)
            while url:
                logger.debug(f"Polling URL: {url}")
                
                try:
                    response = requests.get(url, headers=self.config.NWS_HEADERS, timeout=30)
                    response.raise_for_status()
                    http_status = response.status_code
                    
                    data = response.json()
                    api_response_size += len(response.content)
                    features = data.get('features', [])
                    
                    logger.info(f"Retrieved {len(features)} alerts from current page")
                    alerts_to_process.extend(features)
                    
                    # Handle pagination
                    pagination = data.get('pagination', {})
                    url = pagination.get('next')
                    
                    if url:
                        logger.debug(f"Following pagination to: {url}")
                    
                except requests.RequestException as e:
                    logger.error(f"HTTP error during ingestion: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error during page processing: {e}")
                    break
            
            logger.info(f"Collected {len(alerts_to_process)} total alerts for processing")
            
            # Step 2: Process alerts in configurable batches for database writes
            for batch in chunks(alerts_to_process, self.db_write_batch_size):
                logger.debug(f"Processing batch of {len(batch)} alerts")
                
                for feature in batch:
                    try:
                        result = self._process_alert_feature(feature)
                        total_processed += 1
                        
                        if result == 'new':
                            new_alerts += 1
                        elif result == 'updated':
                            updated_alerts += 1
                        elif result == 'skipped' and hasattr(self, '_failed_alerts') and self._failed_alerts:
                            # Check if last error was a duplicate
                            last_error = self._failed_alerts[-1] if self._failed_alerts else {}
                            if 'duplicate' in last_error.get('error', '').lower():
                                duplicate_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing alert feature: {e}")
                        continue
                
                # Commit this batch
                try:
                    self.db.session.commit()
                    logger.debug(f"Committed batch of {len(batch)} alerts")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    self.db.session.rollback()
                    continue
            
            # Calculate processing duration
            processing_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Update log entry with comprehensive details
            log_entry.completed_at = datetime.utcnow()
            log_entry.success = True
            log_entry.alerts_processed = total_processed
            log_entry.new_alerts = new_alerts
            log_entry.updated_alerts = updated_alerts
            self.db.session.commit()
            
            logger.info(f"Ingestion complete: {new_alerts} new, {updated_alerts} updated, {total_processed} total, {duplicate_count} duplicates, {len(self._failed_alerts)} failed")
            return {
                'new_alerts': new_alerts,
                'updated_alerts': updated_alerts,
                'total_processed': total_processed,
                'duplicate_count': duplicate_count,
                'failed_count': len(self._failed_alerts)
            }
            
        except Exception as e:
            logger.error(f"Fatal error during ingestion: {e}")
            
            # Calculate processing duration
            processing_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Update log entry with comprehensive error details
            log_entry.completed_at = datetime.utcnow()
            log_entry.success = False
            log_entry.error_message = str(e)
            self.db.session.commit()
            
            raise
    
    def _process_alert_feature(self, feature: Dict) -> str:
        """
        Process a single alert feature from NWS API
        Returns 'new', 'updated', or 'skipped'
        """
        try:
            properties = feature.get('properties', {})
            alert_id = properties.get('id')
            
            if not alert_id:
                logger.warning("Alert feature missing ID, skipping")
                return 'skipped'
            
            # Check if alert already exists using a separate query to avoid session conflicts
            existing_alert = self.db.session.query(Alert).filter_by(id=alert_id).first()
            
            if existing_alert:
                # Update existing alert
                self._update_alert(existing_alert, feature)
                logger.debug(f"Updated existing alert: {alert_id}")
                return 'updated'
            else:
                # Create new alert with duplicate protection
                try:
                    self._create_alert(feature)
                    logger.debug(f"Created new alert: {alert_id}")
                    return 'new'
                except Exception as create_error:
                    # Check if this is a duplicate key error
                    if "duplicate key value violates unique constraint" in str(create_error):
                        logger.warning(f"Duplicate alert detected during creation: {alert_id}")
                        # Rollback and try to update instead
                        self.db.session.rollback()
                        existing_alert = self.db.session.query(Alert).filter_by(id=alert_id).first()
                        if existing_alert:
                            self._update_alert(existing_alert, feature)
                            return 'updated'
                        else:
                            logger.error(f"Failed to handle duplicate for {alert_id}")
                            return 'skipped'
                    else:
                        raise create_error
                
        except Exception as e:
            logger.error(f"Error processing alert feature {alert_id}: {e}")
            # Record failed alert ID for detailed logging
            if not hasattr(self, '_failed_alerts'):
                self._failed_alerts = []
            self._failed_alerts.append({
                'alert_id': alert_id,
                'error': str(e),
                'event_type': properties.get('event', 'Unknown')
            })
            return 'skipped'
    
    def _create_alert(self, feature: Dict) -> Alert:
        """Create new alert from NWS feature"""
        properties = feature.get('properties', {})
        
        alert = Alert(
            id=properties.get('id'),
            event=properties.get('event'),
            severity=properties.get('severity'),
            area_desc=properties.get('areaDesc'),
            effective=self._parse_datetime(properties.get('effective')),
            expires=self._parse_datetime(properties.get('expires')),
            sent=self._parse_datetime(properties.get('sent')),
            geometry=feature.get('geometry'),
            properties=properties,
            raw=feature,
            radar_indicated=self._parse_radar_indicated(properties)
        )
        
        # Process full geometry for Feature 3: Full Geometry & County Mapping
        alert.process_full_geometry()
        
        self.db.session.add(alert)
        return alert
    
    def _update_alert(self, alert: Alert, feature: Dict) -> Alert:
        """Update existing alert with new data"""
        properties = feature.get('properties', {})
        
        # Update fields that might change
        alert.event = properties.get('event')
        alert.severity = properties.get('severity')
        alert.area_desc = properties.get('areaDesc')
        alert.effective = self._parse_datetime(properties.get('effective'))
        alert.expires = self._parse_datetime(properties.get('expires'))
        alert.sent = self._parse_datetime(properties.get('sent'))
        alert.geometry = feature.get('geometry')
        alert.properties = properties
        alert.raw = feature
        alert.radar_indicated = self._parse_radar_indicated(properties)
        
        # Process full geometry for Feature 3: Full Geometry & County Mapping
        alert.process_full_geometry()
        
        return alert
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string from NWS API"""
        if not dt_string:
            return None
        
        try:
            # Handle various ISO formats
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except ValueError as e:
            logger.warning(f"Could not parse datetime '{dt_string}': {e}")
            return None
    
    def get_ingestion_stats(self) -> Dict:
        """Get ingestion statistics"""
        recent_logs = IngestionLog.query.order_by(
            IngestionLog.started_at.desc()
        ).limit(10).all()
        
        successful_runs = sum(1 for log in recent_logs if log.success)
        total_runs = len(recent_logs)
        
        latest_log = recent_logs[0] if recent_logs else None
        
        return {
            'recent_success_rate': successful_runs / total_runs if total_runs > 0 else 0,
            'total_recent_runs': total_runs,
            'latest_run': {
                'started_at': latest_log.started_at.isoformat() if latest_log else None,
                'success': latest_log.success if latest_log else None,
                'new_alerts': latest_log.new_alerts if latest_log else 0,
                'alerts_processed': latest_log.alerts_processed if latest_log else 0
            } if latest_log else None
        }
    
    def _parse_radar_indicated(self, properties: Dict) -> Optional[Dict]:
        """
        Parse radar-indicated hail and wind data from Severe Thunderstorm Warning
        Returns {"hail_inches": float, "wind_mph": int} or None if not a STW or no data found
        """
        event = properties.get('event', '')
        
        # Only process Severe Thunderstorm Warnings
        if 'Severe Thunderstorm Warning' not in event:
            return None
        
        try:
            # Get text fields to search
            text_fields = []
            if properties.get('headline'):
                text_fields.append(properties['headline'])
            if properties.get('description'):
                text_fields.append(properties['description'])
            if properties.get('instruction'):
                text_fields.append(properties['instruction'])
            
            combined_text = ' '.join(text_fields).lower()
            
            if not combined_text.strip():
                return None
                
            radar_data = {}
            
            # Parse hail size
            hail_inches = self._extract_hail_size(combined_text)
            if hail_inches is not None:
                radar_data['hail_inches'] = hail_inches
            
            # Parse wind speed
            wind_mph = self._extract_wind_speed(combined_text)
            if wind_mph is not None:
                radar_data['wind_mph'] = wind_mph
            
            return radar_data if radar_data else None
            
        except Exception as e:
            logger.error(f"Error parsing radar indicated data: {e}")
            return None
    
    def _extract_hail_size(self, text: str) -> Optional[float]:
        """Extract hail size in inches from text"""
        try:
            # Size conversion mapping based on official NWS hail size chart
            size_map = {
                'pea': 0.25,
                'peanut': 0.5,
                'penny': 0.75,
                'nickel': 0.88,
                'quarter': 1.0,
                'half dollar': 1.25,
                'ping pong ball': 1.5,
                'golf ball': 1.75,
                'egg': 2.0,
                'tennis ball': 2.5,
                'baseball': 2.75,
                'large apple': 3.0,
                'softball': 4.0,
                'grapefruit': 4.5
            }
            
            # Pattern 1: "hail up to X inch" or "hail up to X inches"
            pattern1 = r'hail up to (\d+(?:\.\d+)?)\s*inch'
            match = re.search(pattern1, text)
            if match:
                return float(match.group(1))
            
            # Pattern 2: "hail size of X inch" or "X inch hail"
            pattern2 = r'(?:hail size of |)(\d+(?:\.\d+)?)\s*inch'
            match = re.search(pattern2, text)
            if match:
                return float(match.group(1))
            
            # Pattern 3: Named sizes (quarter size hail, golf ball hail, etc.)
            # Use word boundaries to avoid partial matches
            for size_name, inches in size_map.items():
                # Create pattern with word boundaries for exact matches
                pattern = r'\b' + re.escape(size_name) + r'\b.*hail|\bhail.*\b' + re.escape(size_name) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    return inches
            
            # Pattern 4: "X inch diameter hail"
            pattern4 = r'(\d+(?:\.\d+)?)\s*inch diameter hail'
            match = re.search(pattern4, text)
            if match:
                return float(match.group(1))
                
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting hail size: {e}")
            return None
    
    def _extract_wind_speed(self, text: str) -> Optional[int]:
        """Extract wind speed in mph from text"""
        try:
            # Pattern 1: "winds up to X mph"
            pattern1 = r'winds up to (\d+)\s*mph'
            match = re.search(pattern1, text)
            if match:
                return int(match.group(1))
            
            # Pattern 2: "damaging winds of X mph"
            pattern2 = r'damaging winds of (\d+)\s*mph'
            match = re.search(pattern2, text)
            if match:
                return int(match.group(1))
            
            # Pattern 3: "X mph wind gusts"
            pattern3 = r'(\d+)\s*mph wind gusts'
            match = re.search(pattern3, text)
            if match:
                return int(match.group(1))
            
            # Pattern 4: "wind gusts to X mph"
            pattern4 = r'wind gusts to (\d+)\s*mph'
            match = re.search(pattern4, text)
            if match:
                return int(match.group(1))
            
            # Pattern 5: "winds of X mph"
            pattern5 = r'winds of (\d+)\s*mph'
            match = re.search(pattern5, text)
            if match:
                return int(match.group(1))
                
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting wind speed: {e}")
            return None
