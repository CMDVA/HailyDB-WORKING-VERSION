# HailyDB v2.0 - Core Stability Upgrade

## Overview

HailyDB is a comprehensive National Weather Service (NWS) Alert Ingestion Platform designed for real-time weather data processing and verification. The v2.0 core upgrade implements enhanced stability, autonomous operation monitoring, and comprehensive data integrity verification.

## System Architecture

### Core Components

- **Flask Backend**: RESTful API with SQLAlchemy ORM
- **PostgreSQL Database**: Comprehensive alert storage with JSONB fields
- **NWS Alert Ingestion**: Real-time polling from weather.gov APIs
- **SPC Report Integration**: Storm Prediction Center data cross-referencing
- **AI Enrichment**: OpenAI-powered alert summarization and tagging
- **Admin Dashboard**: Real-time monitoring and control interface

### Key Features

✅ **Autonomous Ingestion**: Self-sustaining data collection with error recovery
✅ **Data Integrity Verification**: Cross-reference NWS alerts with actual SPC reports
✅ **Comprehensive Monitoring**: Operation logging and health status tracking
✅ **Geographic Intelligence**: County FIPS and proximity-based alert matching
✅ **Production Ready**: Robust error handling and session management

## Database Schema

### Core Tables

#### `alerts` - NWS Alert Storage
- Full NWS alert payload with JSONB storage
- AI-generated summaries and tags
- SPC verification fields and confidence scores
- Geographic and temporal indexing

#### `spc_reports` - Storm Prediction Center Data
- Tornado, wind, and hail reports from SPC CSV files
- Geographic coordinates and FIPS county mapping
- Original CSV line preservation for audit trails

#### `scheduler_logs` - Operation Tracking
- Comprehensive logging of all ingestion operations
- Success/failure tracking with error messages
- Trigger method identification (manual, external, timer)

## API Endpoints

### Public API
- `GET /alerts` - Query alerts with filtering
- `GET /alerts/{id}` - Individual alert details
- `GET /alerts/summaries` - AI-generated summaries
- `GET /spc/reports` - Storm Prediction Center reports

### Internal Monitoring
- `GET /internal/status` - Comprehensive health status
- `GET /internal/dashboard` - Administrative interface
- `POST /internal/spc-reupload/{date}` - Force SPC data re-ingestion

### Alert Summaries
- **GET** `/alerts/summary` - AI-enriched alert summaries and verification data

### SPC Verified Matches
- **GET** `/spc-matches` - Web interface for verified alert matches
- **GET** `/spc-matches/data` - API data for verified matches with filtering

### AI Enrichment
- **POST** `/api/alerts/enrich-batch` - Batch enrichment of unenriched alerts
- **POST** `/api/alerts/enrich-by-category` - Category-specific enrichment
- **POST** `/api/alerts/enrich-priority` - Priority alert enrichment
- **GET** `/api/alerts/enrichment-stats` - Enrichment coverage statistics
- **GET** `/api/alerts/unenriched-counts` - Counts of unenriched alerts by category

### SPC Data Verification
- **GET** `/internal/spc-verify` - Data integrity verification interface
- **GET** `/api/spc/calendar-verification` - 2-month verification calendar data
- **GET** `/internal/spc-verify-today` - Recent verification data for dashboard

### System Status
- **GET** `/internal/status` - Comprehensive system health and metrics

### Health Status Response
```json
{
  "status": "healthy",
  "timestamp": "2025-06-03T19:03:30.123456",
  "database": "healthy",
  "alerts": {
    "total": 393,
    "recent_24h": 393,
    "active_now": 15
  },
  "spc_verification": {
    "verified_count": 0,
    "unverified_count": 393,
    "coverage_percentage": 0.0,
    "oldest_unverified": "2025-06-01T11:30:00"
  },
  "ingestion": {
    "last_nws_ingestion": "2025-06-03T00:14:52.597190",
    "last_spc_ingestion": "2025-06-03T15:46:38.366969",
    "failed_jobs_24h": 0
  },
  "scheduler_operations": {
    "total_operations_24h": 0,
    "successful_operations_24h": 0,
    "failed_operations_24h": 0
  }
}
```

## Data Sources

