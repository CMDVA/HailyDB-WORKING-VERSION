"""
Production-Grade Live Radar Alerts Service for HailyDB v2.0
Clean implementation with HailyAI-inspired architecture
"""

import logging
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from cachetools import TTLCache
from sqlalchemy.orm import Session

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
    certainty: str
    certainty_raw: str
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
    alert_status: str
    source: str
    web_url: Optional[str]

class ProductionLiveRadarService:
    """
    Production Live Radar Service with state-based filtering and caching
    Based on proven HailyAI architecture for contractor-focused storm intelligence
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.cache = TTLCache(maxsize=100, ttl=300)  # 5-minute TTL like HailyAI
        self.nws_api_url = "https://api.weather.gov/alerts/active"
        self.headers = {
            'User-Agent': 'HailyDB-NWS-Ingestion/2.0 (contact@hailydb.com)',
            'Accept': 'application/geo+json'
        }
        # Default storm restoration focus states (like HailyAI)
        self.target_states = ['FL', 'TX', 'AL', 'GA', 'SC', 'NC', 'LA', 'MS', 'TN', 'AR', 'OK', 'KS']
        
        # Production-grade instance variables for webhook deduplication
        self.alerts_store = {}  # In-memory alert storage
        self.webhook_seen_ids = TTLCache(maxsize=1000, ttl=3600)  # 1-hour webhook TTL
        self.webhook_suppressions = 0
        self.last_poll_timestamp = None
        
    def get_live_alerts_with_state_filtering(self, user_states: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch live NWS alerts with state-based filtering
        Uses proven caching and filtering approach from HailyAI
        """
        try:
            # Use user states or default target states
            states = user_states or self.target_states
            
            # Create cache key based on states
            cache_key = f"alerts_{'_'.join(sorted(states))}"
            
            # Check cache first (5-minute TTL)
            if cache_key in self.cache:
                logger.debug("Returning cached radar alerts")
                cached_data = self.cache[cache_key]
                cached_data['cache_hit'] = True
                return cached_data
            
            # Fetch from NWS API
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
                    
                    # Apply state filtering (like HailyAI)
                    if self._should_include_alert_by_state(alert, states):
                        radar_alerts.append(asdict(alert))
                        self.alerts_store[alert.id] = alert
                        processed_count += 1
            
            # Cleanup expired alerts
            self._cleanup_expired_alerts()
            
            # Calculate statistics
            stats = self._calculate_statistics(radar_alerts)
            stats['last_nws_poll_timestamp'] = self.last_poll_timestamp.isoformat()
            
            result = {
                'success': True,
                'alerts': radar_alerts,
                'statistics': stats,
                'last_poll_timestamp': self.last_poll_timestamp.isoformat(),
                'source': 'live_nws',
                'cache_hit': False,
                'filtered_states': states
            }
            
            # Cache the result
            self.cache[cache_key] = result
            
            logger.info(f"Processed {processed_count} radar alerts from NWS for states: {states}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error polling NWS alerts: {e}")
            return {
                'success': False,
                'error': f"NWS polling failed: {str(e)}",
                'alerts': [],
                'statistics': {},
                'last_poll_timestamp': self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None,
                'source': 'error'
            }
    
    def _determine_enhanced_radar_indication(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced radar indication detection with explicit criteria"""
        event = props.get('event', '').lower()
        description = props.get('description', '').lower()
        parameters = props.get('parameters', {})
        certainty_raw = props.get('certainty', 'Unknown')
        
        # Core radar alert criteria
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
            
            # Extract hail size - numeric patterns
            hail_patterns = [
                r'(\d+\.?\d*)\s*inch.*?hail',
                r'hail.*?(\d+\.?\d*)\s*inch',
                r'(\d+\.?\d*)".*?hail'
            ]
            
            for pattern in hail_patterns:
                hail_match = re.search(pattern, description)
                if hail_match:
                    hail_size = max(hail_size, float(hail_match.group(1)))
            
            # Extract hail size - NWS descriptive sizes
            hail_size_map = {
                'pea': 0.25, 'peanut': 0.5, 'penny': 0.75,
                'nickel': 0.88, 'quarter': 1.0, 'half dollar': 1.25,
                'ping pong ball': 1.5, 'golf ball': 1.75, 'egg': 2.0,
                'tennis ball': 2.5, 'baseball': 2.75, 'large apple': 3.0,
                'softball': 4.0, 'grapefruit': 4.5
            }
            
            for size_desc, size_val in hail_size_map.items():
                if size_desc in description:
                    hail_size = max(hail_size, size_val)
        
        # Apply radar alert criteria: ANY hail OR wind ≥ 50 mph (standardized threshold)
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
        """Map NWS certainty to enhanced display format"""
        if 'observed' in certainty_raw.lower() or 'radar indicated' in description.lower():
            return 'Observed'
        elif 'likely' in certainty_raw.lower():
            return 'Expected'
        else:
            return 'Possible'
    
    def _create_production_alert(self, feature: Dict[str, Any], radar_data: Dict[str, Any]) -> ProductionRadarAlert:
        """Create production-grade alert object"""
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        # Extract basic alert data
        alert_id = props.get('id', f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        event = props.get('event', 'Unknown Event')
        area_desc = props.get('areaDesc', 'Unknown Area')
        
        # Extract geographic data
        affected_states = self._extract_states_from_area_desc(area_desc)
        county_names = self._extract_counties(area_desc)
        
        # Extract timing
        effective_time = self._parse_time(props.get('effective'))
        expires_time = self._parse_time(props.get('expires'))
        
        # Generate alert template
        message_template = self._generate_message_template(props, radar_data['wind_speed'], radar_data['hail_size'])
        
        return ProductionRadarAlert(
            id=alert_id,
            event=event,
            max_wind_gust=radar_data['wind_speed'] if radar_data['wind_speed'] > 0 else None,
            max_hail_size=radar_data['hail_size'] if radar_data['hail_size'] > 0 else None,
            area_desc=area_desc,
            affected_states=affected_states,
            county_names=county_names,
            certainty=radar_data['certainty'],
            certainty_raw=radar_data['certainty_raw'],
            urgency=props.get('urgency', 'Unknown'),
            severity=props.get('severity', 'Unknown'),
            radar_indicated_event=radar_data['is_radar_indicated'],
            alert_message_template=message_template,
            effective_time=effective_time,
            expires_time=expires_time,
            geometry=geometry,
            description=props.get('description', ''),
            instruction=props.get('instruction', ''),
            created_at=datetime.utcnow(),
            alert_status='ACTIVE' if not expires_time or expires_time > datetime.utcnow() else 'EXPIRED',
            source='live_nws',
            web_url=props.get('@id')
        )
    
    def _should_include_alert_by_state(self, alert: ProductionRadarAlert, target_states: List[str]) -> bool:
        """Filter alerts by target states (like HailyAI)"""
        return any(state.upper() in [s.upper() for s in target_states] for state in alert.affected_states)
    
    def _extract_states_from_area_desc(self, area_desc: str) -> List[str]:
        """Extract state abbreviations from NWS area description"""
        state_pattern = r'\b[A-Z]{2}\b'
        return list(set(re.findall(state_pattern, area_desc)))
    
    def _extract_counties(self, area_desc: str) -> List[str]:
        """Extract county names from area description"""
        # Split by semicolons and extract county names
        parts = area_desc.split(';')
        counties = []
        for part in parts:
            # Remove state abbreviations and clean up
            clean_part = re.sub(r'\s+[A-Z]{2}$', '', part.strip())
            if clean_part:
                counties.append(clean_part)
        return counties
    
    def _generate_message_template(self, props: Dict[str, Any], wind_speed: int, hail_size: float) -> str:
        """Generate pre-formatted message template for webhooks"""
        event = props.get('event', 'Weather Alert')
        area = props.get('areaDesc', 'Unknown Area')
        severity = props.get('severity', 'Unknown')
        
        template = f"ALERT: {event}\nArea: {area}\nSeverity: {severity}"
        
        if wind_speed > 0:
            template += f"\nWind: {wind_speed} mph"
        if hail_size > 0:
            template += f"\nHail: {hail_size} inch"
        
        template += "\nAlert Status: Active"
        
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
            logger.debug(f"Cleaned up {len(expired_ids)} expired alerts")
    
    def _calculate_statistics(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for API response"""
        total_alerts = len(alerts)
        
        # Count by severity
        severity_counts = {}
        for alert in alerts:
            severity = alert.get('severity', 'Unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'severity_breakdown': severity_counts,
            'has_tornado_warnings': any('tornado warning' in alert.get('event', '').lower() for alert in alerts),
            'has_severe_thunderstorm_warnings': any('severe thunderstorm warning' in alert.get('event', '').lower() for alert in alerts)
        }
    
    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """Parse NWS datetime strings"""
        if not time_str:
            return None
        try:
            # Handle ISO format with timezone
            if 'T' in time_str:
                parsed_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                # Convert to UTC naive datetime for comparison
                return parsed_dt.replace(tzinfo=None)
            return None
        except:
            return None
    
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

def get_live_radar_service(db_session: Session) -> ProductionLiveRadarService:
    """Get or create global live radar service instance"""
    global _live_radar_service
    if _live_radar_service is None:
        _live_radar_service = ProductionLiveRadarService(db_session)
    return _live_radar_service