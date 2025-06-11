# HailyDB v2.0 - Weather Intelligence Platform

## Overview

HailyDB is a comprehensive weather intelligence platform that ingests real-time National Weather Service (NWS) alerts, historical hurricane track data, and Storm Prediction Center (SPC) reports. The platform provides enhanced geographic analysis, AI-powered enrichment, and actionable intelligence for insurance, restoration, and emergency management applications.

## 🌟 Key Features

### Core Data Sources
- **NWS Active Alerts**: Real-time severe weather warnings and watches
- **Hurricane Track Data**: NOAA HURDAT2 historical hurricane tracks (2020-2025)
- **SPC Storm Reports**: Daily tornado, wind, and hail verification data
- **County-Level Analysis**: FIPS-based geographic intelligence for precise targeting

### Advanced Intelligence
- **Radar-Indicated Parsing**: Extract hail size (0.75"-2.0"+) and wind speeds (58-80+ mph)
- **AI Enrichment**: OpenAI-powered summaries and categorization
- **Geographic Processing**: Full geometry analysis with county mapping
- **Real-Time Webhooks**: Automated notifications for threshold events
- **Cross-Verification**: Match NWS alerts with actual SPC storm reports

## 🏗️ System Architecture

### Technology Stack
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with JSONB support
- **APIs**: RESTful endpoints with comprehensive filtering
- **AI Integration**: OpenAI GPT for natural language processing
- **Scheduling**: Autonomous data collection with error recovery

### Database Schema

#### Primary Tables
```sql
-- NWS Alerts with enhanced processing
alerts (
  id, event, severity, area_desc, effective, expires,
  geometry JSONB,           -- Full GeoJSON geometry
  properties JSONB,         -- Complete NWS payload
  radar_indicated JSONB,    -- Parsed hail/wind measurements
  fips_codes JSONB,         -- County FIPS codes
  county_names JSONB,       -- County-state mapping
  geometry_bounds JSONB,    -- Geographic bounds
  ai_summary TEXT,          -- AI-generated summary
  spc_verified BOOLEAN,     -- Storm verification status
  spc_reports JSONB         -- Matching storm reports
)

-- Hurricane track data from NOAA
hurricane_tracks (
  id, storm_id, name, year, track_point_index,
  timestamp, lat, lon, category, wind_mph, pressure_mb,
  status, raw_data JSONB, row_hash
)

-- County-level hurricane impact analysis
hurricane_county_impacts (
  id, storm_id, county_fips, state_code, county_name,
  min_distance_to_center_miles, max_wind_mph_observed,
  in_landfall_zone, wind_field_category,
  first_impact_time, last_impact_time, track_points_in_county
)

-- SPC verification reports
spc_reports (
  id, report_date, report_type, time_utc, location,
  county, state, latitude, longitude, magnitude JSONB,
  comments, row_hash
)
```

## 🚀 API Endpoints

### Base URL
```
https://your-hailydb.replit.app
```

### Weather Alerts

#### Search Alerts
```http
GET /api/alerts/search
```

**Parameters:**
- `state` - Two-letter state code (TX, FL, etc.)
- `county` - County name
- `event_type` - Alert type (Tornado Warning, etc.)
- `severity` - Extreme, Severe, Moderate, Minor
- `active_only` - true/false for current alerts
- `search_query` - Text search in descriptions
- `page` - Page number (default: 1)
- `limit` - Results per page (default: 50, max: 200)

**Example:**
```bash
curl "https://your-app.replit.app/api/alerts/search?state=TX&severity=Severe&active_only=true&limit=25"
```

**Response:**
```json
{
  "total": 147,
  "page": 1,
  "limit": 25,
  "alerts": [{
    "id": "urn:oid:2.49.0.1.840.0...",
    "event": "Severe Thunderstorm Warning",
    "severity": "Moderate",
    "area_desc": "Harris, TX; Montgomery, TX",
    "effective": "2025-06-11T20:15:00Z",
    "expires": "2025-06-11T21:00:00Z",
    "radar_indicated": {
      "hail_inches": 1.25,
      "wind_mph": 70
    },
    "fips_codes": ["48201", "48339"],
    "county_names": [
      {"county": "Harris", "state": "TX"},
      {"county": "Montgomery", "state": "TX"}
    ],
    "geometry_bounds": {
      "min_lat": 30.1234,
      "max_lat": 30.5678,
      "min_lon": -95.9876,
      "max_lon": -95.5432
    },
    "spc_verified": true,
    "spc_confidence_score": 0.89,
    "ai_summary": "Severe thunderstorm with quarter-size hail and 70 mph winds affecting northwestern Harris County.",
    "ai_tags": ["hail", "damaging_winds", "property_damage_risk"]
  }]
}
```