### NWS Alert API
- **Endpoint**: `https://api.weather.gov/alerts/active`
- **Format**: GeoJSON with comprehensive alert metadata
- **Polling**: Manual triggers via web interface
- **Coverage**: Nationwide real-time weather alerts

### SPC Storm Reports
- **Endpoint**: `https://www.spc.noaa.gov/climo/reports/YYMMDD_rpts_filtered.csv`
- **Format**: Multi-section CSV (tornado, wind, hail)
- **Coverage**: Historical storm verification data
- **Matching**: Geographic proximity and temporal correlation

## Example Usage:
```
GET https://your-app.replit.app/api/alerts/active
GET https://your-app.replit.app/api/alerts/search?state=TX&severity=Severe&active_only=true
GET https://your-app.replit.app/api/spc/reports?type=tornado&state=KS&date=2025-01-15
GET https://your-app.replit.app/spc-matches/data?hours=168&confidence=high
GET https://your-app.replit.app/api/alerts/enrichment-stats
POST https://your-app.replit.app/api/alerts/enrich-by-category (JSON: {"category": "Severe Weather Alert"})
```

## Deployment

### Environment Requirements
- Python 3.11+
- PostgreSQL database
- OpenAI API key for enrichment

### Required Environment Variables
```bash
DATABASE_URL=postgresql://user:password@host:port/database
OPENAI_API_KEY=sk-...
SESSION_SECRET=your-session-secret
```

### Installation
```bash
# Dependencies are managed via pyproject.toml
pip install -e .

# Database initialization is automatic on first run
python main.py
```

### Server Startup
```bash
# Development
python main.py

# Production
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Data Integrity Features

### SPC Verification Process
1. **Geographic Matching**: County FIPS codes and 25-mile radius proximity
2. **Temporal Correlation**: ±2 hour window from alert effective time
3. **Event Type Mapping**: Tornado → Warning/Watch, Wind/Hail → Severe T-storm
4. **Confidence Scoring**: 0.9 for FIPS match, 0.7 for proximity match

### Error Recovery
- Automatic session rollback on database errors
- Comprehensive operation logging for audit trails
- Graceful degradation on API failures
- Duplicate detection using full CSV content comparison

### Data Quality Assurance
- Null character sanitization for PostgreSQL compatibility
- UNK value preservation for incomplete storm reports
- Transaction-safe re-upload functionality
- Comprehensive logging of all data modifications

## Monitoring and Diagnostics

### Real-time Metrics
- Alert ingestion rates and success ratios
- SPC verification coverage percentages
- Active alert counts and geographic distribution
- Database health and connection status

### Administrative Controls
- Manual trigger system for precise operation control
- Force re-ingestion capabilities for data correction
- Comprehensive error logging and recovery tracking
- Historical operation statistics and trends

## Architecture Decisions

### Why Manual Triggers Over APScheduler
- **Visibility**: Real-time monitoring of all operations
- **Control**: Precise timing and resource management
- **Reliability**: No scheduler conflicts in containerized environments
- **Recovery**: Easy intervention and correction capabilities

### Why PostgreSQL JSONB
- **Flexibility**: Store complete NWS payloads without schema constraints
- **Performance**: Indexed JSON queries for complex filtering
- **Integrity**: ACID compliance with complex nested data
- **Scalability**: Efficient storage and retrieval of large documents

### Why Current Coordinate Math Over External Libraries
- **Performance**: Direct haversine calculations without library overhead
- **Simplicity**: Deterministic and explainable geographic matching
- **Reliability**: No external dependencies for critical functionality
- **Maintenance**: Self-contained logic with clear debugging capabilities

## Production Readiness

✅ **Error Handling**: Comprehensive exception catching and logging
✅ **Session Management**: Proper database transaction handling
✅ **Data Validation**: Input sanitization and type checking
✅ **Performance Optimization**: Strategic database indexing
✅ **Monitoring**: Health checks and operation tracking
✅ **Documentation**: Complete API and architecture documentation

## Support and Maintenance

### Log Analysis
All operations are logged with timestamps, success indicators, and detailed error messages. Monitor `/internal/status` for real-time system health.

### Data Recovery
Force re-ingestion capabilities allow correction of data integrity issues. Use SPC verification dashboard to identify and resolve mismatches.

### Performance Tuning
Database indexes are optimized for common query patterns. Monitor query performance and adjust indexing strategy as data volume grows.

---

## 🔌 API Integration Guide

A comprehensive guide for integrating external applications with HailyDB's enhanced weather alert intelligence platform.

### Overview

HailyDB provides real-time National Weather Service (NWS) alert data enriched with AI analysis, radar-indicated measurements, SPC verification, and comprehensive geometry processing. This guide demonstrates how to leverage HailyDB's API for insurance claims, field operations, emergency management, and partner integrations.

### Core API Endpoints

#### Get Recent Alerts
```bash
curl "https://your-hailydb.com/api/alerts/search?limit=50&active_only=true"
```

#### Search by Location
```bash
curl "https://your-hailydb.com/api/alerts/search?state=TX&county=Harris&limit=25"
```

#### Filter by Event Type and Severity
```bash
curl "https://your-hailydb.com/api/alerts/search?event_type=Tornado%20Warning&severity=Extreme&limit=10"
```

#### Get Specific Alert Details
```bash
curl "https://your-hailydb.com/api/alerts/{alert_id}"
```

### Real-Time Webhook Integration

#### Register Webhook for Hail Events
```bash
curl -X POST "https://your-hailydb.com/internal/webhook-rules" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-app.com/webhooks/hail-alerts",
    "event_type": "hail",
    "threshold_value": 1.0,
    "location_filter": "TX",
    "user_id": "your_user_id"
  }'
