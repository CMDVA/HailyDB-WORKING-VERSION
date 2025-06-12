from app import db
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Column, String, Text, DateTime, Date, Boolean, func, Index, UniqueConstraint
from datetime import datetime
import re

class Alert(db.Model):
    """
    NWS Alert model with full payload storage and enrichment fields
    Based on NWS Alert API schema: https://api.weather.gov/openapi.json
    """
    __tablename__ = "alerts"

    # Core NWS fields
    id = Column(String, primary_key=True)  # Same as properties.id from NWS
    event = Column(String, index=True)     # Event type (e.g., "Tornado Warning")
    severity = Column(String, index=True)  # Severity level
    area_desc = Column(Text)               # Area description
    effective = Column(DateTime)           # When alert becomes effective
    expires = Column(DateTime)             # When alert expires
    sent = Column(DateTime)                # When alert was sent
    
    # JSON storage for complex data
    geometry = Column(JSONB)               # Store full geometry block
    properties = Column(JSONB)             # Store all original NWS fields
    raw = Column(JSONB)                    # Entire feature object

    # AI Enrichment Fields
    ai_summary = Column(Text)              # AI-generated summary
    ai_tags = Column(JSONB)                # List of classified tags
    
    # SPC Cross-referencing
    spc_verified = Column(Boolean, default=False)
    spc_reports = Column(JSONB)            # List of matching SPC reports
    spc_confidence_score = Column(db.Float) # Match confidence (0.0-1.0)
    spc_match_method = Column(String(10))   # "fips", "latlon", "none"
    spc_report_count = Column(db.Integer, default=0)
    spc_ai_summary = Column(Text)          # AI-generated verification summary
    
    # Radar Indicated Parsing (Feature 1)
    radar_indicated = Column(JSONB)        # {"hail_inches": float, "wind_mph": int}
    
    # Full Geometry & County Mapping (Feature 3)
    fips_codes = Column(JSONB)             # List of FIPS county codes from geometry
    county_names = Column(JSONB)           # Extracted county names with state mapping
    city_names = Column(ARRAY(String))     # Extracted city names from area_desc for enhanced targeting
    geometry_type = Column(String(20))     # "Polygon", "MultiPolygon", "Point"
    coordinate_count = Column(db.Integer)  # Number of coordinate pairs for complexity analysis
    affected_states = Column(JSONB)        # List of state abbreviations
    geometry_bounds = Column(JSONB)        # {"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}

    # Metadata
    ingested_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Database indexes for location-based queries and performance
    __table_args__ = (
        Index('idx_alert_area_desc', 'area_desc'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_event', 'event'),
        Index('idx_alert_effective', 'effective'),
        Index('idx_alert_expires', 'expires'),
        Index('idx_alert_ingested_at_desc', 'ingested_at'),  # Optimized for recent queries
        Index('idx_alert_active', 'effective', 'expires'),
        Index('idx_alert_spc_verified', 'spc_verified'),  # For verification tracking
    )

    def __repr__(self):
        return f'<Alert {self.id}: {self.event}>'
    
    def to_dict(self):
        """Convert alert to dictionary for JSON serialization"""
        # Process county_names to create a proper state-to-counties mapping
        county_mapping = {}
        if self.county_names and isinstance(self.county_names, list):
            for item in self.county_names:
                if isinstance(item, dict) and 'state' in item and 'county' in item:
                    state = item['state']
                    county = item['county']
                    if state not in county_mapping:
                        county_mapping[state] = []
                    if county not in county_mapping[state]:
                        county_mapping[state].append(county)
        
        return {
            'id': self.id,
            'event': self.event,
            'severity': self.severity,
            'area_desc': self.area_desc,
            'effective': self.effective.isoformat() if self.effective else None,
            'expires': self.expires.isoformat() if self.expires else None,
            'sent': self.sent.isoformat() if self.sent else None,
            'geometry': self.geometry,
            'properties': self.properties,
            'ai_summary': self.ai_summary,
            'ai_tags': self.ai_tags,
            'spc_verified': self.spc_verified,
            'spc_reports': self.spc_reports,
            'spc_confidence_score': self.spc_confidence_score,
            'spc_match_method': self.spc_match_method,
            'spc_report_count': self.spc_report_count,
            'spc_ai_summary': self.spc_ai_summary,
            'radar_indicated': self.radar_indicated,  # Feature 1: Radar-indicated parsing
            'fips_codes': self.fips_codes,            # Feature 3: FIPS county codes
            'county_names': county_mapping,           # Feature 3: County-state mapping (processed)
            'city_names': self.city_names,            # City names extracted from area_desc
            'geometry_type': self.geometry_type,      # Feature 3: Geometry classification
            'coordinate_count': self.coordinate_count, # Feature 3: Complexity analysis
            'affected_states': self.affected_states,  # Feature 3: State list
            'geometry_bounds': self.geometry_bounds,  # Feature 3: Coordinate bounds
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'duration_minutes': self.duration_minutes,
            'location_info': self.get_location_info(),
            'enhanced_geometry': self.get_enhanced_geometry_info(),  # Feature 3: Comprehensive geometry data
            'geocode': self.properties.get('geocode') if self.properties else None  # Add geocode for fallback parsing
        }
    
    @property
    def is_active(self):
        """Check if alert is currently active"""
        now = datetime.utcnow()
        return (self.effective <= now if self.effective else True) and \
               (self.expires > now if self.expires else True)
    
    @property
    def duration_minutes(self):
        """Calculate alert duration in minutes"""
        if not self.effective or not self.expires:
            return None
        return int((self.expires - self.effective).total_seconds() / 60)
    
    def extract_states(self):
        """Extract state codes from area description"""
        if not self.area_desc:
            return []
        
        # Match state abbreviations (e.g., "FL", "CA", "TX")
        state_pattern = r'\b([A-Z]{2})\b'
        states = re.findall(state_pattern, self.area_desc)
        return list(set(states))
    
    def extract_counties(self):
        """Extract county names from area description"""
        if not self.area_desc:
            return []
        
        # Split by semicolon and extract county names before state codes
        areas = self.area_desc.split(';')
        counties = []
        
        for area in areas:
            area = area.strip()
            # Match pattern "County Name, ST"
            county_match = re.match(r'^([^,]+),\s*([A-Z]{2})$', area)
            if county_match:
                county_name = county_match.group(1).strip()
                # Remove " County" suffix if present
                county_name = re.sub(r'\s+County$', '', county_name)
                counties.append(county_name)
        
        return counties
    
    def get_location_info(self):
        """Get structured location information for API consumption"""
        return {
            'states': self.extract_states(),
            'counties': self.extract_counties(),
            'area_description': self.area_desc,
            'geocodes': self.properties.get('geocode', {}) if self.properties else {},
            'affected_zones': self.properties.get('affectedZones', []) if self.properties else [],
            'fips_codes': self.fips_codes or [],
            'geometry_type': self.geometry_type,
            'coordinate_count': self.coordinate_count,
            'geometry_bounds': self.geometry_bounds
        }
    
    def process_full_geometry(self):
        """
        Process full geometry data for Feature 3: Full Geometry & County Mapping
        Extracts FIPS codes, county mappings, geometry analysis, and coordinate bounds
        """
        if not self.geometry:
            return
            
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Determine geometry type
            geom_type = self.geometry.get('type', 'Unknown')
            self.geometry_type = geom_type
            
            # Extract coordinates and calculate bounds
            coordinates = self.geometry.get('coordinates', [])
            coord_count, bounds = self._analyze_coordinates(coordinates, geom_type)
            self.coordinate_count = coord_count
            self.geometry_bounds = bounds
            
            # Extract FIPS codes from properties if available
            fips_codes = []
            if self.properties:
                # Look for FIPS codes in various property fields
                geocode = self.properties.get('geocode', {})
                if isinstance(geocode, dict):
                    # FIPS codes may be in UGC (Universal Geographic Code) format
                    ugc = geocode.get('UGC', [])
                    if isinstance(ugc, list):
                        for code in ugc:
                            if isinstance(code, str) and len(code) >= 5:
                                # Extract FIPS code (first 5 digits of UGC)
                                fips = code[:5]
                                if fips.isdigit():
                                    fips_codes.append(fips)
                
                # Also check for direct FIPS references
                fips_prop = self.properties.get('FIPS', [])
                if isinstance(fips_prop, list):
                    fips_codes.extend([str(f) for f in fips_prop if str(f).isdigit()])
            
            self.fips_codes = list(set(fips_codes)) if fips_codes else []
            
            # Enhanced county and state extraction
            self._extract_enhanced_location_data()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error processing geometry for alert {self.id}: {e}")
    
    def _analyze_coordinates(self, coordinates, geom_type):
        """Analyze coordinate structure and calculate bounds"""
        coord_count = 0
        min_lat = min_lon = float('inf')
        max_lat = max_lon = float('-inf')
        
        def process_coord_pair(coord_pair):
            nonlocal coord_count, min_lat, max_lat, min_lon, max_lon
            if isinstance(coord_pair, list) and len(coord_pair) >= 2:
                lon, lat = coord_pair[0], coord_pair[1]
                if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
                    coord_count += 1
                    min_lon = min(min_lon, lon)
                    max_lon = max(max_lon, lon)
                    min_lat = min(min_lat, lat)
                    max_lat = max(max_lat, lat)
        
        def process_coordinates_recursive(coords):
            if not isinstance(coords, list):
                return
            
            # Check if this is a coordinate pair [lon, lat]
            if len(coords) == 2 and all(isinstance(x, (int, float)) for x in coords):
                process_coord_pair(coords)
            else:
                # Recursively process nested coordinate structures
                for item in coords:
                    if isinstance(item, list):
                        process_coordinates_recursive(item)
        
        process_coordinates_recursive(coordinates)
        
        bounds = None
        if coord_count > 0 and min_lat != float('inf'):
            bounds = {
                'min_lat': min_lat,
                'max_lat': max_lat,
                'min_lon': min_lon,
                'max_lon': max_lon
            }
        
        return coord_count, bounds
    
    def _extract_enhanced_location_data(self):
        """Extract enhanced county and state information"""
        # Extract from area description
        states = self.extract_states()
        counties = self.extract_counties()
        
        # Build county-state mapping
        county_state_mapping = []
        if self.area_desc:
            # Parse format like "Barton, KS; Rice, KS"
            parts = self.area_desc.split(';')
            for part in parts:
                part = part.strip()
                if ',' in part:
                    county_part, state_part = part.rsplit(',', 1)
                    county_name = county_part.strip()
                    state_code = state_part.strip()
                    if len(state_code) == 2:  # Valid state abbreviation
                        county_state_mapping.append({
                            'county': county_name,
                            'state': state_code
                        })
        
        self.county_names = county_state_mapping
        self.affected_states = states
    
    def get_enhanced_geometry_info(self):
        """Get comprehensive geometry information for API responses"""
        return {
            'geometry_type': self.geometry_type,
            'coordinate_count': self.coordinate_count,
            'geometry_bounds': self.geometry_bounds,
            'fips_codes': self.fips_codes or [],
            'county_state_mapping': self.county_names or [],
            'affected_states': self.affected_states or [],
            'has_detailed_geometry': bool(self.geometry and self.coordinate_count),
            'coverage_area_sq_degrees': self._calculate_coverage_area() if self.geometry_bounds else None
        }
    
    def _calculate_coverage_area(self):
        """Calculate approximate coverage area in square degrees"""
        if not self.geometry_bounds:
            return None
        
        try:
            bounds = self.geometry_bounds
            lat_diff = bounds['max_lat'] - bounds['min_lat']
            lon_diff = bounds['max_lon'] - bounds['min_lon']
            return round(lat_diff * lon_diff, 6)
        except (KeyError, TypeError):
            return None

class IngestionLog(db.Model):
    """
    Log of ingestion attempts for monitoring and debugging
    """
    __tablename__ = "ingestion_logs"
    
    id = Column(db.Integer, primary_key=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    success = Column(Boolean, default=False)
    alerts_processed = Column(db.Integer, default=0)
    new_alerts = Column(db.Integer, default=0)
    updated_alerts = Column(db.Integer, default=0)
    error_message = Column(Text)
    
    def __repr__(self):
        return f'<IngestionLog {self.id}: {self.success}>'


class SPCReport(db.Model):
    """
    Storm Prediction Center report model for verification
    Stores tornado, wind, and hail reports from SPC daily files
    """
    __tablename__ = "spc_reports"

    id = Column(db.Integer, primary_key=True)
    report_date = Column(Date, nullable=False, index=True)  # YYMMDD from filename
    report_type = Column(String(10), nullable=False, index=True)  # tornado, wind, hail
    time_utc = Column(String(4))  # HHMM format from CSV
    location = Column(String(100))
    county = Column(String(50), index=True)
    state = Column(String(2), index=True)
    latitude = Column(db.Float)
    longitude = Column(db.Float)
    comments = Column(Text)
    
    # Type-specific fields stored as JSON for flexibility
    magnitude = Column(JSONB)  # {f_scale: int} or {speed: int} or {size: int}
    
    # Tracking fields
    raw_csv_line = Column(Text)  # Store original CSV line for audit
    row_hash = Column(String(64), unique=True)  # SHA256 hash for strict duplicate detection
    ingested_at = Column(DateTime, server_default=func.now())
    
    # SPC Report Enrichment
    spc_enrichment = Column(JSONB, default=lambda: {})  # Contextual enrichment data
    enhanced_context = Column(JSONB, default=lambda: {})  # Enhanced multi-alert context
    enhanced_context_version = Column(String, nullable=True)  # Track AI model/prompt version
    enhanced_context_generated_at = Column(DateTime, nullable=True)  # Track generation timestamp
    
    # SPC Verification Status  
    spc_verified = Column(Boolean, default=False, index=True)  # Whether this report has verified alerts
    
    __table_args__ = (
        Index('idx_spc_date_type', 'report_date', 'report_type'),
        Index('idx_spc_location', 'state', 'county'),
        Index('idx_spc_coords', 'latitude', 'longitude'),
        Index('idx_spc_duplicate_detection', 'report_date', 'report_type', 'time_utc', 'location', 'county', 'state'),
        # Hash-based duplicate prevention - safer than raw CSV line comparison
        UniqueConstraint('row_hash', name='uq_spc_report_hash'),
    )

    def __repr__(self):
        return f'<SPCReport {self.report_type} {self.report_date} {self.location}>'

    def to_dict(self):
        """Convert SPC report to dictionary"""
        return {
            'id': self.id,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'report_type': self.report_type,
            'time_utc': self.time_utc,
            'location': self.location,
            'county': self.county,
            'state': self.state,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'magnitude': self.magnitude,
            'comments': self.comments,
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None
        }


class SPCIngestionLog(db.Model):
    """
    Log of SPC report ingestion attempts
    """
    __tablename__ = "spc_ingestion_logs"

    id = Column(db.Integer, primary_key=True)
    report_date = Column(Date, nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    success = Column(Boolean, default=False)
    tornado_reports = Column(db.Integer, default=0)
    wind_reports = Column(db.Integer, default=0)
    hail_reports = Column(db.Integer, default=0)
    total_reports = Column(db.Integer, default=0)
    error_message = Column(Text)
    url_attempted = Column(String(200))

    def __repr__(self):
        return f'<SPCIngestionLog {self.report_date}: {self.success}>'

class SchedulerLog(db.Model):
    """
    Autonomous operation tracking for scheduler metadata
    Logs all automated ingestion attempts regardless of trigger method
    """
    __tablename__ = "scheduler_logs"
    
    id = Column(db.Integer, primary_key=True)
    operation_type = Column(String(50), nullable=False, index=True)  # 'nws_poll', 'spc_poll', 'spc_match'
    trigger_method = Column(String(20), nullable=False)  # 'manual', 'external_cron', 'internal_timer'
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    success = Column(Boolean, default=False)
    records_processed = Column(db.Integer, default=0)
    records_new = Column(db.Integer, default=0)
    error_message = Column(Text)
    operation_metadata = Column(JSONB)  # Operation-specific data
    
    # Enhanced error tracking
    error_details = Column(JSONB)  # Detailed error breakdown
    failed_alert_ids = Column(JSONB)  # List of specific alert IDs that failed
    duplicate_count = Column(db.Integer, default=0)  # Number of duplicates encountered
    http_status_code = Column(db.Integer)  # HTTP response code from NWS API
    api_response_size = Column(db.Integer)  # Size of API response
    processing_duration = Column(db.Float)  # Duration in seconds
    
    def __repr__(self):
        return f'<SchedulerLog {self.id}: {self.operation_type} - {self.success}>'

class WebhookRule(db.Model):
    """
    Webhook registration and dispatch rules for real-time notifications
    Supports hail, wind, and damage probability triggers
    """
    __tablename__ = "webhook_rules"
    
    id = Column(db.Integer, primary_key=True)
    user_id = Column(String(50), index=True)  # For multi-tenant support
    webhook_url = Column(String(500), nullable=False)
    event_type = Column(String(20), nullable=False, index=True)  # hail, wind, damage_probability
    threshold_value = Column(db.Float, nullable=False)
    location_filter = Column(String(100))  # FIPS code, county name, or state
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_webhook_threshold', 'event_type', 'threshold_value'),
    )
    
    def __repr__(self):
        return f'<WebhookRule {self.id}: {self.event_type} >= {self.threshold_value} -> {self.webhook_url}>'
    
    def to_dict(self):
        """Convert webhook rule to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'webhook_url': self.webhook_url,
            'event_type': self.event_type,
            'threshold_value': self.threshold_value,
            'location_filter': self.location_filter,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WebhookEvent(db.Model):
    """
    Track webhook dispatches and delivery status for audit trail
    Records all webhook attempts with payload details
    """
    __tablename__ = "webhook_events"
    
    id = Column(db.Integer, primary_key=True)
    webhook_rule_id = Column(db.Integer, db.ForeignKey('webhook_rules.id'), nullable=False)
    alert_id = Column(String(255), db.ForeignKey('alerts.id'), nullable=False)
    user_id = Column(String(50), index=True)
    event_type = Column(String(20), nullable=False, index=True)
    threshold_value = Column(db.Float)
    actual_value = Column(db.Float)  # The actual hail/wind measurement
    webhook_url = Column(String(500), nullable=False)
    location_data = Column(JSONB)  # Granular location: FIPS, city, coordinates
    payload = Column(JSONB)  # Complete webhook payload sent
    dispatched_at = Column(DateTime, server_default=func.now(), index=True)
    http_status_code = Column(db.Integer)
    response_time_ms = Column(db.Integer)
    success = Column(Boolean, default=False, index=True)
    error_message = Column(Text)
    retry_count = Column(db.Integer, default=0)
    
    # Relationships
    webhook_rule = db.relationship('WebhookRule', backref='events')
    alert = db.relationship('Alert', backref='webhook_events')
    
    def __repr__(self):
        return f'<WebhookEvent {self.id}: {self.event_type} {self.actual_value} -> {self.success}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'webhook_rule_id': self.webhook_rule_id,
            'alert_id': self.alert_id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'threshold_value': self.threshold_value,
            'actual_value': self.actual_value,
            'webhook_url': self.webhook_url,
            'location_data': self.location_data,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'http_status_code': self.http_status_code,
            'response_time_ms': self.response_time_ms,
            'success': self.success,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }


class HurricaneTrack(db.Model):
    """
    Historical hurricane track data from NOAA sources
    Supports field intelligence for roof/property damage assessment
    """
    __tablename__ = "hurricane_tracks"

    id = Column(db.Integer, primary_key=True)
    storm_id = Column(String, nullable=False, index=True)  # NOAA storm identifier (e.g., AL122022)
    name = Column(String, index=True)  # "Ian"
    year = Column(db.Integer, index=True)
    track_point_index = Column(db.Integer)  # Sequence of point along track
    timestamp = Column(DateTime, index=True)
    lat = Column(db.Float, index=True)
    lon = Column(db.Float, index=True)
    category = Column(String)  # TS, TD, CAT1–5
    wind_mph = Column(db.Integer)
    pressure_mb = Column(db.Integer)
    status = Column(String)  # e.g., 'HU', 'TS', 'EX'
    raw_data = Column(JSONB)  # Preserve full NOAA JSON
    row_hash = Column(String(64), unique=True)  # SHA256 of storm_id + timestamp + lat + lon
    ingested_at = Column(DateTime, server_default=func.now())
    
    # Optional AI summarization field
    ai_summary = Column(Text)

    __table_args__ = (
        Index("idx_storm_id", "storm_id"),
        Index("idx_hurricane_coords", "lat", "lon"),
        Index("idx_hurricane_timestamp", "timestamp"),
        Index("idx_hurricane_year", "year"),
        Index("idx_hurricane_name", "name"),
        UniqueConstraint("row_hash", name="uq_hurricane_track_hash"),
    )
    
    def __repr__(self):
        return f'<HurricaneTrack {self.storm_id}: {self.name} - {self.timestamp}>'
    
    def to_dict(self):
        """Convert hurricane track to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'storm_id': self.storm_id,
            'name': self.name,
            'year': self.year,
            'track_point_index': self.track_point_index,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'lat': self.lat,
            'lon': self.lon,
            'category': self.category,
            'wind_mph': self.wind_mph,
            'pressure_mb': self.pressure_mb,
            'status': self.status,
            'raw_data': self.raw_data,
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'ai_summary': self.ai_summary
        }


class HurricaneCountyImpact(db.Model):
    """
    County-level hurricane impact analysis for insurance and restoration targeting
    Links hurricanes to specific FIPS codes with temporal and wind field data
    """
    __tablename__ = "hurricane_county_impacts"
    
    id = Column(db.Integer, primary_key=True)
    storm_id = Column(String(20), nullable=False, index=True)  # e.g., "AL092022"
    county_fips = Column(String(5), nullable=False, index=True)  # 5-digit FIPS code
    state_code = Column(String(2), nullable=False)  # 2-letter state code
    county_name = Column(String(100))  # County name for readability
    
    # Geographic impact metrics
    min_distance_to_center_miles = Column(db.Numeric(8,2))  # Closest approach distance
    max_wind_mph_observed = Column(db.Integer)  # Highest wind speed affecting county
    in_landfall_zone = Column(Boolean, default=False)  # Direct landfall in county
    wind_field_category = Column(String(10))  # Highest category affecting county (CAT1-5, TS, TD)
    
    # Temporal impact tracking
    first_impact_time = Column(DateTime)  # When storm first affected county
    last_impact_time = Column(DateTime)  # When storm last affected county  
    track_points_in_county = Column(db.Integer, default=0)  # Number of track points within impact radius
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Ensure one record per storm-county combination
    __table_args__ = (
        UniqueConstraint('storm_id', 'county_fips', name='uq_storm_county'),
        Index('idx_county_impact_storm', 'storm_id'),
        Index('idx_county_impact_fips', 'county_fips'),
        Index('idx_county_impact_wind', 'max_wind_mph_observed'),
        Index('idx_county_impact_distance', 'min_distance_to_center_miles'),
    )
    
    def __repr__(self):
        return f'<HurricaneCountyImpact {self.storm_id}: {self.county_fips} - {self.wind_field_category}>'
        
    def to_dict(self):
        """Convert impact record to dictionary for JSON serialization"""
        return {
            'storm_id': self.storm_id,
            'county_fips': self.county_fips,
            'state_code': self.state_code,
            'county_name': self.county_name,
            'min_distance_to_center_miles': float(self.min_distance_to_center_miles) if self.min_distance_to_center_miles else None,
            'max_wind_mph_observed': self.max_wind_mph_observed,
            'in_landfall_zone': self.in_landfall_zone,
            'wind_field_category': self.wind_field_category,
            'first_impact_time': self.first_impact_time.isoformat() if self.first_impact_time else None,
            'last_impact_time': self.last_impact_time.isoformat() if self.last_impact_time else None,
            'track_points_in_county': self.track_points_in_county,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RadarAlert(db.Model):
    """
    Processed radar-detected events for enhanced targeting and API access
    Extracted from NWS alerts with radar_indicated data
    """
    __tablename__ = 'radar_alerts'
    
    id = Column(db.Integer, primary_key=True)
    alert_id = Column(String(255), db.ForeignKey('alerts.id'), nullable=False)
    
    # Event classification
    event_type = Column(String(10), nullable=False)  # 'hail' or 'wind'
    event_date = Column(Date, nullable=False)
    detected_time = Column(DateTime, nullable=False)
    
    # Radar measurements
    hail_inches = Column(db.Numeric(4,2))
    wind_mph = Column(db.Integer)
    
    # Geographic data
    city_names = Column(ARRAY(String))  # Parsed from area_desc
    county_names = Column(ARRAY(String))
    fips_codes = Column(ARRAY(String))
    affected_states = Column(ARRAY(String))
    
    # Geometry (stored as GeoJSON for compatibility)
    geometry = Column(JSONB)
    geometry_bounds = Column(JSONB)  # {min_lat, max_lat, min_lon, max_lon}
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    alert = db.relationship('Alert', backref=db.backref('radar_alerts', lazy='dynamic'))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_radar_alerts_event_date', 'event_date'),
        Index('idx_radar_alerts_event_type', 'event_type'),
        Index('idx_radar_alerts_detected_time', 'detected_time'),
        Index('idx_radar_alerts_hail_inches', 'hail_inches'),
        Index('idx_radar_alerts_wind_mph', 'wind_mph'),
        Index('idx_radar_alerts_city_names', 'city_names', postgresql_using='gin'),
        Index('idx_radar_alerts_county_names', 'county_names', postgresql_using='gin'),
        Index('idx_radar_alerts_fips_codes', 'fips_codes', postgresql_using='gin'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'event_type': self.event_type,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'detected_time': self.detected_time.isoformat() if self.detected_time else None,
            'hail_inches': float(self.hail_inches) if self.hail_inches else None,
            'wind_mph': self.wind_mph,
            'city_names': self.city_names or [],
            'county_names': self.county_names or [],
            'fips_codes': self.fips_codes or [],
            'affected_states': self.affected_states or [],
            'geometry': self.geometry,
            'geometry_bounds': self.geometry_bounds,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<RadarAlert {self.id}: {self.event_type} on {self.event_date}>'