#### Get Specific Alert
```http
GET /api/alerts/{alert_id}
```

**Example:**
```bash
curl "https://your-app.replit.app/api/alerts/urn:oid:2.49.0.1.840.0.abc123"
```

### Hurricane Data

#### Get Hurricane Statistics
```http
GET /internal/hurricane-stats
```

**Response:**
```json
{
  "total_track_points": 1405,
  "unique_storms": 14,
  "year_range": {"min": 2020, "max": 2025},
  "latest_ingestion": "2025-06-11T03:51:37.470510"
}
```

#### Search Hurricane Tracks
```http
GET /api/hurricanes/tracks
```

**Parameters:**
- `storm_id` - NOAA storm identifier (AL122022)
- `name` - Hurricane name (Ian, Milton, etc.)
- `year` - Hurricane season year
- `lat_min/lat_max` - Latitude bounding box
- `lon_min/lon_max` - Longitude bounding box
- `start_date/end_date` - ISO date range
- `limit` - Results limit (default: 100)
- `offset` - Pagination offset

**Example:**
```bash
curl "https://your-app.replit.app/api/hurricanes/tracks?name=Ian&year=2022&limit=50"
```

**Response:**
```json
[{
  "id": 2045,
  "storm_id": "AL142024",
  "name": "MILTON",
  "year": 2024,
  "track_point_index": 2,
  "timestamp": "2024-10-10T00:15:00",
  "lat": 27.3,
  "lon": -82.5,
  "category": "CAT3",
  "wind_mph": 120,
  "pressure_mb": 955,
  "status": "HU",
  "raw_data": {
    "basin": "AL",
    "landfall": "Florida",
    "source": "HURDAT2"
  }
}]
```

#### Geographic Hurricane Search
```http
GET /api/hurricanes/search
```

**Parameters:**
- `lat` - Latitude (required)
- `lon` - Longitude (required)
- `radius` - Search radius in miles (default: 50)

**Example:**
```bash
curl "https://your-app.replit.app/api/hurricanes/search?lat=25.7617&lon=-80.1918&radius=100"
```

**Response:**
```json
[{
  "id": 1995,
  "storm_id": "AL132020",
  "name": "LAURA",
  "category": "CAT4",
  "wind_mph": 130,
  "distance_from_query": 76.6,
  "timestamp": "2020-08-26T00:00:00",
  "lat": 25.0,
  "lon": -81.0
}]
```

#### County Hurricane Impact Analysis
```http
GET /api/hurricanes/county-impacts/{county_fips}
```

**Parameters:**
- `county_fips` - 5-digit FIPS code (required)
- `min_wind` - Minimum wind speed filter
- `category` - Hurricane category (CAT1-CAT5, TS, TD)
- `since_year` - Year filter for recent impacts

**Example:**
```bash
curl "https://your-app.replit.app/api/hurricanes/county-impacts/12086?min_wind=50&since_year=2020"
```

**Response:**
```json
{
  "county_fips": "12086",
  "county_name": "Miami-Dade",
  "state_code": "FL",
  "summary": {
    "total_storms": 6,
    "max_wind_observed": 55,
    "landfall_events": 3,
    "category_distribution": {
      "MINIMAL": 3,
      "TD": 1,
      "TS": 2
    },
    "most_recent_impact": "2020-11-09T00:00:00"
  },
  "impacts": [{
    "storm_id": "AL292020",
    "county_fips": "12086",
    "county_name": "Miami-Dade",
    "state_code": "FL",
    "min_distance_to_center_miles": 52.55,
    "max_wind_mph_observed": 55,
    "in_landfall_zone": true,
    "wind_field_category": "TS",
    "first_impact_time": "2020-11-09T00:00:00",
    "last_impact_time": "2020-11-09T06:00:00",
    "track_points_in_county": 3
  }]
}
```

#### Search County Impacts
```http
GET /api/hurricanes/county-impacts/search
```

**Parameters:**
- `state` - Two-letter state code
- `min_wind` - Minimum wind threshold
- `category` - Hurricane category
- `landfall_only` - true/false
- `since_year` - Year filter
- `limit` - Results limit (max: 500)

**Example:**
```bash
curl "https://your-app.replit.app/api/hurricanes/county-impacts/search?state=FL&min_wind=74&landfall_only=true&limit=100"
```

#### Get Storm County Impacts
```http
GET /api/hurricanes/storms/{storm_id}/county-impacts
```