```

### Enhanced Data Structure

#### Alert Response Format

```json
{
  "id": "urn:oid:2.49.0.1.840.0...",
  "event": "Severe Thunderstorm Warning",
  "severity": "Moderate",
  "area_desc": "Harris, TX; Montgomery, TX",
  "effective": "2025-06-10T20:15:00Z",
  "expires": "2025-06-10T21:00:00Z",
  "sent": "2025-06-10T20:14:32Z",
  
  "radar_indicated": {
    "hail_inches": 1.25,
    "wind_mph": 70
  },
  
  "fips_codes": ["48201", "48339"],
  "county_names": [
    {"county": "Harris", "state": "TX"},
    {"county": "Montgomery", "state": "TX"}
  ],
  "geometry_type": "Polygon",
  "coordinate_count": 156,
  "affected_states": ["TX"],
  "geometry_bounds": {
    "min_lat": 30.1234,
    "max_lat": 30.5678,
    "min_lon": -95.9876,
    "max_lon": -95.5432
  },
  
  "spc_verified": true,
  "spc_reports": [
    {
      "type": "hail",
      "size": 1.25,
      "location": "Spring, TX",
      "time": "20:22Z"
    }
  ],
  "spc_confidence_score": 0.89,
  
  "enhanced_geometry": {
    "has_detailed_geometry": true,
    "coverage_area_sq_degrees": 0.125,
    "county_state_mapping": [...],
    "affected_states": ["TX"]
  },
  
  "ai_summary": "Severe thunderstorm with quarter-size hail and 70 mph winds affecting northwestern Harris County and southern Montgomery County.",
  "ai_tags": ["hail", "damaging_winds", "property_damage_risk"]
}
```

### Integration Examples

#### Insurance Claims Processing

```python
import requests
import json
from datetime import datetime, timedelta

class InsuranceClaimsBot:
    def __init__(self, hailydb_base_url, webhook_url):
        self.base_url = hailydb_base_url
        self.webhook_url = webhook_url
        self.setup_hail_monitoring()
    
    def setup_hail_monitoring(self):
        """Register webhook for hail events affecting coverage areas"""
        webhook_config = {
            "webhook_url": f"{self.webhook_url}/hail-events",
            "event_type": "hail", 
            "threshold_value": 0.75,  # 3/4 inch or larger
            "user_id": "insurance_bot"
        }
        
        response = requests.post(
            f"{self.base_url}/internal/webhook-rules",
            json=webhook_config
        )
        print(f"Hail monitoring active: {response.status_code}")
    
    def process_hail_alert(self, alert_data):
        """Process incoming hail alert for claims preparation"""
        radar_indicated = alert_data.get('radar_indicated', {})
        hail_size = radar_indicated.get('hail_inches', 0)
        
        if hail_size >= 1.0:  # Quarter size or larger
            self.create_potential_claim_area(alert_data)
            self.notify_field_adjusters(alert_data)
