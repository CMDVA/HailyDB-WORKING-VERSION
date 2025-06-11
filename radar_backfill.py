"""
Radar Alerts Backfill System
Processes historical NWS radar-detected events into structured radar_alerts table
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app import db
from models import Alert, RadarAlert
from city_parser import CityNameParser

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RadarBackfillProcessor:
    """
    Processes radar-detected alerts into structured radar_alerts table
    """
    
    def __init__(self):
        self.city_parser = CityNameParser()
        
    def process_date_range(self, start_date: str, end_date: str, batch_size: int = 100) -> Dict[str, Any]:
        """
        Process radar-detected alerts for a specific date range
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
            batch_size: Number of alerts to process per batch
            
        Returns:
            Processing statistics
        """
        logger.info(f"Starting radar backfill from {start_date} to {end_date}")
        
        stats = {
            'total_alerts_found': 0,
            'hail_events_created': 0,
            'wind_events_created': 0,
            'failed_processing': 0,
            'skipped_existing': 0,
            'processing_errors': []
        }
        
        with db.session.begin():
            # Find all radar-detected alerts in date range
            query = db.session.query(Alert).filter(
                Alert.radar_indicated.isnot(None),
                Alert.effective >= start_date,
                Alert.effective <= end_date
            ).order_by(Alert.effective)
            
            total_alerts = query.count()
            stats['total_alerts_found'] = total_alerts
            logger.info(f"Found {total_alerts} radar-detected alerts in date range")
            
            # Process in batches
            processed = 0
            for offset in range(0, total_alerts, batch_size):
                batch_alerts = query.offset(offset).limit(batch_size).all()
                
                for alert in batch_alerts:
                    try:
                        batch_stats = self._process_single_alert(alert)
                        stats['hail_events_created'] += batch_stats.get('hail_events', 0)
                        stats['wind_events_created'] += batch_stats.get('wind_events', 0)
                        stats['skipped_existing'] += batch_stats.get('skipped', 0)
                        
                        processed += 1
                        if processed % 50 == 0:
                            logger.info(f"Processed {processed}/{total_alerts} alerts")
                            
                    except Exception as e:
                        stats['failed_processing'] += 1
                        error_msg = f"Failed to process alert {alert.id}: {str(e)}"
                        stats['processing_errors'].append(error_msg)
                        logger.error(error_msg)
                        
                # Commit batch
                db.session.commit()
                
        logger.info(f"Backfill complete. Created {stats['hail_events_created']} hail events, {stats['wind_events_created']} wind events")
        return stats
    
    def _process_single_alert(self, alert: Alert) -> Dict[str, int]:
        """
        Process a single radar-detected alert into radar_alerts table
        """
        stats = {'hail_events': 0, 'wind_events': 0, 'skipped': 0}
        
        radar_data = alert.radar_indicated
        if not radar_data:
            return stats
            
        # Check if already processed
        existing = db.session.query(RadarAlert).filter_by(alert_id=alert.id).first()
        if existing:
            stats['skipped'] = 1
            return stats
            
        # Extract radar measurements
        hail_inches = self._extract_float(radar_data.get('hail_inches'))
        wind_mph = self._extract_int(radar_data.get('wind_mph'))
        
        # Filter by criteria: all hail events, wind >= 50 mph
        create_hail_event = hail_inches is not None and hail_inches > 0
        create_wind_event = wind_mph is not None and wind_mph >= 50
        
        if not (create_hail_event or create_wind_event):
            return stats
            
        # Parse geographic data
        city_names = self._parse_city_names(alert.area_desc)
        county_names = self._extract_counties(alert.county_names)
        fips_codes = self._extract_fips(alert.fips_codes)
        affected_states = self._extract_states(alert.affected_states)
        
        # Extract event details
        event_date = alert.effective.date() if alert.effective else date.today()
        detected_time = alert.effective or datetime.utcnow()
        
        # Create radar alert events
        if create_hail_event:
            radar_alert = RadarAlert(
                alert_id=alert.id,
                event_type='hail',
                event_date=event_date,
                detected_time=detected_time,
                hail_inches=hail_inches,
                wind_mph=None,
                city_names=city_names,
                county_names=county_names,
                fips_codes=fips_codes,
                affected_states=affected_states,
                geometry=alert.geometry,
                geometry_bounds=alert.geometry_bounds
            )
            db.session.add(radar_alert)
            stats['hail_events'] = 1
            
        if create_wind_event and create_hail_event:
            # Create separate wind event if both hail and wind present
            radar_alert = RadarAlert(
                alert_id=alert.id,
                event_type='wind',
                event_date=event_date,
                detected_time=detected_time,
                hail_inches=None,
                wind_mph=wind_mph,
                city_names=city_names,
                county_names=county_names,
                fips_codes=fips_codes,
                affected_states=affected_states,
                geometry=alert.geometry,
                geometry_bounds=alert.geometry_bounds
            )
            db.session.add(radar_alert)
            stats['wind_events'] = 1
            
        elif create_wind_event and not create_hail_event:
            # Wind-only event
            radar_alert = RadarAlert(
                alert_id=alert.id,
                event_type='wind',
                event_date=event_date,
                detected_time=detected_time,
                hail_inches=None,
                wind_mph=wind_mph,
                city_names=city_names,
                county_names=county_names,
                fips_codes=fips_codes,
                affected_states=affected_states,
                geometry=alert.geometry,
                geometry_bounds=alert.geometry_bounds
            )
            db.session.add(radar_alert)
            stats['wind_events'] = 1
        
        return stats
    
    def _parse_city_names(self, area_desc: str) -> List[str]:
        """Parse city names from area_desc field"""
        if not area_desc:
            return []
        return self.city_parser.parse_area_desc(area_desc)
    
    def _extract_counties(self, county_data) -> List[str]:
        """Extract county names from county_names field"""
        if not county_data:
            return []
        if isinstance(county_data, list):
            return county_data
        if isinstance(county_data, str):
            return [county_data]
        return []
    
    def _extract_fips(self, fips_data) -> List[str]:
        """Extract FIPS codes from fips_codes field"""
        if not fips_data:
            return []
        if isinstance(fips_data, list):
            return [str(f) for f in fips_data]
        if isinstance(fips_data, (str, int)):
            return [str(fips_data)]
        return []
    
    def _extract_states(self, states_data) -> List[str]:
        """Extract state abbreviations from affected_states field"""
        if not states_data:
            return []
        if isinstance(states_data, list):
            return states_data
        if isinstance(states_data, str):
            return [states_data]
        return []
    
    def _extract_float(self, value) -> Optional[float]:
        """Safely extract float value"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_int(self, value) -> Optional[int]:
        """Safely extract integer value"""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