**Example:**
```bash
curl "https://your-app.replit.app/api/hurricanes/storms/AL142024/county-impacts"
```

**Response:**
```json
{
  "storm_id": "AL142024",
  "summary": {
    "total_counties_affected": 23,
    "landfall_counties": 8,
    "max_wind_observed": 120,
    "states_affected": ["FL"],
    "counties_by_state": {"FL": 23}
  },
  "county_impacts": [...]
}
```

### SPC Reports

#### Search SPC Reports
```http
GET /api/spc/reports
```

**Parameters:**
- `type` - tornado, wind, hail
- `state` - Two-letter state code
- `county` - County name
- `date` - Report date (YYYY-MM-DD)
- `start_date/end_date` - Date range
- `min_magnitude` - Minimum storm intensity
- `limit` - Results limit

**Example:**
```bash
curl "https://your-app.replit.app/api/spc/reports?type=hail&state=TX&min_magnitude=1.0&limit=50"
```

### Webhook System

#### Register Webhook
```http
POST /internal/webhook-rules
```

**Request Body:**
```json
{
  "webhook_url": "https://your-app.com/webhooks/weather",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX",
  "user_id": "your_user_id"
}
```

**Supported Event Types:**
- `hail` - Hail size threshold (inches)
- `wind` - Wind speed threshold (mph)
- `damage_probability` - Damage risk score

#### List Webhooks
```http
GET /internal/webhook-rules?user_id=your_user_id
```

#### Delete Webhook
```http
DELETE /internal/webhook-rules/{webhook_id}
```

### System Status

#### Health Check
```http
GET /internal/status
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-11T03:55:00.123456",
  "database": "healthy",
  "alerts": {
    "total": 1247,
    "recent_24h": 156,
    "active_now": 23
  },
  "hurricanes": {
    "total_tracks": 1405,
    "unique_storms": 14,
    "latest_ingestion": "2025-06-11T03:51:37.470510"
  },
  "spc_verification": {
    "verified_count": 234,
    "unverified_count": 89,
    "coverage_percentage": 72.4
  },
  "ingestion": {
    "last_nws_ingestion": "2025-06-11T03:45:12.597190",
    "last_spc_ingestion": "2025-06-11T03:30:08.366969",
    "failed_jobs_24h": 0
  }
}
```

### Administrative Endpoints

#### Trigger Data Ingestion
```http
POST /internal/nws-poll
POST /internal/spc-poll
POST /internal/hurricane-ingest
```

#### AI Enrichment
```http
POST /api/alerts/enrich-batch
POST /api/alerts/enrich-by-category
```

**Request Body (enrich-by-category):**
```json
{
  "category": "Severe Weather Alert",
  "limit": 100
}
```

#### SPC Verification
```http
GET /internal/spc-verify
GET /api/spc/calendar-verification
```

## 💼 Integration Examples

### Insurance Claims Processing

```python
import requests
from datetime import datetime, timedelta

class HailyDBIntegration:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def get_recent_hail_events(self, state=None, min_size=1.0):
        """Get recent hail events for claims processing"""
        params = {
            'active_only': 'true',
            'limit': 100
        }
        if state:
            params['state'] = state
            
        response = requests.get(f"{self.base_url}/api/alerts/search", params=params)
        alerts = response.json().get('alerts', [])
        
        hail_events = []
        for alert in alerts:
            radar = alert.get('radar_indicated', {})
            if radar.get('hail_inches', 0) >= min_size:
                hail_events.append({
                    'alert_id': alert['id'],
                    'hail_size': radar['hail_inches'],
                    'counties': alert.get('county_names', []),
                    'effective': alert['effective'],
                    'expires': alert['expires']
                })
        
        return hail_events
    
    def get_hurricane_impacts_for_property(self, county_fips, since_year=2020):
        """Get hurricane impact history for property assessment"""
        url = f"{self.base_url}/api/hurricanes/county-impacts/{county_fips}"
        params = {'since_year': since_year}
        
        response = requests.get(url, params=params)
        return response.json()
    
    def search_hurricanes_near_property(self, lat, lon, radius_miles=25):
        """Find hurricanes within radius of property"""
        params = {
            'lat': lat,
            'lon': lon,
            'radius': radius_miles
        }
        
        response = requests.get(f"{self.base_url}/api/hurricanes/search", params=params)
        return response.json()

# Usage example
hailydb = HailyDBIntegration("https://your-app.replit.app")

# Get recent hail events in Texas
hail_events = hailydb.get_recent_hail_events(state="TX", min_size=1.0)

# Check hurricane history for Miami-Dade County
hurricane_impacts = hailydb.get_hurricane_impacts_for_property("12086")

# Search for hurricanes near a specific property
nearby_storms = hailydb.search_hurricanes_near_property(25.7617, -80.1918, 50)
```

