"""
Live Radar Alerts Service for HailyDB
Provides real-time NWS alert streaming with pre-formatted message templates
"""

import json
import logging
import requests
import threading
import time
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
from cachetools import TTLCache
from shapely.geometry import shape, Point

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LiveRadarAlert:
    """Data class for live radar alerts"""
    id: str
    event: str
    max_wind_gust: Optional[int]
    max_hail_size: Optional[float]
    area_desc: str
    affected_states: List[str]
    county_names: List[str]
    certainty: str
    certainty_raw: str
    urgency: str
    severity: str
    radar_indicated_event: bool
    event_certainty: str
    event_urgency: str
    alert_message_template: str
    effective_time: Optional[datetime]
    expires_time: Optional[datetime]
    geometry: Optional[Dict[str, Any]]
    description: str
    instruction: str
    created_at: datetime
    alert_status: str  # "ACTIVE" | "EXPIRED"
    source: str  # "live_nws"

class LiveRadarAlertService:
    """
    Production-grade Live NWS radar alerts service with webhook deduplication
    Maintains in-memory store with TTL cache for webhook spam prevention
    """
    
    def __init__(self, db_session: Session = None, nws_api_url: str = "https://api.weather.gov/alerts/active", 
                 poll_interval: int = 60, webhook_dedupe_ttl: int = 600):
        self.db = db_session
        self.nws_api_url = nws_api_url
        self.poll_interval = poll_interval
        self.alerts_store: Dict[str, LiveRadarAlert] = {}
        self.last_poll_timestamp: Optional[datetime] = None
        self.is_running = False
        self.poll_thread: Optional[threading.Thread] = None
        
        # Webhook deduplication cache - prevents spam
        self.webhook_seen_ids = TTLCache(maxsize=5000, ttl=webhook_dedupe_ttl)
        self.webhook_suppressions = 0
        
        # Request headers for NWS API
        self.headers = {
            'User-Agent': 'HailyDB-LiveRadar/2.0 (production@hailydb.com)',
            'Accept': 'application/geo+json'
        }
        
    def start_polling(self):
        """Start continuous polling of NWS active alerts"""
        if self.is_running:
            logger.warning("Live radar alert polling already running")
            return
            
        self.is_running = True
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        logger.info("Started live radar alert polling service")
        
    def stop_polling(self):
        """Stop polling service"""
        self.is_running = False
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=5)
        logger.info("Stopped live radar alert polling service")
        
    def _poll_loop(self):
        """Main polling loop - runs continuously"""
        while self.is_running:
            try:
                self._fetch_and_process_alerts()
                self._cleanup_expired_alerts()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in live radar alert polling: {e}")
                time.sleep(30)  # Back off on error
                
    def _fetch_and_process_alerts(self):
        """Fetch alerts from NWS API and process them"""
        try:
            # Fetch active alerts from NWS API
            url = "https://api.weather.gov/alerts/active"
            headers = {
                'User-Agent': 'HailyDB/1.0 (weather-monitoring-system)',
                'Accept': 'application/geo+json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"Fetched {len(features)} active alerts from NWS API")
            
            processed_count = 0
            for feature in features:
                try:
                    alert = self._process_alert_feature(feature)
                    if alert:
                        self.alerts_store[alert.id] = alert
                        processed_count += 1
                        
                        # Optionally store in database with TTL
                        if self.db:
                            self._store_alert_in_db(alert)
                            
                        # Trigger webhook evaluation for new alert
                        self._evaluate_webhooks_for_alert(alert)
                            
                except Exception as e:
                    logger.error(f"Error processing alert feature: {e}")
                    
            logger.info(f"Processed {processed_count} live radar alerts")
            
        except Exception as e:
            logger.error(f"Error fetching NWS alerts: {e}")
            
    def _process_alert_feature(self, feature: Dict[str, Any]) -> Optional[LiveRadarAlert]:
        """Process a single alert feature from NWS API"""
        try:
            properties = feature.get('properties', {})
            
            # Extract basic properties
            alert_id = properties.get('id', '')
            event = properties.get('event', '')
            
            # Extract parameters for wind/hail filtering
            parameters = properties.get('parameters', {})
            max_wind_gust = self._extract_wind_parameter(parameters)
            max_hail_size = self._extract_hail_parameter(parameters)
            
            # Filter: Process ANY hail size OR wind >= 50 mph (independent conditions)
            has_qualifying_hail = max_hail_size is not None and max_hail_size > 0
            has_qualifying_wind = max_wind_gust is not None and max_wind_gust >= 50
            
            if not (has_qualifying_hail or has_qualifying_wind):
                return None
                
            # Extract location information
            area_desc = properties.get('areaDesc', '')
            affected_states = self._extract_affected_states(properties)
            county_names = self._extract_county_names(properties)
            
            # Extract alert metadata
            certainty = properties.get('certainty', '')
            urgency = properties.get('urgency', '')
            severity = properties.get('severity', '')
            
            description = properties.get('description', '')
            instruction = properties.get('instruction', '')
            
            # Parse timestamps
            effective_time = self._parse_timestamp(properties.get('effective'))
            expires_time = self._parse_timestamp(properties.get('expires'))
            
            # Determine radar indication
            radar_indicated = self._determine_radar_indication(description, certainty)
            
            # Generate alert message template
            alert_message = self._generate_alert_message_template(
                radar_indicated, urgency, max_wind_gust, max_hail_size, area_desc, certainty
            )
            
            # Extract geometry
            geometry = feature.get('geometry')
            
            return LiveRadarAlert(
                id=alert_id,
                event=event,
                max_wind_gust=max_wind_gust,
                max_hail_size=max_hail_size,
                area_desc=area_desc,
                affected_states=affected_states,
                county_names=county_names,
                certainty=certainty,
                certainty_raw=certainty,
                urgency=urgency,
                severity=severity,
                radar_indicated_event=radar_indicated,
                event_certainty=certainty,
                event_urgency=urgency,
                alert_message_template=alert_message,
                effective_time=effective_time,
                expires_time=expires_time,
                geometry=geometry,
                description=description,
                instruction=instruction,
                created_at=datetime.now(timezone.utc),
                alert_status="ACTIVE",
                source="live_nws"
            )
            
        except Exception as e:
            logger.error(f"Error processing alert feature: {e}")
            return None
            
    def _extract_wind_parameter(self, parameters: Dict[str, Any]) -> Optional[int]:
        """Extract wind gust parameter from NWS alert parameters"""
        wind_params = ['maxWindGust', 'windGust', 'windSpeed']
        
        for param in wind_params:
            values = parameters.get(param, [])
            if values and len(values) > 0:
                try:
                    # Extract numeric value from string like "70 MPH"
                    wind_str = str(values[0]).upper()
                    if 'MPH' in wind_str:
                        wind_value = int(''.join(filter(str.isdigit, wind_str)))
                        return wind_value
                except (ValueError, TypeError):
                    continue
                    
        return None
        
    def _extract_hail_parameter(self, parameters: Dict[str, Any]) -> Optional[float]:
        """Extract hail size parameter from NWS alert parameters"""
        hail_params = ['maxHailSize', 'hailSize']
        
        for param in hail_params:
            values = parameters.get(param, [])
            if values and len(values) > 0:
                try:
                    # Extract numeric value from string like "1.25"
                    hail_str = str(values[0])
                    hail_value = float(''.join(c for c in hail_str if c.isdigit() or c == '.'))
                    return hail_value if hail_value > 0 else None
                except (ValueError, TypeError):
                    continue
                    
        return None
        
    def _extract_affected_states(self, properties: Dict[str, Any]) -> List[str]:
        """Extract affected states from alert properties"""
        affected_zones = properties.get('affectedZones', [])
        states = set()
        
        for zone in affected_zones:
            # Extract state code from zone URL like ".../zones/forecast/GAZ154"
            if isinstance(zone, str) and '/zones/' in zone:
                parts = zone.split('/')
                if len(parts) > 0:
                    zone_code = parts[-1]
                    if len(zone_code) >= 2:
                        state_code = zone_code[:2]
                        states.add(state_code)
                        
        return list(states)
        
    def _extract_county_names(self, properties: Dict[str, Any]) -> List[str]:
        """Extract county names from area description"""
        area_desc = properties.get('areaDesc', '')
        
        # Split by semicolons and commas, clean up
        counties = []
        for part in area_desc.replace(';', ',').split(','):
            county = part.strip()
            if county and len(county) > 2:
                counties.append(county)
                
        return counties[:10]  # Limit to first 10 counties
        
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime"""
        if not timestamp_str:
            return None
            
        try:
            # Parse ISO format timestamp
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            return None
            
    def _determine_radar_indication(self, description: str, certainty: str) -> bool:
        """
        Determine if alert is radar-indicated based on NWS certainty and description
        
        NWS Certainty Levels:
        - "Observed": Confirmed radar-indicated event or direct observation
        - "Likely": High confidence forecast
        - "Possible": Lower confidence forecast
        - "Unknown": Insufficient data
        """
        if not description and not certainty:
            return False
            
        # Primary indicator: NWS certainty field
        certainty_lower = certainty.lower() if certainty else ''
        
        # "Observed" is the strongest signal for radar-detected events
        if certainty_lower == 'observed':
            return True
            
        # Secondary check: radar keywords in description text
        if description:
            description_lower = description.lower()
            radar_keywords = [
                'radar indicated', 'radar detected', 'radar showed', 'radar confirmed',
                'doppler radar indicated', 'radar velocity', 'radar reflectivity',
                'observed by radar', 'detected by radar'
            ]
            
            if any(keyword in description_lower for keyword in radar_keywords):
                return True
        
        return False
        
    def _generate_alert_message_template(self, radar_indicated: bool, urgency: str, 
                                       wind_gust: Optional[int], hail_size: Optional[float],
                                       area_desc: str, certainty: str) -> str:
        """
        Generate human-readable alert message template
        Distinguishes between radar-detected (Observed) vs forecast (Expected) events
        """
        
        # Parse locations from area description (first 2 locations)
        locations = self._parse_locations_for_template(area_desc)
        
        # Determine primary hazard with both hail and wind if present
        hazards = []
        if hail_size and hail_size > 0:
            hazards.append(f'{hail_size:.2f}" hail')
        if wind_gust and wind_gust >= 50:
            hazards.append(f"{wind_gust} mph winds")
            
        if not hazards:
            return f"Weather advisory issued for {locations}."
            
        hazard_text = " and ".join(hazards)
        
        # Generate message based on certainty (Observed vs Expected)
        certainty_lower = certainty.lower() if certainty else ''
        
        if certainty_lower == 'observed' or radar_indicated:
            # Radar-detected/observed events
            return f"⚠️ {hazard_text} detected by radar near {locations}!"
            
        elif urgency.lower() == "immediate":
            # Immediate threat but not yet observed
            return f"⚠️ {hazard_text} WARNING issued for {locations}!"
            
        elif urgency.lower() == "expected":
            # Forecast-based threat
            return f"Heads up: Potential {hazard_text} expected in {locations}."
        
        else:
            # Default case for other urgency levels
            return f"Weather alert: {hazard_text} possible in {locations}."
            
    def _parse_locations_for_template(self, area_desc: str) -> str:
        """Parse first 2 city/county names from area description for message template"""
        if not area_desc:
            return "unknown area"
            
        # Split by semicolons and commas
        locations = []
        for part in area_desc.replace(';', ',').split(','):
            location = part.strip()
            if location and len(location) > 2:
                locations.append(location)
                
        if len(locations) >= 2:
            return f"{locations[0]} and {locations[1]}"
        elif len(locations) == 1:
            return locations[0]
        else:
            return "unknown area"
            
    def _cleanup_expired_alerts(self):
        """Remove alerts older than 3 hours from expiration"""
        current_time = datetime.now(timezone.utc)
        expired_ids = []
        
        for alert_id, alert in self.alerts_store.items():
            # Remove only if more than 3 hours past expiration
            if alert.expires_time:
                hours_since_expiry = (current_time - alert.expires_time).total_seconds() / 3600
                if hours_since_expiry > 3:
                    expired_ids.append(alert_id)
            else:
                # If no expiry time, remove after 6 hours from creation
                age_hours = (current_time - alert.created_at).total_seconds() / 3600
                if age_hours > 6:
                    expired_ids.append(alert_id)
                
        for alert_id in expired_ids:
            del self.alerts_store[alert_id]
            
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} old expired alerts")
            
    def _store_alert_in_db(self, alert: LiveRadarAlert):
        """Store alert in database with automatic TTL cleanup"""
        if not self.db:
            return
            
        try:
            # Create table if not exists
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS live_radar_alerts (
                    id VARCHAR(255) PRIMARY KEY,
                    event VARCHAR(255),
                    max_wind_gust INTEGER,
                    max_hail_size FLOAT,
                    area_desc TEXT,
                    affected_states JSONB,
                    county_names JSONB,
                    certainty VARCHAR(100),
                    urgency VARCHAR(100),
                    severity VARCHAR(100),
                    radar_indicated_event BOOLEAN,
                    event_certainty VARCHAR(100),
                    event_urgency VARCHAR(100),
                    alert_message_template TEXT,
                    effective_time TIMESTAMP,
                    expires_time TIMESTAMP,
                    geometry JSONB,
                    description TEXT,
                    instruction TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Insert or update alert
            self.db.execute(text("""
                INSERT INTO live_radar_alerts (
                    id, event, max_wind_gust, max_hail_size, area_desc,
                    affected_states, county_names, certainty, urgency, severity,
                    radar_indicated_event, event_certainty, event_urgency,
                    alert_message_template, effective_time, expires_time,
                    geometry, description, instruction, created_at
                ) VALUES (
                    :id, :event, :max_wind_gust, :max_hail_size, :area_desc,
                    :affected_states, :county_names, :certainty, :urgency, :severity,
                    :radar_indicated_event, :event_certainty, :event_urgency,
                    :alert_message_template, :effective_time, :expires_time,
                    :geometry, :description, :instruction, :created_at
                ) ON CONFLICT (id) DO UPDATE SET
                    event = EXCLUDED.event,
                    max_wind_gust = EXCLUDED.max_wind_gust,
                    max_hail_size = EXCLUDED.max_hail_size,
                    area_desc = EXCLUDED.area_desc,
                    affected_states = EXCLUDED.affected_states,
                    county_names = EXCLUDED.county_names,
                    certainty = EXCLUDED.certainty,
                    urgency = EXCLUDED.urgency,
                    severity = EXCLUDED.severity,
                    radar_indicated_event = EXCLUDED.radar_indicated_event,
                    event_certainty = EXCLUDED.event_certainty,
                    event_urgency = EXCLUDED.event_urgency,
                    alert_message_template = EXCLUDED.alert_message_template,
                    effective_time = EXCLUDED.effective_time,
                    expires_time = EXCLUDED.expires_time,
                    geometry = EXCLUDED.geometry,
                    description = EXCLUDED.description,
                    instruction = EXCLUDED.instruction
            """), {
                'id': alert.id,
                'event': alert.event,
                'max_wind_gust': alert.max_wind_gust,
                'max_hail_size': alert.max_hail_size,
                'area_desc': alert.area_desc,
                'affected_states': json.dumps(alert.affected_states),
                'county_names': json.dumps(alert.county_names),
                'certainty': alert.certainty,
                'urgency': alert.urgency,
                'severity': alert.severity,
                'radar_indicated_event': alert.radar_indicated_event,
                'event_certainty': alert.event_certainty,
                'event_urgency': alert.event_urgency,
                'alert_message_template': alert.alert_message_template,
                'effective_time': alert.effective_time,
                'expires_time': alert.expires_time,
                'geometry': json.dumps(alert.geometry) if alert.geometry else None,
                'description': alert.description,
                'instruction': alert.instruction,
                'created_at': alert.created_at
            })
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing live alert in database: {e}")
            self.db.rollback()
            
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active and recently expired live radar alerts"""
        alerts = []
        current_time = datetime.now(timezone.utc)
        
        for alert in self.alerts_store.values():
            # Determine if alert is active or expired
            is_expired = False
            if alert.expires_time and current_time > alert.expires_time:
                is_expired = True
            
            # Determine status for display
            if is_expired:
                status = "Expired"
            else:
                status = "Active"
            
            alerts.append({
                'id': alert.id,
                'event': alert.event,
                'maxHailSize': alert.max_hail_size,
                'maxWindGust': alert.max_wind_gust,
                'area_desc': alert.area_desc,
                'affected_states': alert.affected_states,
                'county_names': alert.county_names,
                'certainty': alert.certainty,
                'urgency': alert.urgency,
                'severity': alert.severity,
                'radar_indicated_event': alert.radar_indicated_event,
                'event_certainty': alert.event_certainty,
                'event_urgency': alert.event_urgency,
                'alert_message_template': alert.alert_message_template,
                'effective_time': alert.effective_time.isoformat() if alert.effective_time else None,
                'expires_time': alert.expires_time.isoformat() if alert.expires_time else None,
                'geometry': alert.geometry,
                'status': status,
                'is_expired': is_expired
            })
            
        # Sort by created time (newest first)
        alerts.sort(key=lambda x: x['id'], reverse=True)
        return alerts
        
    def cleanup_database_alerts(self):
        """Clean up expired alerts from database"""
        if not self.db:
            return
            
        try:
            # Remove alerts older than 3 hours
            self.db.execute(text("""
                DELETE FROM live_radar_alerts 
                WHERE created_at < NOW() - INTERVAL '3 hours'
                   OR expires_time < NOW()
            """))
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning up database alerts: {e}")
            self.db.rollback()
            
    def _evaluate_webhooks_for_alert(self, alert: LiveRadarAlert):
        """Evaluate and dispatch webhooks for a new live radar alert"""
        try:
            # Convert alert to webhook-compatible format
            alert_data = {
                'id': alert.id,
                'event': alert.event,
                'maxHailSize': alert.max_hail_size,
                'maxWindGust': alert.max_wind_gust,
                'area_desc': alert.area_desc,
                'affected_states': alert.affected_states,
                'county_names': alert.county_names,
                'certainty': alert.certainty,
                'urgency': alert.urgency,
                'severity': alert.severity,
                'radar_indicated_event': alert.radar_indicated_event,
                'event_certainty': alert.event_certainty,
                'event_urgency': alert.event_urgency,
                'alert_message_template': alert.alert_message_template,
                'effective_time': alert.effective_time.isoformat() if alert.effective_time else None,
                'expires_time': alert.expires_time.isoformat() if alert.expires_time else None
            }
            
            # Import and use webhook service
            try:
                from webhook_service import WebhookDispatcher
                webhook_dispatcher = WebhookDispatcher()
                
                # Evaluate webhooks for live radar alert
                result = webhook_dispatcher.evaluate_live_radar_alert(alert_data)
                
                if result.get('dispatched', 0) > 0:
                    logger.info(f"Dispatched {result['dispatched']} webhooks for live alert {alert.id}")
                    
            except ImportError:
                logger.warning("Webhook service not available for live radar alerts")
                
        except Exception as e:
            logger.error(f"Error evaluating webhooks for live alert {alert.id}: {e}")

# Global service instance
live_radar_service = None

def init_live_radar_service(db_session = None):
    """Initialize the global live radar service"""
    global live_radar_service
    live_radar_service = LiveRadarAlertService(db_session)
    
def start_live_radar_service():
    """Start the live radar alert polling service"""
    global live_radar_service
    if live_radar_service:
        live_radar_service.start_polling()
        
def stop_live_radar_service():
    """Stop the live radar alert polling service"""
    global live_radar_service
    if live_radar_service:
        live_radar_service.stop_polling()
        
def get_live_radar_service() -> Optional[LiveRadarAlertService]:
    """Get the global live radar service instance"""
    return live_radar_service