def get_available_dates() -> List[str]:
    """
    Get list of dates with radar-detected alerts
    """
    with db.session.begin():
        dates = db.session.query(
            func.date(Alert.effective).label('date')
        ).filter(
            Alert.radar_indicated.isnot(None)
        ).distinct().order_by('date').all()
        
        return [d.date.isoformat() for d in dates if d.date]

def get_radar_backfill_stats() -> Dict[str, Any]:
    """
    Get current radar_alerts table statistics
    """
    with db.session.begin():
        stats = {}
        
        # Total events
        stats['total_events'] = db.session.query(RadarAlert).count()
        
        # By event type
        stats['hail_events'] = db.session.query(RadarAlert).filter_by(event_type='hail').count()
        stats['wind_events'] = db.session.query(RadarAlert).filter_by(event_type='wind').count()
        
        # Date range
        date_range = db.session.query(
            func.min(RadarAlert.event_date).label('earliest'),
            func.max(RadarAlert.event_date).label('latest')
        ).first()
        
        stats['earliest_date'] = date_range.earliest.isoformat() if date_range.earliest else None
        stats['latest_date'] = date_range.latest.isoformat() if date_range.latest else None
        
        # Recent activity
        recent_events = db.session.query(RadarAlert).filter(
            RadarAlert.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        stats['events_created_today'] = recent_events
        
        return stats

# Module-level functions for API integration
def process_date_range(start_date: str, end_date: str, batch_size: int = 100) -> Dict[str, Any]:
    """
    Module-level function for processing radar alerts date range
    Used by API endpoints
    """
    processor = RadarBackfillProcessor()
    return processor.process_date_range(start_date, end_date, batch_size)