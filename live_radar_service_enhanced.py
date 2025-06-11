"""
Production-Grade Live Radar Alerts Service for HailyDB v2.0
Implements TTL webhook deduplication, enhanced certainty detection, and clean separation
"""

import json
import logging
import requests
import threading
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from cachetools import TTLCache
from shapely.geometry import shape, Point

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProductionRadarAlert:
    """Production-grade radar alert with enhanced fields"""
    id: str
    event: str
    max_wind_gust: Optional[int]
    max_hail_size: Optional[float]
    area_desc: str
    affected_states: List[str]
    county_names: List[str]
    certainty: str  # "Observed" | "Expected"
    certainty_raw: str  # Original NWS certainty value
    urgency: str
    severity: str
    radar_indicated_event: bool
    alert_message_template: str
    effective_time: Optional[datetime]
    expires_time: Optional[datetime]
    geometry: Optional[Dict[str, Any]]
    description: str
    instruction: str
    created_at: datetime
    alert_status: str  # "ACTIVE" | "EXPIRED"
    source: str  # "live_nws"
    web_url: Optional[str]

class ProductionLiveRadarService:
    """
    Production-ready Live Radar service with webhook deduplication
    Implements all requirements for client-facing API deployment
    """
    
    def __init__(self, nws_api_url: str = "https://api.weather.gov/alerts/active", 
                 webhook_dedupe_ttl: int = 600):
        self.nws_api_url = nws_api_url
        self.alerts_store: Dict[str, ProductionRadarAlert] = {}
        self.last_poll_timestamp: Optional[datetime] = None
        
        # Webhook deduplication - critical for production
        self.webhook_seen_ids = TTLCache(maxsize=5000, ttl=webhook_dedupe_ttl)
        self.webhook_suppressions = 0
        
        # Request headers for NWS API
        self.headers = {
            'User-Agent': 'HailyDB-LiveRadar-Production/2.0 (api@hailydb.com)',
            'Accept': 'application/geo+json'
        }
        
        logger.info("Production Live Radar Service initialized")
    
    def poll_nws_alerts(self) -> Dict[str, Any]:
        """
        Poll NWS alerts and return processed radar alerts
        Returns: {'alerts': List[dict], 'statistics': dict, 'last_poll_timestamp': str}
        """
        try:
            response = requests.get(self.nws_api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            self.last_poll_timestamp = datetime.utcnow()
            data = response.json()
            
            # Process alerts for radar indication
            radar_alerts = []
            processed_count = 0
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                
                # Check for radar indication
                radar_data = self._determine_enhanced_radar_indication(props)
                if radar_data['is_radar_indicated']:
                    alert = self._create_production_alert(feature, radar_data)
                    radar_alerts.append(asdict(alert))
                    self.alerts_store[alert.id] = alert
                    processed_count += 1
            
            # Cleanup expired alerts (retain for 15 minutes post-expiration)
            self._cleanup_expired_alerts()
            
            # Calculate statistics
            stats = self._calculate_statistics(radar_alerts)
            stats['last_nws_poll_timestamp'] = self.last_poll_timestamp.isoformat()
            
            logger.info(f"Processed {processed_count} radar alerts from NWS")
            
            return {
                'success': True,
                'alerts': radar_alerts,
                'statistics': stats,
                'last_poll_timestamp': self.last_poll_timestamp.isoformat(),
                'source': 'live_nws'
            }
            
        except Exception as e:
            logger.error(f"Error polling NWS alerts: {e}")
            return {
                'success': False,
                'error': f"NWS polling failed: {str(e)}",
                'alerts': [],
                'statistics': {},
                'last_poll_timestamp': self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None
            }
    
    def _determine_enhanced_radar_indication(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced radar indication detection with explicit certainty parsing
        Returns: {'is_radar_indicated': bool, 'certainty': str, 'certainty_raw': str, ...}
        """
        event = props.get('event', '').lower()
        description = props.get('description', '').lower()
        parameters = props.get('parameters', {})
        certainty_raw = props.get('certainty', 'Unknown')
        
        # Core radar alert criteria: Hail (any size) OR Wind ≥ 50 mph
        is_radar_indicated = False
        wind_speed = 0
        hail_size = 0.0
        
        # Check event types
        radar_events = [
            'severe thunderstorm warning',
            'tornado warning', 
            'tornado watch',
            'severe weather statement'
        ]
        
        event_matches = any(re_event in event for re_event in radar_events)
        
        if event_matches:
            # Extract wind speed
            wind_patterns = [
                r'(\d+)\s*mph\s*wind',
                r'wind.*?(\d+)\s*mph',
                r'winds.*?(\d+)\s*mph'
            ]
            
            for pattern in wind_patterns:
                wind_match = re.search(pattern, description)
                if wind_match:
                    wind_speed = max(wind_speed, int(wind_match.group(1)))
            
            # Extract hail size
            hail_patterns = [
                r'(\d+\.?\d*)\s*inch.*?hail',
                r'hail.*?(\d+\.?\d*)\s*inch',
                r'(\d+\.?\d*)".*?hail'
            ]
            
            for pattern in hail_patterns:
                hail_match = re.search(pattern, description)
                if hail_match:
                    hail_size = max(hail_size, float(hail_match.group(1)))
            
            # Check NWS parameters for more precise data
            if 'windSpeed' in parameters:
                try:
                    param_wind = parameters['windSpeed'][0] if isinstance(parameters['windSpeed'], list) else parameters['windSpeed']
                    if isinstance(param_wind, str) and 'mph' in param_wind:
                        wind_match = re.search(r'(\d+)', param_wind)
                        if wind_match:
                            wind_speed = max(wind_speed, int(wind_match.group(1)))
                except:
                    pass
            
            if 'hailSize' in parameters:
                try:
                    param_hail = parameters['hailSize'][0] if isinstance(parameters['hailSize'], list) else parameters['hailSize']
                    if isinstance(param_hail, str):
                        hail_match = re.search(r'(\d+\.?\d*)', param_hail)
                        if hail_match:
                            hail_size = max(hail_size, float(hail_match.group(1)))
                except:
                    pass
        
        # Apply radar alert criteria: Hail (any size) OR Wind ≥ 50 mph
        is_radar_indicated = (hail_size > 0) or (wind_speed >= 50)
        
        # Enhanced certainty determination
        certainty = self._determine_certainty(certainty_raw, description)
        
        return {
            'is_radar_indicated': is_radar_indicated,
            'wind_speed': wind_speed,
            'hail_size': hail_size,
            'certainty': certainty,
            'certainty_raw': certainty_raw
        }
    
    def _determine_certainty(self, certainty_raw: str, description: str) -> str:
        """
        Determine if alert is "Observed" or "Expected" based on NWS data
        """
        certainty_lower = certainty_raw.lower()
        desc_lower = description.lower()
        
        # Observed indicators
        observed_patterns = [
            r'radar.*?indicated',
            r'doppler.*?indicated',
            r'confirmed',
            r'reported',
            r'observed',
            r'in progress',
            r'occurring'
        ]
        
        # Expected indicators  
        expected_patterns = [
            r'possible',
            r'likely',
            r'expected',
            r'forecast',
            r'developing'
        ]
        
        # Check NWS certainty field first
        if certainty_lower in ['observed', 'likely']:
            return "Observed"
        elif certainty_lower in ['possible', 'expected']:
            return "Expected"
        
        # Check description patterns
        for pattern in observed_patterns:
            if re.search(pattern, desc_lower):
                return "Observed"
        
        for pattern in expected_patterns:
            if re.search(pattern, desc_lower):
                return "Expected"
        
        # Default based on certainty field
        return "Observed" if certainty_lower == "observed" else "Expected"
    
    def _create_production_alert(self, feature: Dict[str, Any], radar_data: Dict[str, Any]) -> ProductionRadarAlert:
        """Create production-grade alert object"""
        props = feature.get('properties', {})
        geometry = feature.get('geometry')
        
        # Parse timestamps
        effective_time = None
        expires_time = None
        
        try:
            if props.get('effective'):
                effective_time = datetime.fromisoformat(props['effective'].replace('Z', '+00:00')).replace(tzinfo=None)
            if props.get('expires'):
                expires_time = datetime.fromisoformat(props['expires'].replace('Z', '+00:00')).replace(tzinfo=None)
        except:
            pass
        
        # Determine alert status
        now = datetime.utcnow()
        alert_status = "ACTIVE"
        if expires_time and expires_time < now:
            alert_status = "EXPIRED"
        
        # Extract location data
        area_desc = props.get('areaDesc', '')
        affected_states = self._extract_states(area_desc)
        county_names = self._extract_counties(area_desc)
        
        # Generate message template
        message_template = self._generate_message_template(props, radar_data)
        
        # Generate web URL
        alert_id = props.get('id', '')
        web_url = None
        if alert_id:
            url_suffix = alert_id.split('.')[-1] if '.' in alert_id else alert_id
            web_url = f"https://alerts.weather.gov/cap/{url_suffix}.html"
        
        return ProductionRadarAlert(
            id=alert_id,
            event=props.get('event', ''),
            max_wind_gust=radar_data.get('wind_speed'),
            max_hail_size=radar_data.get('hail_size'),
            area_desc=area_desc,
            affected_states=affected_states,
            county_names=county_names,
            certainty=radar_data['certainty'],
            certainty_raw=radar_data['certainty_raw'],
            urgency=props.get('urgency', ''),
            severity=props.get('severity', ''),
            radar_indicated_event=radar_data['is_radar_indicated'],
            alert_message_template=message_template,
            effective_time=effective_time,
            expires_time=expires_time,
            geometry=geometry,
            description=props.get('description', ''),
            instruction=props.get('instruction', ''),
            created_at=datetime.utcnow(),
            alert_status=alert_status,
            source="live_nws",
            web_url=web_url
        )
    
    def _extract_states(self, area_desc: str) -> List[str]:
        """Extract state codes from area description"""
        state_pattern = r'\b([A-Z]{2})\b'
        return list(set(re.findall(state_pattern, area_desc)))
    
    def _extract_counties(self, area_desc: str) -> List[str]:
        """Extract county names from area description"""
        # Split by semicolon and extract county names
        counties = []
        for area in area_desc.split(';'):
            area = area.strip()
            if ',' in area:
                county_part = area.split(',')[0].strip()
                if not re.match(r'^[A-Z]{2}$', county_part):  # Not a state code
                    counties.append(county_part)
        return list(set(counties))
    
    def _generate_message_template(self, props: Dict[str, Any], radar_data: Dict[str, Any]) -> str:
        """Generate pre-formatted message template for webhooks"""
        event = props.get('event', 'Weather Alert')
        area = props.get('areaDesc', 'Unknown Area')
        
        # Build severity info
        severity_parts = []
        if radar_data.get('wind_speed', 0) >= 50:
            severity_parts.append(f"{radar_data['wind_speed']} mph winds")
        if radar_data.get('hail_size', 0) > 0:
            severity_parts.append(f"{radar_data['hail_size']}\" hail")
        
        severity_text = " and ".join(severity_parts) if severity_parts else "severe conditions"
        
        template = f"""🚨 {event}
📍 {area}
⚠️ {severity_text.title()}
🔍 Certainty: {radar_data['certainty']}
⏰ Alert Status: Active"""
        
        return template
    
    def _cleanup_expired_alerts(self):
        """Remove alerts expired more than 15 minutes ago"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        expired_ids = []
        
        for alert_id, alert in self.alerts_store.items():
            if alert.expires_time and alert.expires_time < cutoff_time:
                expired_ids.append(alert_id)
        
        for alert_id in expired_ids:
            del self.alerts_store[alert_id]
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired alerts")
    
    def _calculate_statistics(self, alerts: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for API response"""
        hail_count = sum(1 for alert in alerts if alert.get('max_hail_size', 0) > 0)
        wind_count = sum(1 for alert in alerts if alert.get('max_wind_gust', 0) >= 50)
        states = set()
        
        for alert in alerts:
            states.update(alert.get('affected_states', []))
        
        return {
            'total_alerts': len(alerts),
            'hail_alerts': hail_count,
            'wind_alerts': wind_count,
            'states_affected': len(states),
            'webhook_suppressions': self.webhook_suppressions
        }
    
    def should_dispatch_webhook(self, alert_id: str) -> bool:
        """
        Check if webhook should be dispatched (deduplication logic)
        Returns True if webhook should fire, False if suppressed
        """
        if alert_id in self.webhook_seen_ids:
            self.webhook_suppressions += 1
            logger.debug(f"Webhook suppressed for alert {alert_id} (dedupe)")
            return False
        
        # Mark as seen
        self.webhook_seen_ids[alert_id] = True
        return True
    
    def get_filtered_alerts(self, state: Optional[str] = None, county: Optional[str] = None) -> List[Dict]:
        """Get alerts filtered by state and/or county"""
        alerts = list(self.alerts_store.values())
        
        if state:
            alerts = [a for a in alerts if state.upper() in a.affected_states]
        
        if county:
            alerts = [a for a in alerts if any(county.lower() in c.lower() for c in a.county_names)]
        
        return [asdict(alert) for alert in alerts]
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'alerts_in_store': len(self.alerts_store),
            'last_poll_timestamp': self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None,
            'webhook_cache_size': len(self.webhook_seen_ids),
            'webhook_suppressions': self.webhook_suppressions,
            'service_status': 'operational'
        }

# Global service instance
_live_radar_service: Optional[ProductionLiveRadarService] = None

def get_live_radar_service() -> ProductionLiveRadarService:
    """Get or create global live radar service instance"""
    global _live_radar_service
    if _live_radar_service is None:
        _live_radar_service = ProductionLiveRadarService()
    return _live_radar_service