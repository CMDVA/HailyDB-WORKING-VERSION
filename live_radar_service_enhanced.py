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
        
    def get_live_alerts_with_state_filtering(self, user_states: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch live NWS alerts with state-based filtering
        Uses proven caching and filtering approach from HailyAI
        """
        try:
            # Use user states or default target states
            states = user_states or self.target_states
            
            # Create cache key based on states
            cache_key = f"live_alerts_{'_'.join(sorted(states))}"
            
            # Check cache first (5-minute TTL)
            if cache_key in self.cache:
                logger.info(f"Returning cached alerts for states: {', '.join(states)}")
                return self.cache[cache_key]
            
            # Fetch from NWS API with area filtering
            area_param = ','.join(states)
            params = {
                'area': area_param,
                'status': 'actual',  # Only actual alerts, not tests
                'message_type': 'alert',  # Exclude administrative messages
            }
            
            logger.info(f"Fetching live NWS alerts for states: {area_param}")
            response = requests.get(self.nws_api_url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"NWS API request failed: {response.status_code}")
                return self._empty_response()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"Received {len(features)} raw alerts from NWS")
            
            # Process and filter alerts
            processed_alerts = []
            for feature in features:
                alert = self._process_nws_feature(feature)
                if alert and self._should_include_alert(alert):
                    processed_alerts.append(asdict(alert))
            
            # Create response with statistics
            response_data = {
                'alerts': processed_alerts,
                'total_count': len(processed_alerts),
                'statistics': self._calculate_statistics(processed_alerts),
                'last_updated': datetime.now().isoformat(),
                'states_filtered': states,
                'source': 'live_nws_with_state_filtering'
            }
            
            # Cache the response
            self.cache[cache_key] = response_data
            logger.info(f"Cached {len(processed_alerts)} processed alerts")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error fetching live alerts: {e}")
            return self._empty_response()
    
    def _process_nws_feature(self, feature: Dict[str, Any]) -> Optional[ProductionRadarAlert]:
        """
        Process NWS GeoJSON feature into ProductionRadarAlert
        Handles coordinate extraction and radar detection parsing
        """
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            alert_id = properties.get('id', '')
            if not alert_id:
                return None
            
            # Extract radar-indicated wind and hail data
            wind_gust, hail_size = self._extract_radar_data(properties)
            
            # Process geometry coordinates (like HailyAI)
            processed_geometry = self._process_geometry(geometry)
            
            # Extract states from area description
            affected_states = self._extract_states_from_area_desc(properties.get('areaDesc', ''))
            
            # Enhanced certainty mapping
            certainty_raw = properties.get('certainty', 'Unknown')
            certainty = self._map_certainty_to_enhanced(certainty_raw)
            
            alert = ProductionRadarAlert(
                id=alert_id,
                event=properties.get('event', 'Unknown'),
                max_wind_gust=wind_gust,
                max_hail_size=hail_size,
                area_desc=properties.get('areaDesc', ''),
                affected_states=affected_states,
                county_names=self._extract_counties(properties.get('areaDesc', '')),
                certainty=certainty,
                certainty_raw=certainty_raw,
                urgency=properties.get('urgency', 'Unknown'),
                severity=properties.get('severity', 'Unknown'),
                radar_indicated_event=bool(wind_gust or hail_size),
                alert_message_template=self._generate_message_template(properties, wind_gust, hail_size),
                effective_time=self._parse_time(properties.get('effective')),
                expires_time=self._parse_time(properties.get('expires')),
                geometry=processed_geometry,
                description=properties.get('description', ''),
                instruction=properties.get('instruction', ''),
                created_at=datetime.now(),
                alert_status='ACTIVE',
                source='live_nws',
                web_url=properties.get('web', '')
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Error processing NWS feature: {e}")
            return None
    
    def _should_include_alert(self, alert: ProductionRadarAlert) -> bool:
        """
        Severity-based filtering to exclude minor advisories (like HailyAI)
        Focus on actionable storm restoration events
        """
        # Exclude minor marine and coastal advisories
        exclude_events = [
            'Small Craft Advisory',
            'Marine Weather Statement',
            'Coastal Flood Advisory',
            'Beach Hazards Statement',
            'Rip Current Statement'
        ]
        
        if alert.event in exclude_events:
            return False
        
        # Include all severe weather events
        severe_events = [
            'Tornado Warning',
            'Tornado Watch',
            'Severe Thunderstorm Warning', 
            'Severe Thunderstorm Watch',
            'Hail',
            'High Wind Warning',
            'Wind Advisory'
        ]
        
        if alert.event in severe_events:
            return True
        
        # Include alerts with radar-indicated severe weather
        if alert.radar_indicated_event:
            return True
        
        # Include based on severity
        if alert.severity in ['Extreme', 'Severe']:
            return True
        
        return False
    
    def _extract_radar_data(self, properties: Dict[str, Any]) -> Tuple[Optional[int], Optional[float]]:
        """
        Extract wind gust and hail size from NWS alert text
        Uses regex patterns to find radar-indicated values
        """
        text_fields = [
            properties.get('description', ''),
            properties.get('instruction', ''),
            properties.get('headline', '')
        ]
        
        combined_text = ' '.join(text_fields).upper()
        
        # Extract wind gusts
        wind_gust = None
        wind_patterns = [
            r'(\d+)\s*MPH\s*WIND',
            r'WIND.*?(\d+)\s*MPH',
            r'GUSTS.*?(\d+)\s*MPH',
            r'(\d+)\s*MPH\s*GUSTS'
        ]
        
        for pattern in wind_patterns:
            match = re.search(pattern, combined_text)
            if match:
                wind_gust = int(match.group(1))
                break
        
        # Extract hail size
        hail_size = None
        hail_keywords = {
            'PEA': 0.25, 'PENNY': 0.75, 'NICKEL': 0.88, 'QUARTER': 1.0,
            'HALF DOLLAR': 1.25, 'PING PONG': 1.5, 'GOLF BALL': 1.75,
            'TENNIS BALL': 2.5, 'BASEBALL': 2.75, 'SOFTBALL': 4.0
        }
        
        for keyword, size in hail_keywords.items():
            if keyword in combined_text:
                hail_size = size
                break
        
        # Look for numeric hail size
        if not hail_size:
            hail_match = re.search(r'(\d+(?:\.\d+)?)\s*INCH.*?HAIL', combined_text)
            if hail_match:
                hail_size = float(hail_match.group(1))
        
        return wind_gust, hail_size
    
    def _process_geometry(self, geometry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process NWS alert geometry coordinates
        Handles Point, Polygon, and MultiPolygon geometries
        """
        if not geometry:
            return None
        
        geom_type = geometry.get('type', '')
        coordinates = geometry.get('coordinates', [])
        
        if not coordinates:
            return None
        
        return {
            'type': geom_type,
            'coordinates': coordinates,
            'centroid': self._calculate_centroid(geometry)
        }
    
    def _calculate_centroid(self, geometry: Dict[str, Any]) -> Optional[List[float]]:
        """Calculate centroid of geometry for API requests"""
        try:
            geom = shape(geometry)
            centroid = geom.centroid
            return [centroid.x, centroid.y]
        except:
            return None
    
    def _extract_states_from_area_desc(self, area_desc: str) -> List[str]:
        """Extract state abbreviations from NWS area description"""
        # Common state abbreviation pattern
        state_pattern = r'\b([A-Z]{2})\b'
        matches = re.findall(state_pattern, area_desc.upper())
        
        # Filter to valid US state codes
        valid_states = {'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 
                       'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                       'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                       'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                       'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'}
        
        return list(set(match for match in matches if match in valid_states))
    
    def _extract_counties(self, area_desc: str) -> List[str]:
        """Extract county names from area description"""
        # Split by semicolons and commas, clean up
        parts = re.split('[;,]', area_desc)
        counties = []
        
        for part in parts:
            part = part.strip()
            # Remove state abbreviations
            part = re.sub(r'\s+[A-Z]{2}$', '', part)
            if part and len(part) > 2:
                counties.append(part)
        
        return counties[:10]  # Limit to prevent excessive data
    
    def _map_certainty_to_enhanced(self, certainty_raw: str) -> str:
        """Map NWS certainty to enhanced display format"""
        mapping = {
            'Observed': 'Observed',
            'Likely': 'Likely', 
            'Possible': 'Possible',
            'Unlikely': 'Unlikely'
        }
        return mapping.get(certainty_raw, 'Unknown')
    
    def _generate_message_template(self, properties: Dict[str, Any], wind_gust: Optional[int], hail_size: Optional[float]) -> str:
        """Generate pre-formatted alert message template"""
        event = properties.get('event', 'Weather Alert')
        area = properties.get('areaDesc', 'Unknown Area')
        
        template = f"{event} for {area}"
        
        if wind_gust:
            template += f" - Wind gusts to {wind_gust} mph"
        
        if hail_size:
            if hail_size >= 1.0:
                template += f" - Hail up to {hail_size} inch diameter"
            else:
                template += f" - Hail up to {hail_size} inch"
        
        return template
    
    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """Parse NWS datetime strings"""
        if not time_str:
            return None
        
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return None
    
    def _calculate_statistics(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate alert statistics for dashboard"""
        total_alerts = len(alerts)
        hail_alerts = sum(1 for alert in alerts if alert.get('max_hail_size', 0) > 0)
        wind_alerts = sum(1 for alert in alerts if alert.get('max_wind_gust', 0) > 0)
        states_affected = len(set(state for alert in alerts for state in alert.get('affected_states', [])))
        
        return {
            'total_alerts': total_alerts,
            'hail_alerts': hail_alerts,
            'wind_alerts': wind_alerts,
            'states_affected': states_affected,
            'radar_indicated': sum(1 for alert in alerts if alert.get('radar_indicated_event', False))
        }
    
    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response structure"""
        return {
            'alerts': [],
            'total_count': 0,
            'statistics': {
                'total_alerts': 0,
                'hail_alerts': 0,
                'wind_alerts': 0,
                'states_affected': 0,
                'radar_indicated': 0
            },
            'last_updated': datetime.now().isoformat(),
            'states_filtered': [],
            'source': 'live_nws_with_state_filtering'
        }
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
            
            hail_description_patterns = [
                r'(pea|peanut|penny|nickel|quarter|half dollar|ping pong ball|golf ball|egg|tennis ball|baseball|large apple|softball|grapefruit)\s*size.*?hail',
                r'hail.*?(pea|peanut|penny|nickel|quarter|half dollar|ping pong ball|golf ball|egg|tennis ball|baseball|large apple|softball|grapefruit)\s*size'
            ]
            
            for pattern in hail_description_patterns:
                hail_desc_match = re.search(pattern, description, re.IGNORECASE)
                if hail_desc_match:
                    size_desc = hail_desc_match.group(1).lower()
                    if size_desc in hail_size_map:
                        hail_size = max(hail_size, hail_size_map[size_desc])
            
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
        
        # Apply radar alert criteria: ANY hail OR ANY wind ≥ 30 mph (show all radar-indicated events)
        is_radar_indicated = (hail_size > 0) or (wind_speed >= 30)
        
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