"""
Historical Radar Parser for HailyDB
Retroactively applies radar parsing to historical severe thunderstorm warnings
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_

from app import db
from models import Alert

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalRadarParser:
    """
    Applies radar parsing logic to historical severe thunderstorm warnings
    that lack radar_indicated data
    """
    
    def __init__(self):
        self.processed_count = 0
        self.updated_count = 0
        self.failed_count = 0
        self.errors = []
    
    def parse_historical_range(self, start_date: str, end_date: str, batch_size: int = 100) -> Dict[str, Any]:
        """
        Parse radar data for historical alerts in date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD) 
            batch_size: Number of alerts to process per batch
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting historical radar parsing from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        
        # Find alerts without radar data that might contain radar parameters
        alerts_query = db.session.query(Alert).filter(
            and_(
                Alert.effective >= start_dt,
                Alert.effective <= end_dt,
                Alert.radar_indicated.is_(None),
                # Check for alerts that might have radar parameters
                db.or_(
                    Alert.properties['parameters']['maxHailSize'].astext.isnot(None),
                    Alert.properties['parameters']['maxWindGust'].astext.isnot(None),
                    Alert.event == 'Severe Thunderstorm Warning',
                    Alert.event == 'Special Weather Statement'
                )
            )
        )
        
        total_alerts = alerts_query.count()
        logger.info(f"Found {total_alerts} alerts needing radar parsing (includes Severe Thunderstorm Warnings and Special Weather Statements)")
        
        # Process in batches
        offset = 0
        while offset < total_alerts:
            batch_alerts = alerts_query.offset(offset).limit(batch_size).all()
            if not batch_alerts:
                break
                
            self._process_batch(batch_alerts)
            offset += batch_size
            
            logger.info(f"Processed {min(offset, total_alerts)}/{total_alerts} alerts")
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Historical radar parsing complete: {self.updated_count} alerts updated")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit radar parsing updates: {e}")
            self.errors.append(f"Commit failed: {e}")
        
        return {
            'total_found': total_alerts,
            'processed': self.processed_count,
            'updated': self.updated_count,
            'failed': self.failed_count,
            'errors': self.errors
        }
    
    def _process_batch(self, alerts):
        """Process a batch of alerts for radar parsing"""
        for alert in alerts:
            try:
                self.processed_count += 1
                radar_data = self._extract_radar_data(alert)
                
                if radar_data:
                    # Convert to JSON string format to match existing data structure
                    import json
                    alert.radar_indicated = json.dumps(radar_data)
                    self.updated_count += 1
                    logger.debug(f"Updated alert {alert.id} with radar data: {radar_data}")
                
            except Exception as e:
                self.failed_count += 1
                error_msg = f"Failed to process alert {alert.id}: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _extract_radar_data(self, alert: Alert) -> Optional[Dict[str, Any]]:
        """
        Extract radar-indicated hail and wind data from alert text
        
        Args:
            alert: Alert object to parse
            
        Returns:
            Dictionary with radar data or None if no data found
        """
        try:
            # Get text fields to search - check both direct attributes and raw data
            text_fields = []
            
            # Try direct attributes first
            if hasattr(alert, 'headline') and alert.headline:
                text_fields.append(alert.headline)
            if hasattr(alert, 'description') and alert.description:
                text_fields.append(alert.description)
            if hasattr(alert, 'instruction') and alert.instruction:
                text_fields.append(alert.instruction)
            
            # If no direct attributes, try raw data
            if not text_fields and hasattr(alert, 'raw') and alert.raw:
                raw_data = alert.raw
                if isinstance(raw_data, dict):
                    properties = raw_data.get('properties', {})
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
            logger.error(f"Error parsing radar data for alert {alert.id}: {e}")
            return None
    
    def _extract_hail_size(self, text: str) -> Optional[float]:
        """Extract hail size in inches from text"""
        try:
            # Common radar-indicated hail patterns
            patterns = [
                r'radar.*?indicated.*?hail.*?(\d+(?:\.\d+)?)\s*(?:inch|in|")',
                r'radar.*?(?:showing|indicating).*?hail.*?(\d+(?:\.\d+)?)\s*(?:inch|in|")',
                r'doppler\s+radar.*?hail.*?(\d+(?:\.\d+)?)\s*(?:inch|in|")',
                r'hail.*?(\d+(?:\.\d+)?)\s*(?:inch|in|").*?radar',
                r'quarter\s+size.*hail',  # 1.0 inch
                r'golf\s+ball.*hail',     # 1.75 inch  
                r'ping\s+pong.*hail',     # 1.5 inch
                r'tennis\s+ball.*hail',   # 2.5 inch
                r'baseball.*hail',        # 2.75 inch
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match.groups():
                        try:
                            size = float(match.group(1))
                            if 0.25 <= size <= 6.0:  # Reasonable hail size range
                                return size
                        except (ValueError, IndexError):
                            continue
            
            # Size descriptors to inches mapping
            size_descriptors = {
                'quarter': 1.0,
                'half dollar': 1.25,
                'ping pong': 1.5,
                'golf ball': 1.75,
                'tennis ball': 2.5,
                'baseball': 2.75,
                'softball': 4.0
            }
            
            for descriptor, size in size_descriptors.items():
                if descriptor in text and 'hail' in text:
                    return size
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting hail size: {e}")
            return None
    
    def _extract_wind_speed(self, text: str) -> Optional[int]:
        """Extract wind speed in mph from text"""
        try:
            # Wind speed patterns
            patterns = [
                r'radar.*?indicated.*?winds.*?(\d+)\s*(?:mph|knots?)',
                r'radar.*?(?:showing|indicating).*?winds.*?(\d+)\s*(?:mph|knots?)',
                r'doppler\s+radar.*?winds.*?(\d+)\s*(?:mph|knots?)',
                r'winds.*?(\d+)\s*(?:mph|knots?).*?radar',
                r'wind\s+gusts?.*?(\d+)\s*(?:mph|knots?)',
                r'damaging\s+winds.*?(\d+)\s*(?:mph|knots?)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        speed = int(match.group(1))
                        # Convert knots to mph if needed
                        if 'knot' in match.group(0).lower():
                            speed = int(speed * 1.15078)  # knots to mph conversion
                        
                        if 50 <= speed <= 200:  # Reasonable wind speed range
                            return speed
                    except (ValueError, IndexError):
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting wind speed: {e}")
            return None


def parse_historical_radar_data(start_date: str, end_date: str, batch_size: int = 100) -> Dict[str, Any]:
    """
    Main function to parse historical radar data
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        batch_size: Batch size for processing
        
    Returns:
        Processing statistics
    """
    parser = HistoricalRadarParser()
    return parser.parse_historical_range(start_date, end_date, batch_size)


if __name__ == "__main__":
    # Parse June 2-9 historical data
    result = parse_historical_radar_data("2025-06-02", "2025-06-09")
    print(f"Historical radar parsing results: {result}")