```

## 📋 Complete API Documentation

### Overview

HailyDB provides comprehensive RESTful API access to National Weather Service alerts with advanced features including radar-indicated measurements, real-time webhooks, full geometry processing, Storm Prediction Center verification, and AI-enriched summaries. Perfect for insurance claims, field operations, emergency management, and partner integrations.

**Base URL**: `https://your-hailydb.replit.app`

### 🚀 New Enhanced Features

#### Feature 1: Radar-Indicated Parsing
- **Hail Size Detection**: Automatically extracts hail measurements (0.75" - 2.0"+) from Severe Thunderstorm Warnings
- **Wind Speed Analysis**: Parses radar-indicated wind speeds (58-80+ mph) from NWS text
- **Immediate Intelligence**: Provides actionable data before SPC verification
- **API Fields**: `radar_indicated.hail_inches`, `radar_indicated.wind_mph`

#### Feature 2: Real-Time Webhooks System  
- **Event Triggers**: Hail size, wind speed, and damage probability thresholds
- **HTTP POST Delivery**: Reliable webhook dispatch with retry logic
- **Geographic Filtering**: State, county, and FIPS-based location targeting
- **Admin API**: Complete webhook rule management endpoints

#### Feature 3: Full Geometry & County Mapping
- **FIPS Code Extraction**: Precise county-level geographic identifiers
- **Coordinate Analysis**: Geometry bounds, coverage area calculation
- **Enhanced Location Data**: County-state mapping for insurance claims
- **Spatial Intelligence**: Comprehensive geographic processing for field operations

### Authentication

No authentication required for public endpoints. Internal endpoints are for administrative use.

---

### 🚨 Alert Endpoints

#### Get All Alerts
```
GET /alerts
```
**Description**: Retrieve alerts with optional filtering and pagination

**Query Parameters**:
- `page` (int, default: 1) - Page number for pagination
- `per_page` (int, default: 50, max: 1000) - Results per page
- `severity` (string) - Filter by severity: "Minor", "Moderate", "Severe", "Extreme"
- `event` (string) - Filter by event type (partial match)
- `category` (string) - Filter by predefined category
- `state` (string) - Filter by state name or abbreviation
- `county` (string) - Filter by county name
- `area` (string) - Filter by area description
- `effective_date` (string, YYYY-MM-DD) - Filter by effective date
- `ingested_date` (string, YYYY-MM-DD) - Filter by ingestion date (database completeness)
- `active_only` (boolean, default: false) - Show only currently active alerts
- `format` (string) - Set to "json" for JSON response

**Categories Available**:
- Severe Weather Alert
- Winter Weather Alert
- Flood Alert
- Coastal Alert
- Wind & Fog Alert
- Fire Weather Alert
- Air Quality & Dust Alert
- Marine Alert
- Tropical Weather Alert
- Tsunami Alert
- General Weather Info

#### Get SPC Reports
```
GET /api/spc/reports
```
**Description**: Retrieve Storm Prediction Center storm reports with filtering

**Query Parameters**:
- `type` (string) - Report type: "tornado", "wind", "hail"
- `state` (string) - State abbreviation (e.g., "TX")
- `county` (string) - County name (partial match)
- `date` (string, YYYY-MM-DD) - Specific report date
- `limit` (int, max: 500, default: 100) - Results limit
- `offset` (int, default: 0) - Results offset for pagination