### Emergency Management

```python
class EmergencyManagement:
    def __init__(self, hailydb_url, webhook_url):
        self.hailydb = HailyDBIntegration(hailydb_url)
        self.webhook_url = webhook_url
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """Setup webhook monitoring for emergency events"""
        webhook_configs = [
            {
                "webhook_url": f"{self.webhook_url}/tornado-alerts",
                "event_type": "wind",
                "threshold_value": 80,
                "user_id": "emergency_mgmt"
            },
            {
                "webhook_url": f"{self.webhook_url}/hail-alerts", 
                "event_type": "hail",
                "threshold_value": 1.75,
                "user_id": "emergency_mgmt"
            }
        ]
        
        for config in webhook_configs:
            requests.post(f"{self.hailydb.base_url}/internal/webhook-rules", json=config)
    
    def get_active_severe_weather(self):
        """Get current severe weather affecting jurisdiction"""
        params = {
            'active_only': 'true',
            'severity': 'Severe',
            'limit': 50
        }
        
        response = requests.get(f"{self.hailydb.base_url}/api/alerts/search", params=params)
        return response.json()
```

### Restoration Contractor

```python
class RestorationIntelligence:
    def __init__(self, hailydb_url):
        self.hailydb = HailyDBIntegration(hailydb_url)
    
    def find_damage_opportunities(self, states, min_hail_size=1.0):
        """Find recent hail damage opportunities"""
        opportunities = []
        
        for state in states:
            hail_events = self.hailydb.get_recent_hail_events(state, min_hail_size)
            for event in hail_events:
                opportunities.append({
                    'state': state,
                    'counties': event['counties'],
                    'hail_size': event['hail_size'],
                    'event_time': event['effective'],
                    'damage_potential': self.calculate_damage_potential(event['hail_size'])
                })
        
        return sorted(opportunities, key=lambda x: x['damage_potential'], reverse=True)
    
    def calculate_damage_potential(self, hail_size):
        """Calculate damage potential score"""
        if hail_size >= 2.0:
            return 10  # Severe damage expected
        elif hail_size >= 1.5:
            return 8   # Significant damage likely
        elif hail_size >= 1.0:
            return 6   # Moderate damage possible
        else:
            return 3   # Minor damage possible
    
    def get_hurricane_restoration_opportunities(self, state, min_wind=74):
        """Find counties with recent hurricane damage"""
        params = {
            'state': state,
            'min_wind': min_wind,
            'landfall_only': 'true',
            'limit': 100
        }
        
        response = requests.get(
            f"{self.hailydb.base_url}/api/hurricanes/county-impacts/search",
            params=params
        )
        
        return response.json()
```

## 🚀 Quick Start

### Environment Setup

```bash
# Clone or download the project
git clone https://github.com/your-org/hailydb.git
cd hailydb

# Set environment variables
export DATABASE_URL="postgresql://user:password@host:port/database"
export OPENAI_API_KEY="sk-your-openai-key"
export SESSION_SECRET="your-session-secret"

# Install dependencies (handled automatically by Replit)
# pip install -r requirements.txt

# Start the application
python main.py
```

### Database Initialization

The database schema is created automatically on first run. No manual setup required.

### Immediate Data Access

```bash
# Check system status
curl "https://your-app.replit.app/internal/status"

# Get recent alerts
curl "https://your-app.replit.app/api/alerts/search?limit=10"

# Get hurricane statistics
curl "https://your-app.replit.app/internal/hurricane-stats"

# Search hurricane impacts for Miami-Dade County
curl "https://your-app.replit.app/api/hurricanes/county-impacts/12086"
```

## 📊 Data Coverage

### Current Data Inventory

#### Hurricane Tracks
- **Time Range**: 2020-2025
- **Total Storms**: 14 major hurricanes
- **Track Points**: 1,405+ individual track points
- **Coverage**: US-impacting storms with landfall data
- **Sources**: NOAA HURDAT2 database

#### NWS Alerts
- **Real-Time**: Active alerts nationwide
- **Coverage**: All NWS alert types and severities
- **Enhancement**: Radar-indicated measurements
- **Verification**: Cross-referenced with SPC reports

