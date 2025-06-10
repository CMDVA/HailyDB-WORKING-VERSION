from app import db
from sqlalchemy.dialects.postgresql import JSONB
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
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'is_active': self.is_active,
            'duration_minutes': self.duration_minutes,
            'location': self.get_location_info()
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
            'affected_zones': self.properties.get('affectedZones', []) if self.properties else []
        }

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
        Index('idx_webhook_event_location', 'event_type', 'location_filter'),
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