### System Health Status
```
GET /internal/status
```
**Description**: Comprehensive system health and diagnostics

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-03T16:00:00Z",
  "database": "healthy",
  "alerts": {
    "total": 1250,
    "recent_24h": 89,
    "active_now": 15
  },
  "spc_verification": {
    "verified_count": 156,
    "unverified_count": 1094,
    "coverage_percentage": 12.5,
    "oldest_unverified": "2025-05-15T10:00:00Z"
  }
}
```

### Real-Time Webhook System

#### Register Webhook Rule
```
POST /internal/webhook-rules
```
**Description**: Create a new webhook rule for real-time alert notifications

**Request Body**:
```json
{
  "webhook_url": "https://your-app.com/webhooks/weather-alerts",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX",
  "user_id": "your_application_id"
}
```

**Event Types**:
- `"hail"` - Triggers on radar-indicated hail size (inches)
- `"wind"` - Triggers on radar-indicated wind speed (mph)
- `"damage_probability"` - Triggers on calculated damage probability (0.0-1.0)

### Hurricane Track Endpoints

#### Get Hurricane Tracks
```
GET /api/hurricane-tracks
```
**Description**: Retrieve historical hurricane track data with filtering options

**Query Parameters**:
- `storm_id` (string) - Filter by NOAA storm identifier (e.g., "AL012020")
- `name` (string) - Filter by hurricane name (e.g., "Laura")
- `year` (int) - Filter by year (e.g., 2020)
- `lat_min`, `lat_max`, `lon_min`, `lon_max` (float) - Bounding box filter
- `start_date`, `end_date` (string, YYYY-MM-DD) - Date range filter
- `landfall_only` (boolean) - Only storms that made US landfall
- `category_min` (int, 1-5) - Minimum hurricane category

## 📊 SPC Storm Report Ingestion - Data Organization and Timezone Handling

### SPC Report Organization

The Storm Prediction Center organizes storm reports based on **meteorological days**, not calendar days:

- **Report Period**: 1200 UTC to 1159 UTC the next day
- **Example**: The report file `240603_rpts_filtered.csv` covers:
  - From: 2024-06-03 at 12:00 UTC
  - To: 2024-06-04 at 11:59 UTC

### Timezone Considerations

#### US Time Zones vs UTC
- **Florida (UTC-4)**: A storm at 0010 UTC (12:10 AM) is actually 8:10 PM the previous day
- **Central Time (UTC-5)**: Same storm would be 7:10 PM the previous day  
- **Hawaii (UTC-10)**: Same storm would be 2:10 PM the previous day

#### Current HailyDB Approach
- **Storage**: All times stored in UTC (no timezone conversion)
- **Date Assignment**: Events are assigned to the SPC meteorological day
- **User Requirement**: Last 3 days (Today-4) synced for Florida user wake-up

### Data Integrity Issue

**Problem**: Events occurring between 00:00-11:59 UTC are meteorologically correct but may appear on the "wrong" calendar day for US users.

**Example from 250603_rpts_filtered.csv**:
```
0010,UNK,1 SW Coyne Center,Rock Island,IL,41.39,-90.59,Tornado tracked from southwest...
```
This tornado at 00:10 UTC is:
- **SPC Date**: 2024-06-03 (correct meteorologically)
- **Local Time**: 2024-06-02 at 8:10 PM Eastern (previous calendar day)

### Current Implementation Status ✓

**VERIFIED**: HailyDB correctly implements SPC meteorological day assignment.

#### Confirmed Behavior
- Events at 00:01-11:59 UTC are correctly assigned to the SPC meteorological day
- Example: Storm at 00:10 UTC on June 4th is properly stored as `report_date = '2025-06-04'`
- All reports from `YYMMDD_rpts_filtered.csv` are assigned to that date regardless of UTC time
- This matches SPC's 12:00 UTC to 11:59 UTC next day reporting period

#### US-Focused Implementation
- **Geographic Scope**: United States only
- **Time Storage**: All times remain in UTC (no conversion needed)
- **Date Assignment**: Follows SPC meteorological day convention
- **User Experience**: Florida user (UTC-4) sees meteorologically correct storm dates

#### Systematic Polling Schedule

**Implemented Schedule**:
- **T-0 (Today)**: Every 5 minutes - Real-time current day updates
- **T-1 through T-4**: Hourly updates on the hour - Recent critical period  
- **T-5 through T-7**: Every 3 hours - Recent historical period
- **T-8 through T-15**: Daily updates - Stabilizing historical period
- **T-16+**: Data protected - No automatic polling (backfill only)

**Florida User Optimization**:
- Morning wake-up guaranteed fresh T-1 through T-4 data
- Hourly updates ensure data completeness for critical recent period
- Systematic coverage eliminates polling gaps

**Data Protection**:
- T-16+ dates protected from automatic updates
- Backfill processing available for missing data recovery
- Manual override capability for data corrections

---

**HailyDB v2.0** - Production-ready weather data ingestion platform with comprehensive monitoring and data integrity verification.