#### SPC Reports
- **Daily Updates**: Tornado, wind, and hail reports
- **Geographic**: Full US coverage with coordinates
- **Verification**: Match alerts with actual storm reports
- **Historical**: Automated backfill capabilities

### Geographic Intelligence

#### County-Level Analysis
- **FIPS Codes**: 5-digit county identifiers
- **Hurricane Impacts**: Distance, wind speed, landfall status
- **Temporal Tracking**: First/last impact times
- **Category Analysis**: Storm intensity by county

#### Coordinate Systems
- **Projection**: WGS84 (EPSG:4326)
- **Precision**: 6 decimal places (~0.1 meter accuracy)
- **Bounding Boxes**: Calculated geometry bounds
- **Distance Calculations**: Haversine formula for accuracy

## 🔧 Advanced Configuration

### Webhook Configuration

```json
{
  "webhook_url": "https://your-app.com/webhooks/hail",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX",
  "user_id": "your_application_id"
}
```

### Performance Optimization

#### Database Indexes
```sql
-- Optimized for common query patterns
CREATE INDEX idx_alert_severity ON alerts(severity);
CREATE INDEX idx_alert_effective ON alerts(effective);
CREATE INDEX idx_hurricane_coords ON hurricane_tracks(lat, lon);
CREATE INDEX idx_county_impact_fips ON hurricane_county_impacts(county_fips);
```

#### Query Performance
- **Pagination**: Use `limit` and `offset` for large result sets
- **Filtering**: Combine multiple filters to reduce result size
- **Caching**: Results cached for 5 minutes for repeated queries

### Error Handling

All API endpoints return standardized error responses:

```json
{
  "error": "Description of the error",
  "code": "ERROR_CODE",
  "timestamp": "2025-06-11T12:00:00Z"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (invalid endpoint or resource)
- `500` - Internal Server Error

## 🔍 Data Quality Assurance

### Duplicate Detection
- **Hurricane Tracks**: SHA256 hash of storm_id + timestamp + coordinates
- **SPC Reports**: Content-based hashing of full CSV lines
- **NWS Alerts**: NWS-provided unique identifiers

### Data Validation
- **Coordinate Bounds**: Validate lat/lon within reasonable ranges
- **Timestamp Parsing**: RFC 3339 compliant datetime handling
- **FIPS Validation**: 5-digit county code format verification

### Cross-Verification
- **SPC Matching**: Geographic proximity and temporal correlation
- **Confidence Scoring**: 0.9 for FIPS match, 0.7 for proximity
- **Manual Override**: Administrative controls for data correction

## 📈 Monitoring and Maintenance

### Health Monitoring
- **Database Connectivity**: Real-time connection status
- **Ingestion Status**: Last successful data updates
- **Error Tracking**: Failed operations with detailed logging

### Automated Operations
- **NWS Polling**: Manual trigger via web interface
- **SPC Collection**: Daily storm report ingestion
- **Hurricane Updates**: Periodic HURDAT2 synchronization

### Logging
All operations logged with:
- Timestamp and operation type
- Success/failure status
- Record counts and processing statistics
- Detailed error messages for troubleshooting

## 🤝 Developer Support

### AI Agent Integration

This API is designed for seamless integration with AI coding agents like Replit Agent. All endpoints follow RESTful conventions with consistent parameter naming and response formats.

### Example Prompts for AI Agents

```
"Get all hail events larger than 1 inch in Texas from the last 24 hours"
"Find hurricane impacts for Miami-Dade County since 2020" 
"Search for severe weather alerts within 50 miles of Houston"
"Set up a webhook for hail events over 1.5 inches in Florida"
```

### Testing Endpoints

Use the provided curl examples to test all functionality:

```bash
# Test basic connectivity
curl "https://your-app.replit.app/internal/status"

# Test alert search
curl "https://your-app.replit.app/api/alerts/search?limit=5"

# Test hurricane data
curl "https://your-app.replit.app/api/hurricanes/tracks?limit=5"

# Test county impact analysis
curl "https://your-app.replit.app/api/hurricanes/county-impacts/12086"
```

### Support Resources

- **API Documentation**: This README provides complete endpoint documentation
- **Error Codes**: Standardized error responses with descriptive messages
- **Example Code**: Python integration examples for common use cases
- **Health Checks**: Built-in monitoring endpoints for system status

---

## 🏷️ Version Information

**Version**: 2.0  
**Last Updated**: June 2025  
**Compatibility**: Python 3.11+, PostgreSQL 12+  
**API Version**: RESTful JSON (no versioning required)

For technical support or feature requests, monitor the application logs via `/internal/status` endpoint and use the provided health monitoring tools.