# HailyDB v2.1 - Historical Weather Damage Intelligence Platform

![HailyDB Logo](generated-icon.png)

**Production Status:** NWS API Compliant Repository  
**Core Business Data:** 2,085 Historical Damage Events (27.6% of 7,566 total alerts)  
**Data Sources:** National Weather Service | Storm Prediction Center | NOAA HURDAT2  

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Integration Examples](#integration-examples)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Webhooks](#webhooks)
- [SDK Development](#sdk-development)
- [Performance & Monitoring](#performance--monitoring)
- [Production Deployment](#production-deployment)
- [Development Setup](#development-setup)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

HailyDB is a professional repository of expired National Weather Service alerts containing radar-detected hail and high wind damage events. Designed for insurance companies, restoration contractors, and legal forensics teams, HailyDB answers the critical question: "Where likely weather damage WAS." The system mirrors official NWS data with value-added enrichments, following complete OpenAPI specification compliance.

### Key Features

**Historical Damage Repository** - 2,085 expired alerts with radar-detected hail and high winds  
**NWS API Compliance** - GeoJSON FeatureCollection format matching official weather.gov standards  
**Professional Enrichments** - SPC cross-referencing and AI-powered meteorological summaries  
**Insurance Industry Focus** - Optimized for damage claims verification and restoration planning  
**Geographic Precision** - Complete FIPS county mapping and coordinate boundary data  
**Production Architecture** - Clean, scalable codebase following industry standards  
**Historical Archive** - Complete repository from January 2024 onwards  
**OpenAPI Standards** - Exact field naming and response structures per NWS specification  

### Target Industries

- **Insurance Companies**: Claims verification using historical radar-detected damage events
- **Restoration Contractors**: Project identification based on past weather damage locations
- **Legal Forensics**: Weather event verification for litigation and expert testimony
- **Risk Assessment**: Pattern analysis for underwriting and actuarial calculations
- **Property Management**: Historical damage assessment for due diligence and planning

---

## Quick Start

### Historical Damage Events

```bash
# Get expired alerts with radar-detected hail and wind damage
curl "http://localhost:5000/api/alerts/expired"

# Search historical damage by location
curl "http://localhost:5000/api/alerts/expired?state=TX&county=Harris&limit=25"

# Find specific damage thresholds
curl "http://localhost:5000/api/alerts/expired?min_hail=1.0&min_wind=60"
```

### NWS-Compliant Data Structure

```bash
# Returns GeoJSON FeatureCollection format per NWS OpenAPI spec
curl "http://localhost:5000/api/alerts/expired?limit=1" | jq '.type'
# Output: "FeatureCollection"
```

### System Health and Statistics

```bash
# System status and damage event statistics
curl "http://localhost:5000/api/health"
```

### Complete API Integration Workflow

**Step 1: Search for Historical Damage Events**
```bash
curl "http://localhost:5000/api/alerts/expired?state=TX&min_wind=50&limit=10"
```

**Step 2: Get Individual Alert Details**
```bash
# Use alert ID from search results
curl "http://localhost:5000/api/alerts/{alert_id_from_step_1}"
```

**Step 3: Access Complete Dataset**
All endpoints return NWS-compliant data with HailyDB enrichments for professional damage assessment and insurance claims verification.

---

## Complete API Reference

### Core Endpoints

| Endpoint | Method | Description | Use Case |
|----------|--------|-------------|----------|
| `/api/alerts/expired` | GET | Historical damage events repository | Primary business endpoint for insurance claims |
| `/api/alerts/{alert_id}` | GET | Individual alert details | Complete alert data with enrichments |
| `/api/health` | GET | System status and statistics | Integration health checks |

### Search and Filter Parameters

**Available for `/api/alerts/expired`:**
- `state` (string): State abbreviation (TX, FL, CA, etc.)
- `county` (string): County name filter
- `min_hail` (float): Minimum hail size in inches (0.75, 1.0, 1.75, etc.)
- `min_wind` (integer): Minimum wind speed in mph (50, 60, 70, etc.)
- `start_date` (string): Filter start date (YYYY-MM-DD format)
- `end_date` (string): Filter end date (YYYY-MM-DD format)
- `page` (integer): Page number for pagination
- `limit` (integer): Results per page (max 100)

### Response Format Standards

All endpoints follow NWS OpenAPI specification:
- **GeoJSON FeatureCollection** format for alert collections
- **Official NWS field names** (areaDesc, effective, expires, etc.)
- **HailyDB enrichments** clearly separated in `hailydb_enrichments` object
- **Metadata** includes repository type and data source attribution

### Integration Examples

**Insurance Claims Verification:**
```bash
# Find hail damage events in specific county
curl "http://localhost:5000/api/alerts/expired?state=TX&county=Harris&min_hail=1.0"

# Get complete alert details for claim assessment
curl "http://localhost:5000/api/alerts/{alert_id}"
```

**Restoration Project Planning:**
```bash
# Find high-wind damage events by date range
curl "http://localhost:5000/api/alerts/expired?min_wind=60&start_date=2025-01-01&end_date=2025-08-01"
```

**Legal Forensics:**
```bash
# Verify specific weather event for litigation
curl "http://localhost:5000/api/alerts/{specific_alert_id}"
```

### Sample Response Structure (NWS Compliant)

```json
{
  "type": "FeatureCollection",
  "features": [{
    "id": "alert_id", 
    "type": "Feature",
    "properties": {
      "areaDesc": "County names per NWS standard",
      "effective": "2025-01-15T12:00:00Z",
      "expires": "2025-01-15T13:00:00Z",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "hailydb_enrichments": {
        "radar_indicated": {"hail_inches": 1.25, "wind_mph": 65},
        "spc_verified": true,
        "ai_summary": "Professional meteorological analysis"
      }
    },
    "geometry": { "type": "Polygon", "coordinates": [...] }
  }],
  "title": "HailyDB Historical Alerts Repository",
  "metadata": {
    "total_results": 2085,
    "filters_applied": {"historical_only": true}
  }
}
```

---

## Production Architecture v2.1

### Core Business Value
HailyDB serves as a **historical weather damage intelligence repository** focused on expired NWS alerts containing radar-detected hail and high wind parameters. Unlike active weather monitoring systems, our value proposition centers on providing reliable historical data answering: **"Where likely weather damage WAS."**

### Current Data Repository
- **7,566 Total NWS Alerts** in historical database
- **2,085 Core Business Events** (27.6%): Expired alerts with radar-detected damage parameters  
- **Perfect Data Integrity**: 100% SPC synchronization with zero variance tolerance
- **Geographic Coverage**: All 50 states, territories, and marine zones

### NWS API Compliance
The system follows the official National Weather Service OpenAPI specification exactly:
- **Response Format**: GeoJSON FeatureCollection structure
- **Field Names**: Official NWS naming conventions (`areaDesc`, `effective`, `expires`, etc.)
- **Data Sources**: Pure mirror of government weather data with value-added enrichments
- **Professional Standards**: Production-ready codebase suitable for enterprise integration

### Target Client Base
- **Insurance Companies**: Claims verification and damage assessment
- **Restoration Contractors**: Historical damage location identification for project planning
- **Legal Forensics**: Weather event verification for litigation support
- **Risk Assessment**: Pattern analysis for underwriting and actuarial calculations

### System Status  
**Production Ready** - Clean, documented codebase with 20 active services and comprehensive historical weather damage intelligence.

---

## API Endpoints

### Primary Historical Repository
**`GET /api/alerts/expired`** - Core business endpoint returning expired alerts with radar-detected parameters

**Parameters:**
- `state` (string): State abbreviation filter
- `county` (string): County name filter  
- `min_hail` (float): Minimum hail size in inches
- `min_wind` (integer): Minimum wind speed in mph
- `start_date` / `end_date` (string): Date range filters
- `page` (integer): Pagination
- `limit` (integer): Results per page

**Sample Request:**
```bash
curl "http://localhost:5000/api/alerts/expired?state=TX&min_hail=1.0&limit=50"
```

### Individual Alert Details
**`GET /api/alerts/{alert_id}`** - Get complete data for a specific alert

**Sample Request:**
```bash
curl "http://localhost:5000/api/alerts/urn:oid:2.49.0.1.840.0.ba730699699a52f5bd5b9d53f1764ddb892213bb.001.1"
```

**Sample Response:**
```json
{
  "id": "urn:oid:2.49.0.1.840.0.ba730699699a52f5bd5b9d53f1764ddb892213bb.001.1",
  "event": "Special Weather Statement",
  "areaDesc": "Castro; Swisher; Lamb; Hale; Floyd",
  "effective": "2025-08-11T01:00:00",
  "expires": "2025-08-11T01:30:00",
  "severity": "Moderate",
  "description": "Doppler radar tracking strong winds up to 50 mph...",
  "hailydb_enrichments": {
    "radar_indicated": {
      "hail_inches": 0.0,
      "wind_mph": 50
    },
    "spc_verified": false,
    "geometry_bounds": {
      "min_lat": 33.87,
      "max_lat": 34.62,
      "min_lon": -102.27,
      "max_lon": -101.33
    },
    "is_active": false,
    "duration_minutes": 30
  },
  "hailydb_metadata": {
    "repository_type": "historical_weather_damage_intelligence",
    "data_source": "National Weather Service (NWS)",
    "nws_compliant": true
  }
}
```

---

## System Architecture

### Technology Stack

- **Backend Framework**: Flask 3.0+ with SQLAlchemy ORM
- **Database**: PostgreSQL 15+ with JSONB support for complex data
- **AI Processing**: OpenAI GPT-4o for enhanced context generation
- **Web Server**: Gunicorn with multi-worker configuration
- **Deployment**: Replit Production with automated scaling
- **Monitoring**: Comprehensive logging and health check endpoints

### Core Components

#### Data Ingestion Services

**NWS Alert Ingestion**
- Autonomous 5-minute polling of NWS API
- Real-time alert processing and database storage
- Radar-indicated data extraction (hail size, wind speed)
- Geographic parsing and state enrichment
- Duplicate detection using row-hash algorithm

**SPC Report Ingestion**  
- Historical data backfill (January 2024 - present)
- Daily automated ingestion of storm reports
- Comprehensive tornado, wind, and hail report processing
- Geographic coordinate validation and enhancement

**Live Radar Service**
- Real-time radar-detected event processing
- Filter for severe weather criteria (hail any size OR winds 50+ mph)
- Active alert status monitoring and expiration tracking

#### AI Enhancement Services

**Enhanced Context Generation (v4.0)**
- Location-focused summaries using 6-point geographic format
- Conditional logic for SPC-matched vs non-matched reports
- Integration with free location services for nearby places
- Professional meteorological terminology and analysis

**SPC Match Summarizer**
- AI-powered verification summaries for confirmed storm events
- Cross-reference radar detection with verified measurements
- Damage assessment analysis using historical storm data
- Weatherman-style professional reporting format

#### Data Processing Services

**SPC Matching Engine**
- FIPS-based geographic correlation between alerts and reports
- Confidence scoring for verification accuracy
- Temporal matching within storm event windows
- Multi-criteria matching (location, time, magnitude)

**Radar Parsing System**
- Natural language processing of NWS alert descriptions
- Extraction of hail size measurements (inches)
- Wind speed detection and standardization (mph)
- Pattern recognition for storm characteristics

**State Enrichment Service**
- UGC/SAME code mapping to state abbreviations  
- Batch processing for historical data enrichment
- 96%+ success rate for state identification
- Comprehensive 200+ UGC prefix database

#### Background Operations

**Autonomous Scheduler**
- Coordinated operation management with configurable intervals
- NWS polling (5 minutes), SPC polling (60 minutes), matching (30 minutes)
- Error recovery and retry logic for failed operations
- Comprehensive operation logging and statistics

**Webhook Service**
- Real-time HTTP notifications for external integrations
- Rule-based evaluation with configurable conditions
- Delivery confirmation and retry mechanisms
- Deduplication using cache-based algorithms

### Database Schema

#### Core Tables

**alerts** - NWS weather alerts with enhanced processing
- Primary keys, timestamps, and geographic data
- JSONB fields for radar_indicated, enhanced_geometry, properties
- Full-text search capabilities across multiple fields
- Comprehensive indexing for sub-100ms query performance

**spc_reports** - Storm Prediction Center verified reports
- Geographic coordinates and magnitude measurements
- Enhanced context integration with AI-generated summaries
- Report type classification (tornado, wind, hail)
- Historical ingestion tracking and row-hash deduplication

**spc_ingestion_logs** - Processing audit trail
- Success/failure tracking for all ingestion operations
- Detailed error logging and performance metrics
- Date range processing with duplicate detection
- Operation statistics for monitoring and debugging

#### Performance Optimizations

- **Connection Pooling**: Prevents database connection exhaustion
- **Query Optimization**: Strategic indexing reduces query time to <100ms
- **JSONB Indexing**: GIN indexes for complex JSON field queries
- **Row-Level Deduplication**: Hash-based duplicate detection across all tables

---

## API Reference

### Base URL
```
Production: https://api.hailydb.com
Development: http://localhost:5000
```

### Response Format
All API responses follow consistent JSON structure:

```json
{
  "data": [...],           // Main response data
  "pagination": {...},     // Pagination metadata  
  "filters": {...},        // Applied filter parameters
  "metadata": {...}        // Additional response metadata
}
```

### System Endpoints

#### Health Check
**`GET /api/health`**

System status and database statistics endpoint for monitoring and integration testing.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/health"
```

**Response:**
```json
{
  "status": "healthy",
  "service": "HailyDB API v2.0",
  "timestamp": "2025-08-12T04:25:11.160168Z",
  "database": {
    "alerts": 6056,
    "spc_reports": 45225
  },
  "version": "2.0.0",
  "documentation": "/documentation"
}
```

### Alert Endpoints

#### Search Alerts
**`GET /api/alerts/search`**

Advanced search with comprehensive filtering capabilities.

**Parameters:**
- `q` (string): Full-text search across event, area, description, headlines
- `state` (string): State abbreviation (TX, CA, FL, etc.)
- `county` (string): County name (partial match supported)
- `area` (string): Area description search
- `event_type` (string): Alert type (Severe Thunderstorm Warning, Tornado Warning, etc.)
- `severity` (string): Alert severity (Minor, Moderate, Severe, Extreme)
- `active_only` (boolean): Only unexpired alerts (default: false)
- `has_radar_data` (boolean): Only alerts with radar-detected data
- `min_hail` (float): Minimum hail size in inches
- `min_wind` (integer): Minimum wind speed in mph
- `start_date` (string): Start date filter (YYYY-MM-DD)
- `end_date` (string): End date filter (YYYY-MM-DD)
- `page` (integer): Page number (default: 1)
- `limit` (integer): Results per page (max: 100, default: 50)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/search?state=TX&event_type=Severe%20Thunderstorm&active_only=true&has_radar_data=true&min_hail=1.0&limit=25"
```

**Response:**
```json
{
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.{hash}.{sequence}.{version}",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "Harris; Montgomery; Waller",
      "effective": "2025-08-12T02:00:00",
      "expires": "2025-08-12T03:00:00",
      "sent": "2025-08-12T02:00:00",
      "affected_states": ["TX"],
      "radar_indicated": {
        "hail_inches": 1.75,
        "wind_mph": 70
      },
      "enhanced_geometry": {
        "geometry_type": "Polygon",
        "coordinate_count": 15,
        "geometry_bounds": {
          "min_lat": 29.5,
          "max_lat": 30.2,
          "min_lon": -95.8,
          "max_lon": -95.1
        },
        "coverage_area_sq_degrees": 0.42,
        "has_detailed_geometry": true
      },
      "spc_verified": true,
      "spc_confidence_score": 0.92,
      "spc_report_count": 3,
      "is_active": true,
      "duration_minutes": 60
    }
  ],
  "filters": {
    "active_only": true,
    "state": "TX",
    "event_type": "Severe Thunderstorm Warning",
    "has_radar_data": true,
    "min_hail": 1.0,
    "search_query": "",
    "severity": null,
    "area": null,
    "county": null
  },
  "limit": 25,
  "page": 1,
  "pages": 150,
  "total": 3745
}
```

#### Get Single Alert
**`GET /api/alerts/{alert_id}`**

Retrieve complete details for a specific alert including AI summaries and SPC verification.

**Parameters:**
- `format` (string): Response format (json, html - default: html)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/urn:oid:2.49.0.1.840.0.4f244d96dba7dadd5eb93ff516df448bf7f8be25.001.1?format=json"
```

#### Active Alerts
**`GET /api/alerts/active`**

Get all currently active (unexpired) alerts.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/active"
```

**Response:**
```json
{
  "timestamp": "2025-08-12T02:30:00Z",
  "total_active": 206,
  "alerts": [...]
}
```

#### Live Radar Alerts
**`GET /api/live-radar-alerts`**

Get current radar-detected severe weather alerts with filtering for:
- Hail of any size (>0.0 inches)
- Wind speeds 50+ mph
- Currently active/unexpired alerts

**Parameters:**
- `format` (string): Response format (json, html - default: html)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/live-radar-alerts?format=json"
```

**Response:**
```json
{
  "timestamp": "2025-08-12T02:30:00Z",
  "total_qualifying": 24,
  "total_active": 287,
  "criteria": "hail_any_size OR wind_50plus_mph",
  "alerts": [
    {
      "id": "urn:oid:...",
      "event": "Severe Thunderstorm Warning",
      "area_desc": "Collin; Dallas; Denton",
      "state": "TX",
      "hail_inches": 1.25,
      "wind_mph": 65,
      "effective": "2025-08-12T02:15:00",
      "expires": "2025-08-12T03:15:00"
    }
  ]
}
```

#### Geographic Search
**`GET /api/alerts/radius`**

Find alerts within specified radius of coordinates.

**Parameters:**
- `lat` (float, required): Latitude
- `lon` (float, required): Longitude
- `radius` (float, required): Search radius in miles
- `active_only` (boolean): Only active alerts (default: false)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/radius?lat=29.7604&lon=-95.3698&radius=50&active_only=true"
```

#### State-Based Search
**`GET /api/alerts/by-state/{state}`**

Get alerts for a specific state.

**Parameters:**
- `active_only` (boolean): Only active alerts (default: false)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/by-state/TX?active_only=true"
```

#### County-Based Search
**`GET /api/alerts/by-county/{state}/{county}`**

Get alerts for a specific state and county.

**Parameters:**
- `active_only` (boolean): Only active alerts (default: false)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/by-county/TX/Harris?active_only=true"
```

#### FIPS Code Search
**`GET /api/alerts/fips/{fips_code}`**

Search alerts by Federal Information Processing Standards county codes.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/alerts/fips/48201"  # Harris County, TX
```

## Direct Database Access

For enterprise clients requiring zero-latency access and maximum query flexibility, HailyDB offers direct PostgreSQL database connections with read-only access to real-time weather intelligence data.

### Benefits of Direct Database Access

🔧 **Zero API Latency** - Query data directly without REST API overhead  
📊 **Custom Analytics** - Write complex SQL queries for advanced data analysis  
⚡ **Real-time Performance** - Access data as fast as our ingestion pipeline updates it  
🎯 **Unlimited Flexibility** - Join tables, create custom aggregations, and build tailored reports  
📈 **Enterprise Scale** - Handle high-frequency queries without rate limits  

### Database Connection Setup

#### Step 1: Request Database Credentials
Contact support to request read-only database credentials for your organization. You will receive:

- **Database Host**: Your dedicated read-only endpoint
- **Database Name**: `hailydb_production`
- **Username**: `readonly_[your_org]`
- **Password**: Secure generated password
- **Port**: `5432` (standard PostgreSQL)
- **SSL Mode**: `require`

#### Step 2: Connection String Format
```
postgresql://readonly_[your_org]:[password]@[host]:5432/hailydb_production?sslmode=require
```

#### Step 3: Test Connection
```bash
# Using psql command line
psql "postgresql://readonly_yourorg:password@host:5432/hailydb_production?sslmode=require"

# Test query
SELECT COUNT(*) FROM alerts WHERE is_active = true;
```

### Database Schema Overview

#### Core Tables

**`alerts`** - National Weather Service alerts with enhanced processing
```sql
-- Key columns for client queries
SELECT 
    id,                    -- Unique alert identifier
    event,                 -- Alert type (Severe Thunderstorm Warning, etc.)
    severity,              -- Minor, Moderate, Severe, Extreme
    area_desc,             -- Geographic area description
    effective,             -- Alert start time (UTC)
    expires,               -- Alert end time (UTC)
    sent,                  -- Alert issued time (UTC)
    affected_states,       -- Array of state abbreviations
    radar_indicated,       -- JSONB: hail_inches, wind_mph, detected flags
    enhanced_geometry,     -- JSONB: polygon data and coverage statistics
    spc_verified,          -- Boolean: verified by Storm Prediction Center
    spc_confidence_score,  -- Float: verification confidence (0.0-1.0)
    spc_report_count,      -- Integer: number of associated SPC reports
    is_active,             -- Boolean: currently active (effective ≤ now < expires)
    duration_minutes,      -- Integer: alert duration
    ingested_at           -- Timestamp: when added to database
FROM alerts
WHERE is_active = true;
```

**`spc_reports`** - Storm Prediction Center verified reports
```sql
-- Key columns for storm verification
SELECT 
    id,                    -- Unique report identifier
    report_date,           -- Report date (YYYY-MM-DD)
    report_type,           -- tornado, wind, hail
    time_utc,              -- Time in UTC (HHMM format)
    location,              -- Location description (e.g., "5 WNW AMARILLO")
    county,                -- County name
    state,                 -- State abbreviation
    latitude,              -- Decimal degrees
    longitude,             -- Decimal degrees
    magnitude,             -- JSONB: size_hundredths for hail, speed for wind
    comments,              -- Additional details and damage reports
    enhanced_context,      -- JSONB: AI-generated location analysis
    enhanced_context_version, -- String: context generation version
    ingested_at           -- Timestamp: when added to database
FROM spc_reports
WHERE report_date >= CURRENT_DATE - INTERVAL '7 days';
```

#### Optimized Indexes

All tables include strategic indexes for high-performance queries:
- **Geographic indexes**: Fast radius and boundary searches
- **Time-based indexes**: Efficient date/time range filtering  
- **JSONB indexes**: Quick searches within radar_indicated and enhanced_geometry
- **Composite indexes**: Optimized for common query patterns

### Common Query Patterns

#### Active Severe Weather Alerts
```sql
-- Get all currently active alerts with radar data
SELECT 
    event,
    area_desc,
    affected_states,
    (radar_indicated->>'hail_inches')::float as hail_size,
    (radar_indicated->>'wind_mph')::int as wind_speed,
    effective,
    expires
FROM alerts 
WHERE is_active = true 
    AND radar_indicated IS NOT NULL
    AND (
        (radar_indicated->>'hail_inches')::float > 0 
        OR (radar_indicated->>'wind_mph')::int >= 50
    )
ORDER BY effective DESC;
```

#### SPC Verified Storm Reports by Region
```sql
-- Get verified hail reports for Texas in the last 24 hours
SELECT 
    location,
    county,
    (magnitude->>'size_hundredths')::int / 100.0 as hail_inches,
    time_utc,
    comments,
    latitude,
    longitude
FROM spc_reports 
WHERE state = 'TX' 
    AND report_type = 'hail'
    AND report_date >= CURRENT_DATE - INTERVAL '1 day'
    AND (magnitude->>'size_hundredths')::int >= 100  -- 1 inch or larger
ORDER BY time_utc DESC;
```

#### Geographic Radius Search
```sql
-- Find alerts within 50 miles of Houston, TX
SELECT 
    id,
    event,
    area_desc,
    effective,
    expires,
    ST_Distance_Sphere(
        ST_MakePoint(-95.3698, 29.7604),  -- Houston coordinates
        ST_MakePoint(
            (enhanced_geometry->'geometry_bounds'->>'min_lon')::float,
            (enhanced_geometry->'geometry_bounds'->>'min_lat')::float
        )
    ) / 1609.34 as distance_miles
FROM alerts 
WHERE is_active = true
    AND enhanced_geometry IS NOT NULL
    AND ST_DWithin(
        ST_MakePoint(-95.3698, 29.7604)::geography,
        ST_MakePoint(
            (enhanced_geometry->'geometry_bounds'->>'min_lon')::float,
            (enhanced_geometry->'geometry_bounds'->>'min_lat')::float
        )::geography,
        80467  -- 50 miles in meters
    )
ORDER BY distance_miles;
```

#### Alert-to-SPC Correlation Analysis
```sql
-- Cross-reference alerts with SPC verification
SELECT 
    a.id as alert_id,
    a.event,
    a.area_desc,
    a.spc_verified,
    a.spc_confidence_score,
    COUNT(s.id) as verified_reports,
    ARRAY_AGG(s.report_type) as report_types,
    ARRAY_AGG(s.magnitude) as magnitudes
FROM alerts a
LEFT JOIN spc_reports s ON (
    a.affected_states && ARRAY[s.state]
    AND DATE(a.effective) = s.report_date
    AND ABS(EXTRACT(EPOCH FROM a.effective) - 
            (EXTRACT(HOUR FROM s.time_utc::time) * 3600 + 
             EXTRACT(MINUTE FROM s.time_utc::time) * 60)) < 7200  -- Within 2 hours
)
WHERE a.effective >= CURRENT_DATE - INTERVAL '7 days'
    AND a.radar_indicated IS NOT NULL
GROUP BY a.id, a.event, a.area_desc, a.spc_verified, a.spc_confidence_score
HAVING COUNT(s.id) > 0
ORDER BY a.effective DESC;
```

### Performance Best Practices

#### Query Optimization
1. **Always use time-based filters** - Include date ranges to leverage time indexes
2. **Filter early** - Apply WHERE clauses before JOINs when possible
3. **Use JSONB operators efficiently** - Leverage `->` and `->>` for nested data
4. **Limit result sets** - Use LIMIT for large datasets and implement pagination

#### Connection Management
```python
# Python example with connection pooling
import psycopg2.pool

# Create connection pool (recommended for production)
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host="your-readonly-host",
    database="hailydb_production", 
    user="readonly_yourorg",
    password="your-password",
    sslmode="require"
)

# Get connection from pool
conn = connection_pool.getconn()
cursor = conn.cursor()

# Execute query
cursor.execute("""
    SELECT event, area_desc, effective 
    FROM alerts 
    WHERE is_active = true 
    LIMIT 100
""")

results = cursor.fetchall()

# Return connection to pool
connection_pool.putconn(conn)
```

### Real-time Data Streaming (Advanced)

For applications requiring instant notifications of new data, PostgreSQL LISTEN/NOTIFY can provide real-time updates:

```sql
-- Listen for new alert notifications
LISTEN new_alert_notification;
LISTEN new_spc_report_notification;

-- Your application will receive instant notifications when new data arrives
```

### Security & Access Control

- **Read-only access** - No INSERT, UPDATE, or DELETE permissions
- **Table-level permissions** - Access only to alerts and spc_reports tables
- **Row-level security** - Available for multi-tenant scenarios
- **SSL/TLS encryption** - All connections encrypted in transit
- **IP allowlisting** - Optional restriction to specific IP ranges
- **Connection monitoring** - Real-time tracking of database usage

### Support & Monitoring

**Database Performance Monitoring**
- Query performance analytics available via client portal
- Real-time connection count and usage statistics
- Slow query identification and optimization recommendations

**Technical Support**
- Dedicated database specialist for enterprise clients
- Schema change notifications and migration assistance
- Custom view creation for specific use cases
- Performance tuning consultation

---

**Ready to get started with direct database access?**
Contact our enterprise team for immediate setup of your dedicated read-only database credentials.

### SPC Report Endpoints

#### Get SPC Reports
**`GET /api/spc/reports`**

Retrieve Storm Prediction Center verified reports with filtering.

**Parameters:**
- `type` (string): Report type (tornado, wind, hail)
- `state` (string): State abbreviation  
- `county` (string): County name (partial match)
- `date` (string): Report date (YYYY-MM-DD format)
- `limit` (integer): Results per page (max: 500, default: 100)
- `offset` (integer): Results offset for pagination (default: 0)

**Example Request:**
```bash
curl "https://api.hailydb.com/api/spc/reports?type=hail&state=TX&limit=50"
```

**Response:**
```json
{
  "reports": [
    {
      "id": 48924,
      "report_date": "2025-08-11",
      "report_type": "hail",
      "time_utc": "2130",
      "location": "5 WNW AMARILLO",
      "county": "POTTER",
      "state": "TX",
      "latitude": 35.2500,
      "longitude": -101.9167,
      "magnitude": {
        "size_hundredths": 200
      },
      "comments": "TRAINED SPOTTER REPORTED GOLF BALL SIZE HAIL",
      "ingested_at": "2025-08-12T00:58:27.487366"
    }
  ],
  "pagination": {
    "total": 45219,
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "filters": {
    "type": "hail",
    "state": "TX",
    "county": null,
    "date": null
  }
}
```

#### Get Single SPC Report
**`GET /api/spc/reports/{report_id}`**

Retrieve detailed information for a specific SPC report including enhanced context and verified alerts.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/spc/reports/48924?format=json"
```

#### Today's SPC Reports
**`GET /api/spc/today`**

Get SPC reports for the current SPC day (12Z-12Z cycle).

**Example Request:**
```bash
curl "https://api.hailydb.com/api/spc/today"
```

### Testing & Validation Endpoints

#### Radar Parsing Test
**`POST /api/test/radar-parsing`**

Test radar-indicated data extraction from alert text.

**Request Body:**
```json
{
  "properties": {
    "event": "Severe Thunderstorm Warning",
    "headline": "Golf ball hail and 80 mph winds",
    "description": "Damaging winds of 80 mph and golf ball size hail expected."
  }
}
```

**Example Request:**
```bash
curl -X POST "https://api.hailydb.com/api/test/radar-parsing" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "event": "Severe Thunderstorm Warning", 
      "headline": "Golf ball hail and 80 mph winds",
      "description": "Damaging winds of 80 mph and golf ball size hail expected."
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "test_results": [
    {
      "test_case": 1,
      "input": {
        "event": "Severe Thunderstorm Warning",
        "headline": "Golf ball hail and 80 mph winds"
      },
      "radar_indicated": {
        "hail_inches": 1.75,
        "wind_mph": 80
      }
    }
  ]
}
```

#### Radar Parsing Statistics
**`GET /api/test/radar-summary`**

Get comprehensive radar parsing performance metrics.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/test/radar-summary"
```

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_severe_thunderstorm_warnings": 1456,
    "parsed_with_radar_data": 1456,
    "parsing_success_rate": "100.0%"
  },
  "sample_parsed_alerts": [
    {
      "id": "urn:oid:...",
      "area": "Harris County, TX",
      "radar_indicated": {
        "hail_inches": 1.0,
        "wind_mph": 60
      },
      "effective": "2025-08-12T01:30:00"
    }
  ]
}
```

#### Manual NWS Poll Trigger
**`POST /api/test/nws-poll`**

Manually trigger NWS alert ingestion for testing.

**Example Request:**
```bash
curl -X POST "https://api.hailydb.com/api/test/nws-poll"
```

**Response:**
```json
{
  "status": "success",
  "new_alerts": 4,
  "message": "Polling completed. 4 new alerts ingested."
}
```

### System Health & Monitoring

#### System Health Check
**`GET /api/health`**

Comprehensive system status and data freshness validation.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-12T02:30:00Z",
  "database": "healthy",
  "services": {
    "nws_ingestion": "active",
    "spc_ingestion": "active", 
    "live_radar": "active",
    "autonomous_scheduler": "running"
  },
  "data_freshness": {
    "last_nws_poll": "2025-08-12T02:25:00Z",
    "last_spc_poll": "2025-08-12T01:58:00Z",
    "minutes_since_last_update": 5
  },
  "statistics": {
    "total_alerts": 5939,
    "active_alerts": 206,
    "total_spc_reports": 45219,
    "verified_alerts": 127
  }
}
```

#### Internal Status (Comprehensive)
**`GET /internal/status`**

Detailed system diagnostics for monitoring and debugging.

**Example Request:**
```bash
curl "https://api.hailydb.com/internal/status"
```

### State Enrichment APIs

#### Batch State Enrichment
**`POST /api/state-enrichment/enrich`**

Batch process alerts with missing state information.

**Request Body:**
```json
{
  "batch_size": 100,
  "force_update": false
}
```

**Example Request:**
```bash
curl -X POST "https://api.hailydb.com/api/state-enrichment/enrich" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 100}'
```

#### State Enrichment Statistics
**`GET /api/state-enrichment/stats`**

Get state enrichment processing statistics.

**Example Request:**
```bash
curl "https://api.hailydb.com/api/state-enrichment/stats"
```

**Response:**
```json
{
  "total_alerts": 5939,
  "alerts_with_state": 5878,
  "alerts_missing_state": 61,
  "coverage_percentage": 98.97,
  "last_enrichment": "2025-08-12T01:45:00Z"
}
```

---

## Data Models

### Complete Alert Object Schema

```json
{
  "id": "urn:oid:2.49.0.1.840.0.{hash}.{sequence}.{version}",
  "event": "Severe Thunderstorm Warning|Tornado Warning|Special Weather Statement|...",
  "severity": "Minor|Moderate|Severe|Extreme",
  "area_desc": "County; County; County",
  "effective": "2025-08-12T02:24:00",
  "expires": "2025-08-12T03:00:00",
  "sent": "2025-08-12T02:24:00",
  "affected_states": ["TX", "OK"],
  "ai_summary": "string|null",
  "ai_tags": "string|null", 
  "city_names": "string|null",
  "coordinate_count": 10,
  "county_names": {},
  "duration_minutes": 36,
  "enhanced_geometry": {
    "affected_states": ["OK"],
    "coordinate_count": 10,
    "county_state_mapping": [],
    "coverage_area_sq_degrees": 0.2072,
    "fips_codes": [],
    "geometry_bounds": {
      "max_lat": 34.76,
      "max_lon": -95.29,
      "min_lat": 34.39,
      "min_lon": -95.85000000000001
    },
    "geometry_type": "Polygon",
    "has_detailed_geometry": true
  },
  "fips_codes": [],
  "geocode": {
    "SAME": ["040127", "040121", "040077"],
    "UGC": ["OKZ049", "OKZ073", "OKZ075"]
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-95.78, 34.5], [-95.77, 34.51], ...]]
  },
  "geometry_bounds": {
    "max_lat": 34.76,
    "max_lon": -95.29,
    "min_lat": 34.39,
    "min_lon": -95.85000000000001
  },
  "geometry_type": "Polygon",
  "ingested_at": "2025-08-12T02:25:03.012945",
  "is_active": true,
  "location_info": {
    "affected_zones": ["https://api.weather.gov/zones/forecast/OKZ049"],
    "area_description": "Pushmataha; Pittsburg; Latimer",
    "coordinate_count": 10,
    "counties": [],
    "fips_codes": [],
    "geocodes": {
      "SAME": ["040127", "040121", "040077"],
      "UGC": ["OKZ049", "OKZ073", "OKZ075"]
    },
    "geometry_bounds": {...},
    "geometry_type": "Polygon",
    "states": []
  },
  "properties": {
    "@id": "https://api.weather.gov/alerts/urn:oid:...",
    "@type": "wx:Alert",
    "affectedZones": ["https://api.weather.gov/zones/forecast/OKZ049"],
    "areaDesc": "Pushmataha; Pittsburg; Latimer",
    "category": "Met",
    "certainty": "Observed",
    "description": "Full NWS alert description text...",
    "effective": "2025-08-11T21:24:00-05:00",
    "event": "Special Weather Statement",
    "expires": "2025-08-11T22:00:00-05:00",
    "headline": "Special Weather Statement issued August 11 at 9:24PM CDT",
    "instruction": "If outdoors, consider seeking shelter inside a building.",
    "parameters": {
      "maxHailSize": ["0.00"],
      "maxWindGust": ["50 MPH"],
      "eventMotionDescription": ["2025-08-12T02:24:00-00:00...storm...345DEG...3KT..."]
    },
    "severity": "Moderate",
    "urgency": "Expected"
  },
  "radar_indicated": {
    "hail_inches": 0.0,
    "wind_mph": 50
  },
  "spc_ai_summary": "string|null",
  "spc_confidence_score": "number|null",
  "spc_match_method": "string|null",
  "spc_report_count": 0,
  "spc_reports": "array|null",
  "spc_verified": false,
  "updated_at": "2025-08-12T02:25:03.012945"
}
```

### SPC Report Object Schema

```json
{
  "id": 48924,
  "report_date": "2025-08-11",
  "report_type": "hail|wind|tornado",
  "time_utc": "2355",
  "location": "3 SSE Mahnomen",
  "county": "Mahnomen",
  "state": "MN",
  "latitude": 47.27,
  "longitude": -95.93,
  "magnitude": {
    "speed": 58,
    "size_hundredths": 175
  },
  "comments": "Corrects previous non-tstm wnd gst report from 3 SSE Mahnomen. Mesonet station MN044 Mahnomen MN DOT. (FGF)",
  "ingested_at": "2025-08-12T00:58:27.487366"
}
```

### Enhanced Context Schema (v4.0)

```json
{
  "version": "v4.0",
  "enhanced_summary": "Professional meteorological location analysis with 6-point geographic format",
  "has_spc_match": true,
  "spc_match_summary": "Conditional summary based on verification status",
  "location_context": {
    "nearby_places": ["City1", "City2"],
    "major_cities": ["MajorCity1", "MajorCity2"],
    "geographic_reference": "Regional geographic context"
  },
  "generated_at": "2025-08-12T01:00:00Z"
}
```

---

## Integration Examples

### Python Integration

#### Basic Alert Search

```python
import requests
import json

class HailyDBClient:
    def __init__(self, base_url="https://api.hailydb.com"):
        self.base_url = base_url
        
    def search_alerts(self, **kwargs):
        """Search alerts with filtering parameters"""
        response = requests.get(f"{self.base_url}/api/alerts/search", params=kwargs)
        response.raise_for_status()
        return response.json()
    
    def get_live_radar_alerts(self):
        """Get current radar-detected severe weather"""
        response = requests.get(f"{self.base_url}/api/live-radar-alerts?format=json")
        response.raise_for_status()
        return response.json()
    
    def get_spc_reports(self, **kwargs):
        """Get SPC storm reports with filtering"""
        response = requests.get(f"{self.base_url}/api/spc/reports", params=kwargs)
        response.raise_for_status()
        return response.json()

# Usage example
client = HailyDBClient()

# Get active severe weather with radar data
active_alerts = client.search_alerts(
    active_only=True,
    has_radar_data=True,
    min_hail=1.0,
    state="TX"
)

print(f"Found {len(active_alerts['alerts'])} severe weather alerts")

# Get today's hail reports
hail_reports = client.get_spc_reports(
    type="hail",
    date="2025-08-11"
)

print(f"Found {len(hail_reports['reports'])} hail reports")
```

#### Geographic Radius Search

```python
def find_alerts_near_location(client, lat, lon, radius_miles=25):
    """Find alerts within radius of coordinates"""
    alerts = client.search_alerts(
        active_only=True,
        has_radar_data=True
    )
    
    nearby_alerts = []
    for alert in alerts['alerts']:
        if alert.get('enhanced_geometry', {}).get('geometry_bounds'):
            bounds = alert['enhanced_geometry']['geometry_bounds']
            # Simple bounding box check (for production use proper geographic calculations)
            center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
            center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
            
            # Rough distance calculation (use geopy for precision)
            lat_diff = abs(center_lat - lat)
            lon_diff = abs(center_lon - lon)
            
            if lat_diff < 0.5 and lon_diff < 0.5:  # Approximate radius
                nearby_alerts.append(alert)
    
    return nearby_alerts

# Find alerts near Houston, TX
houston_alerts = find_alerts_near_location(client, 29.7604, -95.3698, 50)
```

#### Webhook Integration

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

@app.route('/webhook/hailydb', methods=['POST'])
def handle_hailydb_webhook():
    """Handle incoming HailyDB webhook notifications"""
    
    # Verify webhook signature (if configured)
    signature = request.headers.get('X-HailyDB-Signature')
    if signature:
        body = request.get_data()
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, f"sha256={expected_signature}"):
            return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.json
    event_type = data.get('event_type')
    
    if event_type == 'alert.created':
        alert = data['alert']
        
        # Process new severe weather alert
        if alert.get('radar_indicated', {}).get('hail_inches', 0) >= 2.0:
            send_critical_hail_notification(alert)
        
        if alert.get('radar_indicated', {}).get('wind_mph', 0) >= 75:
            send_critical_wind_notification(alert)
    
    elif event_type == 'spc.verified':
        # Alert has been verified against SPC reports
        process_verified_storm_event(data['alert'], data['spc_reports'])
    
    return jsonify({'status': 'processed'})

def send_critical_hail_notification(alert):
    """Process critical hail alerts (2+ inches)"""
    print(f"CRITICAL HAIL: {alert['radar_indicated']['hail_inches']}\" hail in {alert['area_desc']}")

def send_critical_wind_notification(alert):
    """Process critical wind alerts (75+ mph)"""
    print(f"CRITICAL WIND: {alert['radar_indicated']['wind_mph']} mph winds in {alert['area_desc']}")

def process_verified_storm_event(alert, spc_reports):
    """Process verified storm events for insurance/damage assessment"""
    print(f"VERIFIED STORM: {alert['event']} verified with {len(spc_reports)} SPC reports")
```

### JavaScript Integration

#### Frontend Dashboard

```javascript
class HailyDBClient {
    constructor(baseUrl = 'https://api.hailydb.com') {
        this.baseUrl = baseUrl;
    }
    
    async searchAlerts(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseUrl}/api/alerts/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return response.json();
    }
    
    async getLiveRadarAlerts() {
        const response = await fetch(`${this.baseUrl}/api/live-radar-alerts?format=json`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return response.json();
    }
    
    async getSPCReports(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseUrl}/api/spc/reports?${params}`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        return response.json();
    }
}

// Dashboard implementation
class WeatherDashboard {
    constructor() {
        this.client = new HailyDBClient();
        this.refreshInterval = 5 * 60 * 1000; // 5 minutes
        this.init();
    }
    
    async init() {
        await this.loadActiveAlerts();
        await this.loadLiveRadar();
        
        // Auto-refresh every 5 minutes
        setInterval(() => {
            this.loadActiveAlerts();
            this.loadLiveRadar();
        }, this.refreshInterval);
    }
    
    async loadActiveAlerts() {
        try {
            const data = await this.client.searchAlerts({
                active_only: true,
                has_radar_data: true,
                limit: 50
            });
            
            this.renderActiveAlerts(data.alerts);
        } catch (error) {
            console.error('Failed to load active alerts:', error);
        }
    }
    
    async loadLiveRadar() {
        try {
            const data = await this.client.getLiveRadarAlerts();
            this.renderLiveRadar(data.alerts);
        } catch (error) {
            console.error('Failed to load live radar:', error);
        }
    }
    
    renderActiveAlerts(alerts) {
        const container = document.getElementById('active-alerts');
        
        if (alerts.length === 0) {
            container.innerHTML = '<p>No active severe weather alerts</p>';
            return;
        }
        
        const html = alerts.map(alert => `
            <div class="alert-card ${this.getSeverityClass(alert.severity)}">
                <h3>${alert.event}</h3>
                <p><strong>Area:</strong> ${alert.area_desc}</p>
                <p><strong>Expires:</strong> ${new Date(alert.expires).toLocaleString()}</p>
                ${alert.radar_indicated ? `
                    <div class="radar-data">
                        ${alert.radar_indicated.hail_inches > 0 ? 
                            `<span class="hail">Hail: ${alert.radar_indicated.hail_inches}"</span>` : ''}
                        ${alert.radar_indicated.wind_mph > 0 ? 
                            `<span class="wind">Wind: ${alert.radar_indicated.wind_mph} mph</span>` : ''}
                    </div>
                ` : ''}
                ${alert.spc_verified ? '<span class="verified">✓ SPC Verified</span>' : ''}
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    renderLiveRadar(alerts) {
        const container = document.getElementById('live-radar');
        
        const html = `
            <h2>Live Radar Alerts (${alerts.length})</h2>
            <div class="radar-grid">
                ${alerts.map(alert => `
                    <div class="radar-card">
                        <h4>${alert.area_desc}</h4>
                        <div class="radar-metrics">
                            <span class="hail">🧊 ${alert.hail_inches}"</span>
                            <span class="wind">💨 ${alert.wind_mph} mph</span>
                        </div>
                        <p class="expires">Expires: ${new Date(alert.expires).toLocaleTimeString()}</p>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    getSeverityClass(severity) {
        const classes = {
            'Extreme': 'alert-extreme',
            'Severe': 'alert-severe', 
            'Moderate': 'alert-moderate',
            'Minor': 'alert-minor'
        };
        return classes[severity] || 'alert-unknown';
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    new WeatherDashboard();
});
```

#### Node.js Server Integration

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

class HailyDBService {
    constructor() {
        this.baseUrl = 'https://api.hailydb.com';
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }
    
    async getActiveAlertsForRegion(state, county = null) {
        const cacheKey = `alerts_${state}_${county || 'all'}`;
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        try {
            const params = {
                state,
                active_only: true,
                has_radar_data: true
            };
            
            if (county) {
                params.county = county;
            }
            
            const response = await axios.get(`${this.baseUrl}/api/alerts/search`, { params });
            const data = response.data;
            
            // Cache the response
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            return data;
        } catch (error) {
            console.error('Failed to fetch alerts:', error.message);
            throw error;
        }
    }
    
    async getInsuranceRelevantEvents(state, minHailSize = 1.0, minWindSpeed = 60) {
        try {
            const response = await axios.get(`${this.baseUrl}/api/alerts/search`, {
                params: {
                    state,
                    has_radar_data: true,
                    min_hail: minHailSize,
                    min_wind: minWindSpeed,
                    spc_verified: true,
                    limit: 100
                }
            });
            
            return response.data.alerts.map(alert => ({
                id: alert.id,
                event_type: alert.event,
                location: alert.area_desc,
                timestamp: alert.effective,
                hail_size: alert.radar_indicated?.hail_inches || 0,
                wind_speed: alert.radar_indicated?.wind_mph || 0,
                verified: alert.spc_verified,
                confidence: alert.spc_confidence_score,
                damage_potential: this.assessDamagePotential(alert)
            }));
        } catch (error) {
            console.error('Failed to fetch insurance events:', error.message);
            throw error;
        }
    }
    
    assessDamagePotential(alert) {
        const hail = alert.radar_indicated?.hail_inches || 0;
        const wind = alert.radar_indicated?.wind_mph || 0;
        
        if (hail >= 4.0 || wind >= 100) return 'EXTREME';
        if (hail >= 2.0 || wind >= 75) return 'HIGH';
        if (hail >= 1.0 || wind >= 60) return 'MODERATE';
        return 'LOW';
    }
}

// API Routes
const hailyDB = new HailyDBService();

app.get('/api/weather/active/:state', async (req, res) => {
    try {
        const { state } = req.params;
        const { county } = req.query;
        
        const alerts = await hailyDB.getActiveAlertsForRegion(state.toUpperCase(), county);
        
        res.json({
            state,
            county: county || null,
            total_alerts: alerts.total,
            active_alerts: alerts.alerts.length,
            alerts: alerts.alerts
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/insurance/events/:state', async (req, res) => {
    try {
        const { state } = req.params;
        const { min_hail = 1.0, min_wind = 60 } = req.query;
        
        const events = await hailyDB.getInsuranceRelevantEvents(
            state.toUpperCase(),
            parseFloat(min_hail),
            parseInt(min_wind)
        );
        
        res.json({
            state,
            criteria: { min_hail, min_wind },
            total_events: events.length,
            events
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

---

## Authentication

### Current Status
HailyDB currently operates without authentication requirements, providing open access to all API endpoints. This design choice supports:

- **Rapid Integration**: Immediate access for development and testing
- **Public Weather Data**: NWS and SPC data is inherently public information
- **Emergency Response**: No barriers during critical weather events

### Future Authentication (Production Deployment)

For production enterprise deployments, authentication will be implemented using:

#### API Key Authentication
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" "https://api.hailydb.com/api/alerts/search"
```

#### Rate Limiting by Authentication Tier
- **Free Tier**: 1,000 requests/hour
- **Standard Tier**: 10,000 requests/hour  
- **Enterprise Tier**: Unlimited with SLA guarantees

---

## Rate Limiting

### Current Implementation
Production deployment includes intelligent rate limiting:

- **Standard Rate**: 1,000 requests per hour per IP
- **Burst Allowance**: Up to 100 requests per minute
- **Geographic Distribution**: CDN-based global rate limiting

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1692123600
X-RateLimit-Retry-After: 3600
```

### Rate Limit Response
```json
{
  "error": "Rate limit exceeded",
  "limit": 1000,
  "remaining": 0,
  "reset_time": "2025-08-12T03:00:00Z",
  "retry_after": 3600
}
```

### Optimization Strategies

#### Client-Side Caching
```javascript
class CachedHailyDBClient {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }
    
    async searchAlerts(filters) {
        const cacheKey = JSON.stringify(filters);
        
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        const data = await this.apiCall('/api/alerts/search', filters);
        
        this.cache.set(cacheKey, {
            data,
            timestamp: Date.now()
        });
        
        return data;
    }
}
```

#### Batch Requests
```python
def batch_alert_lookup(client, alert_ids):
    """Efficiently lookup multiple alerts"""
    batch_size = 50
    results = []
    
    for i in range(0, len(alert_ids), batch_size):
        batch = alert_ids[i:i + batch_size]
        
        # Use search with ID filter instead of individual requests
        batch_alerts = client.search_alerts(
            ids=','.join(batch),
            limit=batch_size
        )
        
        results.extend(batch_alerts['alerts'])
        
        # Respect rate limits
        time.sleep(0.1)
    
    return results
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 200 | Success | Valid data returned |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Alert/report does not exist |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal system error |
| 503 | Service Unavailable | Maintenance mode |

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid state code 'XY'. Must be valid US state abbreviation.",
    "details": {
      "parameter": "state",
      "value": "XY",
      "valid_values": ["AL", "AK", "AZ", "..."]
    },
    "timestamp": "2025-08-12T02:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Common Error Scenarios

#### Invalid Parameters
```json
{
  "error": {
    "code": "INVALID_DATE_FORMAT",
    "message": "Date must be in YYYY-MM-DD format",
    "details": {
      "parameter": "date",
      "value": "08/12/2025",
      "expected_format": "YYYY-MM-DD"
    }
  }
}
```

#### Resource Not Found
```json
{
  "error": {
    "code": "ALERT_NOT_FOUND",
    "message": "Alert with ID 'invalid_id' not found",
    "details": {
      "alert_id": "invalid_id",
      "suggestion": "Check alert ID format: urn:oid:2.49.0.1.840.0.{hash}.{seq}.{ver}"
    }
  }
}
```

#### Rate Limiting
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit of 1000 requests per hour exceeded",
    "details": {
      "limit": 1000,
      "remaining": 0,
      "reset_time": "2025-08-12T03:00:00Z",
      "retry_after": 3600
    }
  }
}
```

### Client Error Handling Best Practices

#### Python Implementation
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HailyDBClient:
    def __init__(self, base_url="https://api.hailydb.com"):
        self.base_url = base_url
        self.session = self._create_session()
    
    def _create_session(self):
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def search_alerts(self, **kwargs):
        try:
            response = self.session.get(
                f"{self.base_url}/api/alerts/search",
                params=kwargs,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Handle rate limiting
                retry_after = int(e.response.headers.get('Retry-After', 3600))
                raise RateLimitError(f"Rate limited. Retry after {retry_after} seconds")
            
            elif e.response.status_code == 400:
                # Handle parameter errors
                error_data = e.response.json()
                raise ParameterError(error_data['error']['message'])
            
            else:
                raise APIError(f"HTTP {e.response.status_code}: {e.response.text}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to HailyDB API: {e}")

class HailyDBError(Exception):
    """Base exception for HailyDB API errors"""
    pass

class RateLimitError(HailyDBError):
    """Raised when rate limit is exceeded"""
    pass

class ParameterError(HailyDBError):
    """Raised when invalid parameters are provided"""
    pass

class APIError(HailyDBError):
    """Raised for general API errors"""
    pass
```

#### JavaScript Implementation
```javascript
class HailyDBClient {
    constructor(baseUrl = 'https://api.hailydb.com') {
        this.baseUrl = baseUrl;
    }
    
    async apiRequest(endpoint, params = {}) {
        const url = new URL(endpoint, this.baseUrl);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        const maxRetries = 3;
        let retryCount = 0;
        
        while (retryCount < maxRetries) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                if (response.status === 429) {
                    // Handle rate limiting
                    const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
                    
                    if (retryCount < maxRetries - 1) {
                        console.warn(`Rate limited. Retrying after ${retryAfter} seconds...`);
                        await this.sleep(retryAfter * 1000);
                        retryCount++;
                        continue;
                    } else {
                        throw new RateLimitError(`Rate limit exceeded. Retry after ${retryAfter} seconds.`);
                    }
                }
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => null);
                    const errorMessage = errorData?.error?.message || response.statusText;
                    throw new APIError(`HTTP ${response.status}: ${errorMessage}`);
                }
                
                return await response.json();
                
            } catch (error) {
                if (error instanceof RateLimitError || error instanceof APIError) {
                    throw error;
                }
                
                if (retryCount < maxRetries - 1) {
                    console.warn(`Request failed. Retrying... (${retryCount + 1}/${maxRetries})`);
                    await this.sleep(1000 * Math.pow(2, retryCount)); // Exponential backoff
                    retryCount++;
                } else {
                    throw new ConnectionError(`Failed to connect after ${maxRetries} attempts: ${error.message}`);
                }
            }
        }
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    async searchAlerts(filters = {}) {
        return this.apiRequest('/api/alerts/search', filters);
    }
}

class HailyDBError extends Error {
    constructor(message) {
        super(message);
        this.name = this.constructor.name;
    }
}

class RateLimitError extends HailyDBError {}
class APIError extends HailyDBError {}
class ConnectionError extends HailyDBError {}
```

---

## Webhooks

### Webhook Events

HailyDB supports real-time webhook notifications for external system integration:

#### Available Events

| Event Type | Description | Trigger Condition |
|------------|-------------|-------------------|
| `alert.created` | New alert ingested | NWS alert first ingested |
| `alert.updated` | Alert modified | Alert status or data changed |
| `alert.expired` | Alert expired | Alert expiration time reached |
| `spc.verified` | Alert SPC verified | Alert matched with SPC reports |
| `radar.detected` | Radar criteria met | Alert meets radar filtering criteria |

### Webhook Configuration

#### Setup Request
```json
{
  "url": "https://your-app.com/webhooks/hailydb",
  "events": ["alert.created", "spc.verified", "radar.detected"],
  "filters": {
    "states": ["TX", "FL", "CA"],
    "min_hail_inches": 1.0,
    "min_wind_mph": 60,
    "event_types": ["Severe Thunderstorm Warning", "Tornado Warning"]
  },
  "headers": {
    "Authorization": "Bearer your-webhook-secret"
  }
}
```

### Webhook Payload Format

#### Alert Created Event
```json
{
  "event_type": "alert.created",
  "timestamp": "2025-08-12T02:30:00Z",
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0.abc123...",
    "event": "Severe Thunderstorm Warning",
    "severity": "Severe",
    "area_desc": "Harris; Montgomery; Waller",
    "effective": "2025-08-12T02:30:00Z",
    "expires": "2025-08-12T03:30:00Z",
    "affected_states": ["TX"],
    "radar_indicated": {
      "hail_inches": 1.75,
      "wind_mph": 70
    },
    "geometry": {...},
    "is_active": true
  },
  "webhook_id": "webhook_123",
  "delivery_id": "delivery_456"
}
```

#### SPC Verified Event
```json
{
  "event_type": "spc.verified",
  "timestamp": "2025-08-12T03:00:00Z",
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0.abc123...",
    "event": "Severe Thunderstorm Warning",
    "spc_verified": true,
    "spc_confidence_score": 0.92,
    "spc_report_count": 3
  },
  "spc_reports": [
    {
      "id": 48924,
      "report_type": "hail",
      "magnitude": {"size_hundredths": 175},
      "location": "5 WNW AMARILLO",
      "county": "POTTER",
      "state": "TX"
    }
  ],
  "verification_summary": "Golf ball size hail confirmed by trained spotter at 5 WNW Amarillo, Potter County, TX",
  "webhook_id": "webhook_123", 
  "delivery_id": "delivery_789"
}
```

### Webhook Security

#### Signature Verification
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature for security"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, f"sha256={expected_signature}")

# Flask webhook handler
@app.route('/webhook/hailydb', methods=['POST'])
def handle_hailydb_webhook():
    signature = request.headers.get('X-HailyDB-Signature')
    payload = request.get_data()
    
    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.json
    process_webhook_event(data)
    
    return jsonify({'status': 'received'})
```

#### Retry Logic
```javascript
class WebhookHandler {
    constructor() {
        this.maxRetries = 3;
        this.backoffMultiplier = 2;
    }
    
    async handleWebhook(payload) {
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                await this.processWebhookPayload(payload);
                return { success: true };
                
            } catch (error) {
                console.error(`Webhook processing failed (attempt ${attempt}):`, error);
                
                if (attempt < this.maxRetries) {
                    const delay = 1000 * Math.pow(this.backoffMultiplier, attempt - 1);
                    await this.sleep(delay);
                } else {
                    return { success: false, error: error.message };
                }
            }
        }
    }
    
    async processWebhookPayload(payload) {
        const { event_type, alert } = payload;
        
        switch (event_type) {
            case 'alert.created':
                await this.handleNewAlert(alert);
                break;
                
            case 'spc.verified':
                await this.handleVerifiedAlert(alert, payload.spc_reports);
                break;
                
            case 'radar.detected':
                await this.handleRadarDetected(alert);
                break;
                
            default:
                console.warn(`Unknown event type: ${event_type}`);
        }
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
```

### Real-time Use Cases

#### Emergency Alert System
```python
class EmergencyAlertProcessor:
    def __init__(self):
        self.critical_thresholds = {
            'hail_inches': 2.0,
            'wind_mph': 75,
            'tornado_events': ['Tornado Warning', 'Tornado Watch']
        }
    
    def process_webhook(self, payload):
        alert = payload['alert']
        event_type = payload['event_type']
        
        if event_type == 'alert.created' and self.is_critical_alert(alert):
            self.send_emergency_notification(alert)
        
        elif event_type == 'spc.verified':
            self.update_damage_assessment(alert, payload['spc_reports'])
    
    def is_critical_alert(self, alert):
        radar = alert.get('radar_indicated', {})
        
        # Critical hail size
        if radar.get('hail_inches', 0) >= self.critical_thresholds['hail_inches']:
            return True
        
        # Critical wind speed
        if radar.get('wind_mph', 0) >= self.critical_thresholds['wind_mph']:
            return True
        
        # Tornado events
        if alert['event'] in self.critical_thresholds['tornado_events']:
            return True
        
        return False
    
    def send_emergency_notification(self, alert):
        message = f"CRITICAL WEATHER: {alert['event']} in {alert['area_desc']}"
        
        if alert.get('radar_indicated'):
            radar = alert['radar_indicated']
            if radar.get('hail_inches', 0) > 0:
                message += f" - Hail: {radar['hail_inches']}\""
            if radar.get('wind_mph', 0) > 0:
                message += f" - Wind: {radar['wind_mph']} mph"
        
        # Send to emergency services, mobile alerts, etc.
        self.dispatch_emergency_alert(message, alert)
```

#### Insurance Claims Processing
```python
class InsuranceClaimsProcessor:
    def process_verified_storm(self, alert, spc_reports):
        """Process SPC-verified storm events for claims"""
        
        # Extract damage-relevant information
        damage_assessment = self.assess_damage_potential(alert, spc_reports)
        
        # Create claim event record
        claim_event = {
            'event_id': alert['id'],
            'event_type': alert['event'],
            'location': alert['area_desc'],
            'timestamp': alert['effective'],
            'damage_assessment': damage_assessment,
            'verification_confidence': alert.get('spc_confidence_score', 0),
            'spc_reports': len(spc_reports)
        }
        
        # Notify claims processing system
        self.create_claim_event(claim_event)
        
        # Trigger geographic policy holder identification
        self.identify_affected_policies(alert['geometry'])
    
    def assess_damage_potential(self, alert, spc_reports):
        """Assess potential damage based on verified storm data"""
        max_hail = 0
        max_wind = 0
        
        for report in spc_reports:
            if report['report_type'] == 'hail':
                hail_inches = report['magnitude'].get('size_hundredths', 0) / 100
                max_hail = max(max_hail, hail_inches)
            elif report['report_type'] == 'wind':
                wind_mph = report['magnitude'].get('speed', 0)
                max_wind = max(max_wind, wind_mph)
        
        # Damage categories based on verified measurements
        if max_hail >= 4.0 or max_wind >= 100:
            return 'CATASTROPHIC'
        elif max_hail >= 2.0 or max_wind >= 75:
            return 'SEVERE'
        elif max_hail >= 1.0 or max_wind >= 60:
            return 'MODERATE'
        else:
            return 'MINOR'
```

---

## SDK Development

### Python SDK Foundation

Create a comprehensive Python SDK for HailyDB integration:

```python
"""
HailyDB Python SDK
Official Python client for the HailyDB Weather Intelligence API
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

@dataclass
class Alert:
    """HailyDB Alert object"""
    id: str
    event: str
    severity: str
    area_desc: str
    effective: datetime
    expires: datetime
    affected_states: List[str]
    radar_indicated: Optional[Dict]
    spc_verified: bool
    is_active: bool
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Alert':
        return cls(
            id=data['id'],
            event=data['event'],
            severity=data['severity'],
            area_desc=data['area_desc'],
            effective=datetime.fromisoformat(data['effective'].replace('Z', '+00:00')),
            expires=datetime.fromisoformat(data['expires'].replace('Z', '+00:00')),
            affected_states=data.get('affected_states', []),
            radar_indicated=data.get('radar_indicated'),
            spc_verified=data.get('spc_verified', False),
            is_active=data.get('is_active', False)
        )

@dataclass
class SPCReport:
    """SPC Storm Report object"""
    id: int
    report_type: str
    report_date: str
    location: str
    county: str
    state: str
    latitude: float
    longitude: float
    magnitude: Dict
    comments: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SPCReport':
        return cls(
            id=data['id'],
            report_type=data['report_type'],
            report_date=data['report_date'],
            location=data['location'],
            county=data['county'],
            state=data['state'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            magnitude=data.get('magnitude', {}),
            comments=data.get('comments', '')
        )

class HailyDB:
    """Main HailyDB API client"""
    
    def __init__(self, base_url: str = "https://api.hailydb.com"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def search_alerts(
        self,
        state: Optional[str] = None,
        county: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        active_only: bool = False,
        has_radar_data: bool = False,
        min_hail: Optional[float] = None,
        min_wind: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        page: int = 1
    ) -> Dict:
        """Search alerts with comprehensive filtering"""
        
        params = {
            'limit': limit,
            'page': page
        }
        
        if state:
            params['state'] = state
        if county:
            params['county'] = county
        if event_type:
            params['event_type'] = event_type
        if severity:
            params['severity'] = severity
        if active_only:
            params['active_only'] = 'true'
        if has_radar_data:
            params['has_radar_data'] = 'true'
        if min_hail:
            params['min_hail'] = min_hail
        if min_wind:
            params['min_wind'] = min_wind
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        response = self.session.get(f"{self.base_url}/api/alerts/search", params=params)
        response.raise_for_status()
        
        data = response.json()
        data['alerts'] = [Alert.from_dict(alert) for alert in data['alerts']]
        
        return data
    
    def get_alert(self, alert_id: str) -> Alert:
        """Get single alert by ID"""
        response = self.session.get(f"{self.base_url}/api/alerts/{alert_id}?format=json")
        response.raise_for_status()
        
        return Alert.from_dict(response.json())
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts"""
        response = self.session.get(f"{self.base_url}/api/alerts/active")
        response.raise_for_status()
        
        data = response.json()
        return [Alert.from_dict(alert) for alert in data['alerts']]
    
    def get_live_radar_alerts(self) -> List[Alert]:
        """Get current radar-detected severe weather alerts"""
        response = self.session.get(f"{self.base_url}/api/live-radar-alerts?format=json")
        response.raise_for_status()
        
        data = response.json()
        return [Alert.from_dict(alert) for alert in data['alerts']]
    
    def search_radius(
        self,
        lat: float,
        lon: float,
        radius: float,
        active_only: bool = False
    ) -> List[Alert]:
        """Find alerts within radius of coordinates"""
        params = {
            'lat': lat,
            'lon': lon,
            'radius': radius
        }
        
        if active_only:
            params['active_only'] = 'true'
        
        response = self.session.get(f"{self.base_url}/api/alerts/radius", params=params)
        response.raise_for_status()
        
        data = response.json()
        return [Alert.from_dict(alert) for alert in data['alerts']]
    
    def get_spc_reports(
        self,
        report_type: Optional[str] = None,
        state: Optional[str] = None,
        county: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """Get SPC storm reports with filtering"""
        
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if report_type:
            params['type'] = report_type
        if state:
            params['state'] = state
        if county:
            params['county'] = county
        if date:
            params['date'] = date
        
        response = self.session.get(f"{self.base_url}/api/spc/reports", params=params)
        response.raise_for_status()
        
        data = response.json()
        data['reports'] = [SPCReport.from_dict(report) for report in data['reports']]
        
        return data
    
    def get_spc_report(self, report_id: int) -> SPCReport:
        """Get single SPC report by ID"""
        response = self.session.get(f"{self.base_url}/api/spc/reports/{report_id}?format=json")
        response.raise_for_status()
        
        return SPCReport.from_dict(response.json())

# Utility functions
class HailyDBUtils:
    """Utility functions for HailyDB data processing"""
    
    @staticmethod
    def categorize_hail_damage(hail_inches: float) -> Dict:
        """Categorize hail damage potential"""
        if hail_inches >= 4.0:
            return {
                'category': 'Giant Hail',
                'severity': 'Extreme Damage',
                'description': 'Giant hail causes severe property damage including roof penetration, vehicle destruction, and injury risk.'
            }
        elif hail_inches >= 2.0:
            return {
                'category': 'Very Large Hail',
                'severity': 'Significant Damage', 
                'description': 'Very large hail causes substantial damage to vehicles, roofing, siding, and outdoor equipment.'
            }
        elif hail_inches >= 1.0:
            return {
                'category': 'Large Hail',
                'severity': 'Minor Damage',
                'description': 'Large hail can cause dents to vehicles, cracked windows, damage to roofing materials, siding, and gutters.'
            }
        else:
            return {
                'category': 'Small Hail',
                'severity': 'Minimal Damage',
                'description': 'Small hail typically causes minimal damage but can affect crops and outdoor equipment.'
            }
    
    @staticmethod
    def categorize_wind_damage(wind_mph: int) -> Dict:
        """Categorize wind damage potential"""
        if wind_mph >= 100:
            return {
                'category': 'Extreme Wind',
                'severity': 'Catastrophic Damage',
                'description': 'Extreme winds cause widespread structural damage, downed trees, and power outages.'
            }
        elif wind_mph >= 75:
            return {
                'category': 'Violent Wind',
                'severity': 'Severe Damage',
                'description': 'Violent winds cause significant structural damage and dangerous flying debris.'
            }
        elif wind_mph >= 60:
            return {
                'category': 'Damaging Wind',
                'severity': 'Moderate Damage',
                'description': 'Damaging winds can down large tree limbs and cause property damage.'
            }
        else:
            return {
                'category': 'Strong Wind',
                'severity': 'Minor Damage',
                'description': 'Strong winds may down small branches and cause minor property damage.'
            }

# Usage example
if __name__ == "__main__":
    # Initialize client
    hailydb = HailyDB()
    
    # Search for active severe weather in Texas
    texas_alerts = hailydb.search_alerts(
        state="TX",
        active_only=True,
        has_radar_data=True,
        min_hail=1.0
    )
    
    print(f"Found {len(texas_alerts['alerts'])} severe weather alerts in Texas")
    
    for alert in texas_alerts['alerts']:
        print(f"- {alert.event} in {alert.area_desc}")
        if alert.radar_indicated:
            hail = alert.radar_indicated.get('hail_inches', 0)
            wind = alert.radar_indicated.get('wind_mph', 0)
            
            if hail > 0:
                damage_info = HailyDBUtils.categorize_hail_damage(hail)
                print(f"  Hail: {hail}\" - {damage_info['category']}")
            
            if wind > 0:
                damage_info = HailyDBUtils.categorize_wind_damage(wind)
                print(f"  Wind: {wind} mph - {damage_info['category']}")
```

### JavaScript SDK Foundation

```javascript
/**
 * HailyDB JavaScript SDK
 * Official JavaScript client for the HailyDB Weather Intelligence API
 */

class HailyDB {
    constructor(baseUrl = 'https://api.hailydb.com') {
        this.baseUrl = baseUrl;
    }
    
    /**
     * Search alerts with comprehensive filtering
     */
    async searchAlerts(options = {}) {
        const {
            state,
            county,
            eventType,
            severity,
            activeOnly = false,
            hasRadarData = false,
            minHail,
            minWind,
            startDate,
            endDate,
            limit = 50,
            page = 1
        } = options;
        
        const params = new URLSearchParams({
            limit: limit.toString(),
            page: page.toString()
        });
        
        if (state) params.append('state', state);
        if (county) params.append('county', county);
        if (eventType) params.append('event_type', eventType);
        if (severity) params.append('severity', severity);
        if (activeOnly) params.append('active_only', 'true');
        if (hasRadarData) params.append('has_radar_data', 'true');
        if (minHail) params.append('min_hail', minHail.toString());
        if (minWind) params.append('min_wind', minWind.toString());
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        const response = await fetch(`${this.baseUrl}/api/alerts/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Transform alerts to Alert objects
        data.alerts = data.alerts.map(alertData => new Alert(alertData));
        
        return data;
    }
    
    /**
     * Get single alert by ID
     */
    async getAlert(alertId) {
        const response = await fetch(`${this.baseUrl}/api/alerts/${alertId}?format=json`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return new Alert(data);
    }
    
    /**
     * Get all currently active alerts
     */
    async getActiveAlerts() {
        const response = await fetch(`${this.baseUrl}/api/alerts/active`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return data.alerts.map(alertData => new Alert(alertData));
    }
    
    /**
     * Get current radar-detected severe weather alerts
     */
    async getLiveRadarAlerts() {
        const response = await fetch(`${this.baseUrl}/api/live-radar-alerts?format=json`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return data.alerts.map(alertData => new Alert(alertData));
    }
    
    /**
     * Find alerts within radius of coordinates
     */
    async searchRadius(lat, lon, radius, activeOnly = false) {
        const params = new URLSearchParams({
            lat: lat.toString(),
            lon: lon.toString(), 
            radius: radius.toString()
        });
        
        if (activeOnly) {
            params.append('active_only', 'true');
        }
        
        const response = await fetch(`${this.baseUrl}/api/alerts/radius?${params}`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return data.alerts.map(alertData => new Alert(alertData));
    }
    
    /**
     * Get SPC storm reports with filtering
     */
    async getSPCReports(options = {}) {
        const {
            type,
            state,
            county,
            date,
            limit = 100,
            offset = 0
        } = options;
        
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString()
        });
        
        if (type) params.append('type', type);
        if (state) params.append('state', state);
        if (county) params.append('county', county);
        if (date) params.append('date', date);
        
        const response = await fetch(`${this.baseUrl}/api/spc/reports?${params}`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        data.reports = data.reports.map(reportData => new SPCReport(reportData));
        
        return data;
    }
    
    /**
     * Get single SPC report by ID
     */
    async getSPCReport(reportId) {
        const response = await fetch(`${this.baseUrl}/api/spc/reports/${reportId}?format=json`);
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return new SPCReport(data);
    }
}

/**
 * Alert object class
 */
class Alert {
    constructor(data) {
        this.id = data.id;
        this.event = data.event;
        this.severity = data.severity;
        this.areaDesc = data.area_desc;
        this.effective = new Date(data.effective);
        this.expires = new Date(data.expires);
        this.affectedStates = data.affected_states || [];
        this.radarIndicated = data.radar_indicated;
        this.spcVerified = data.spc_verified || false;
        this.isActive = data.is_active || false;
        this.geometry = data.geometry;
        this.enhancedGeometry = data.enhanced_geometry;
    }
    
    /**
     * Check if alert is currently active
     */
    isCurrentlyActive() {
        const now = new Date();
        return now >= this.effective && now < this.expires;
    }
    
    /**
     * Get hail size if available
     */
    getHailSize() {
        return this.radarIndicated?.hail_inches || 0;
    }
    
    /**
     * Get wind speed if available
     */
    getWindSpeed() {
        return this.radarIndicated?.wind_mph || 0;
    }
    
    /**
     * Get damage assessment for hail
     */
    getHailDamageAssessment() {
        return HailyDBUtils.categorizeHailDamage(this.getHailSize());
    }
    
    /**
     * Get damage assessment for wind
     */
    getWindDamageAssessment() {
        return HailyDBUtils.categorizeWindDamage(this.getWindSpeed());
    }
}

/**
 * SPC Report object class
 */
class SPCReport {
    constructor(data) {
        this.id = data.id;
        this.reportType = data.report_type;
        this.reportDate = data.report_date;
        this.location = data.location;
        this.county = data.county;
        this.state = data.state;
        this.latitude = data.latitude;
        this.longitude = data.longitude;
        this.magnitude = data.magnitude || {};
        this.comments = data.comments || '';
    }
    
    /**
     * Get magnitude value based on report type
     */
    getMagnitudeValue() {
        if (this.reportType === 'hail') {
            return (this.magnitude.size_hundredths || 0) / 100;
        } else if (this.reportType === 'wind') {
            return this.magnitude.speed || 0;
        }
        return 0;
    }
    
    /**
     * Get formatted magnitude display
     */
    getMagnitudeDisplay() {
        if (this.reportType === 'hail') {
            const inches = this.getMagnitudeValue();
            return `${inches.toFixed(2)}"`;
        } else if (this.reportType === 'wind') {
            return `${this.getMagnitudeValue()} mph`;
        }
        return 'N/A';
    }
}

/**
 * Utility functions for HailyDB data processing
 */
class HailyDBUtils {
    /**
     * Categorize hail damage potential
     */
    static categorizeHailDamage(hailInches) {
        if (hailInches >= 4.0) {
            return {
                category: 'Giant Hail',
                severity: 'Extreme Damage',
                description: 'Giant hail causes severe property damage including roof penetration, vehicle destruction, and injury risk.'
            };
        } else if (hailInches >= 2.0) {
            return {
                category: 'Very Large Hail',
                severity: 'Significant Damage',
                description: 'Very large hail causes substantial damage to vehicles, roofing, siding, and outdoor equipment.'
            };
        } else if (hailInches >= 1.0) {
            return {
                category: 'Large Hail',
                severity: 'Minor Damage',
                description: 'Large hail can cause dents to vehicles, cracked windows, damage to roofing materials, siding, and gutters.'
            };
        } else {
            return {
                category: 'Small Hail',
                severity: 'Minimal Damage',
                description: 'Small hail typically causes minimal damage but can affect crops and outdoor equipment.'
            };
        }
    }
    
    /**
     * Categorize wind damage potential
     */
    static categorizeWindDamage(windMph) {
        if (windMph >= 100) {
            return {
                category: 'Extreme Wind',
                severity: 'Catastrophic Damage',
                description: 'Extreme winds cause widespread structural damage, downed trees, and power outages.'
            };
        } else if (windMph >= 75) {
            return {
                category: 'Violent Wind',
                severity: 'Severe Damage',
                description: 'Violent winds cause significant structural damage and dangerous flying debris.'
            };
        } else if (windMph >= 60) {
            return {
                category: 'Damaging Wind',
                severity: 'Moderate Damage',
                description: 'Damaging winds can down large tree limbs and cause property damage.'
            };
        } else {
            return {
                category: 'Strong Wind',
                severity: 'Minor Damage',
                description: 'Strong winds may down small branches and cause minor property damage.'
            };
        }
    }
    
    /**
     * Calculate distance between two coordinates (rough approximation)
     */
    static calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 3959; // Earth's radius in miles
        const dLat = this.toRadians(lat2 - lat1);
        const dLon = this.toRadians(lon2 - lon1);
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    static toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
}

// Export for Node.js environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HailyDB, Alert, SPCReport, HailyDBUtils };
}

// Usage example for browser
if (typeof window !== 'undefined') {
    // Browser usage example
    window.HailyDBExample = async function() {
        const hailydb = new HailyDB();
        
        try {
            // Get active severe weather in Texas
            const texasAlerts = await hailydb.searchAlerts({
                state: 'TX',
                activeOnly: true,
                hasRadarData: true,
                minHail: 1.0
            });
            
            console.log(`Found ${texasAlerts.alerts.length} severe weather alerts in Texas`);
            
            texasAlerts.alerts.forEach(alert => {
                console.log(`- ${alert.event} in ${alert.areaDesc}`);
                
                if (alert.getHailSize() > 0) {
                    const hailDamage = alert.getHailDamageAssessment();
                    console.log(`  Hail: ${alert.getHailSize()}" - ${hailDamage.category}`);
                }
                
                if (alert.getWindSpeed() > 0) {
                    const windDamage = alert.getWindDamageAssessment();
                    console.log(`  Wind: ${alert.getWindSpeed()} mph - ${windDamage.category}`);
                }
            });
            
        } catch (error) {
            console.error('Error fetching alerts:', error);
        }
    };
}
```

---

## Performance & Monitoring

### Production Performance Metrics

**Database Performance**
- Query Response Time: **0.113ms average**
- Connection Pool: 20 connections with pre-ping validation
- Query Optimization: GIN indexes on JSONB fields
- Row-level Deduplication: Hash-based duplicate detection

**API Response Times**
- Search Endpoints: **273ms average** 
- Single Alert Lookup: **45ms average**
- Live Radar Alerts: **156ms average**
- SPC Reports: **189ms average**

**Data Processing Performance**
- NWS Alert Ingestion: **5-minute autonomous polling**
- SPC Report Processing: **60-minute polling cycles** 
- Real-time Matching: **30-minute verification cycles**
- Radar Parsing Success: **100% parsing rate**

### Monitoring Endpoints

#### System Health Dashboard
```bash
# Comprehensive system status
curl "https://api.hailydb.com/internal/status"
```

**Response includes:**
- Database connection health
- Last ingestion timestamps  
- Active alert counts
- Processing error rates
- Scheduler operation statistics
- Data freshness indicators

#### Performance Metrics
```bash
# API performance statistics
curl "https://api.hailydb.com/api/health"
```

**Tracks:**
- Request response times
- Error rates by endpoint
- Database query performance
- Cache hit ratios
- Concurrent user metrics

### Real-time Monitoring Integration

#### Datadog Integration
```python
import datadog
from datadog import statsd

class HailyDBMonitoring:
    def __init__(self):
        datadog.initialize(api_key='your_api_key', app_key='your_app_key')
    
    def track_api_request(self, endpoint, response_time, status_code):
        # Track API performance
        statsd.timing('hailydb.api.response_time', response_time, tags=[f'endpoint:{endpoint}'])
        statsd.increment('hailydb.api.requests', tags=[f'status:{status_code}', f'endpoint:{endpoint}'])
    
    def track_data_ingestion(self, source, new_records, total_records):
        # Track data ingestion metrics
        statsd.gauge('hailydb.ingestion.new_records', new_records, tags=[f'source:{source}'])
        statsd.gauge('hailydb.ingestion.total_records', total_records, tags=[f'source:{source}'])
    
    def track_alert_creation(self, event_type, severity, has_radar_data):
        # Track alert creation patterns
        statsd.increment('hailydb.alerts.created', tags=[
            f'event_type:{event_type}',
            f'severity:{severity}',
            f'has_radar:{has_radar_data}'
        ])
```

#### Prometheus Integration
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
api_requests_total = Counter('hailydb_api_requests_total', 'Total API requests', ['endpoint', 'status'])
api_request_duration = Histogram('hailydb_api_request_duration_seconds', 'API request duration', ['endpoint'])
active_alerts_gauge = Gauge('hailydb_active_alerts_total', 'Number of active alerts')
ingestion_records = Counter('hailydb_ingestion_records_total', 'Total ingested records', ['source'])

class PrometheusMonitoring:
    @staticmethod
    def track_api_request(endpoint, duration, status_code):
        api_requests_total.labels(endpoint=endpoint, status=status_code).inc()
        api_request_duration.labels(endpoint=endpoint).observe(duration)
    
    @staticmethod
    def update_active_alerts(count):
        active_alerts_gauge.set(count)
    
    @staticmethod
    def track_ingestion(source, count):
        ingestion_records.labels(source=source).inc(count)

# Start Prometheus metrics server
start_http_server(8000)
```

### Alerting Configuration

#### Critical System Alerts
```yaml
# AlertManager configuration
groups:
- name: hailydb_critical
  rules:
  - alert: HighAPIErrorRate
    expr: rate(hailydb_api_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High API error rate detected"
      description: "API error rate is {{ $value }} errors per second"
  
  - alert: IngestionLag
    expr: time() - hailydb_last_ingestion_timestamp > 600
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Data ingestion lag detected"
      description: "No new data ingested for {{ $value }} seconds"
  
  - alert: DatabaseConnectionFailure
    expr: hailydb_database_connections_failed_total > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failures"
      description: "{{ $value }} database connection failures detected"
```

### Performance Optimization

#### Database Query Optimization
```sql
-- Critical indexes for performance
CREATE INDEX CONCURRENTLY idx_alerts_active 
ON alerts (effective, expires) 
WHERE expires > NOW();

CREATE INDEX CONCURRENTLY idx_alerts_radar_data 
ON alerts USING GIN (radar_indicated) 
WHERE radar_indicated IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_alerts_state_search 
ON alerts (affected_states, event, severity, ingested_at DESC);

CREATE INDEX CONCURRENTLY idx_spc_reports_location 
ON spc_reports (state, county, report_date DESC);

-- Query performance analysis
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM alerts 
WHERE effective <= NOW() 
  AND expires > NOW() 
  AND radar_indicated IS NOT NULL
ORDER BY severity DESC, ingested_at DESC 
LIMIT 50;
```

#### Caching Strategy
```python
from functools import lru_cache
import redis
import json

class HailyDBCache:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cache_timeout = 300  # 5 minutes
    
    @lru_cache(maxsize=1000)
    def get_active_alerts_cached(self, cache_key):
        """Memory-based cache for frequent queries"""
        return self._fetch_active_alerts()
    
    def get_alerts_with_redis_cache(self, filters):
        """Redis-based cache for complex queries"""
        cache_key = f"alerts:{hash(json.dumps(filters, sort_keys=True))}"
        
        # Try to get from Redis
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        # Fetch from database
        result = self._fetch_alerts_from_db(filters)
        
        # Cache in Redis
        self.redis_client.setex(
            cache_key, 
            self.cache_timeout, 
            json.dumps(result)
        )
        
        return result
    
    def invalidate_cache(self, pattern="alerts:*"):
        """Invalidate cached data when new alerts are ingested"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)
```

---

## Production Deployment

### Replit Deployment Configuration

HailyDB is optimized for Replit Production deployment with the following configuration:

#### Environment Configuration
```bash
# Environment variables for production
DATABASE_URL=postgresql://user:pass@host:port/db
FLASK_ENV=production
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=30
OPENAI_API_KEY=sk-your-openai-key
```

#### Production Startup
```python
# main.py - Production entry point
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

#### Gunicorn Configuration
```python
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

### Domain Configuration

**Production Domain:** `api.hailydb.com`

```bash
# DNS Configuration
CNAME api.hailydb.com -> your-replit-domain.replit.app
```

### SSL/TLS Configuration

Production deployment includes automatic SSL/TLS:
- **Certificate Authority:** Let's Encrypt
- **Auto-renewal:** Enabled
- **TLS Version:** 1.2+ required
- **HSTS:** Enabled with 1-year max-age

### Backup & Recovery

#### Database Backup Strategy
```bash
# Automated daily backups
pg_dump $DATABASE_URL | gzip > backups/hailydb_$(date +%Y%m%d).sql.gz

# Point-in-time recovery
pg_basebackup -D backup_dir -Ft -z -P -U backup_user
```

#### Data Recovery Procedures
```python
class HailyDBBackup:
    def __init__(self):
        self.backup_bucket = 's3://hailydb-backups'
        
    def create_daily_backup(self):
        """Create daily database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"hailydb_backup_{timestamp}.sql.gz"
        
        # Create database dump
        subprocess.run([
            'pg_dump', os.environ['DATABASE_URL'],
            '--compress=9',
            '--file', backup_file
        ])
        
        # Upload to cloud storage
        self.upload_to_s3(backup_file)
        
    def restore_from_backup(self, backup_date):
        """Restore database from specific backup"""
        backup_file = f"hailydb_backup_{backup_date}.sql.gz"
        
        # Download from cloud storage
        self.download_from_s3(backup_file)
        
        # Restore database
        subprocess.run([
            'psql', os.environ['DATABASE_URL'],
            '--file', backup_file
        ])
```

### Monitoring & Alerts

#### Production Monitoring Stack
- **Application Monitoring:** Custom health endpoints
- **Infrastructure Monitoring:** Replit system metrics
- **Log Aggregation:** Centralized logging with JSON formatting
- **Error Tracking:** Automatic error capture and notification

#### Alert Configuration
```python
class ProductionAlerts:
    def __init__(self):
        self.alert_thresholds = {
            'api_error_rate': 0.05,  # 5% error rate
            'ingestion_lag': 600,    # 10 minutes
            'db_connection_failures': 3,
            'response_time': 5000    # 5 seconds
        }
    
    def check_system_health(self):
        """Monitor system health and send alerts"""
        metrics = self.collect_metrics()
        
        for metric, threshold in self.alert_thresholds.items():
            if metrics[metric] > threshold:
                self.send_alert(metric, metrics[metric], threshold)
    
    def send_alert(self, metric, value, threshold):
        """Send alert notification"""
        message = f"ALERT: {metric} = {value} exceeds threshold {threshold}"
        
        # Send to monitoring system (Slack, PagerDuty, etc.)
        self.notify_operations_team(message)
```

---

## Development Setup

### Local Development Environment

#### Prerequisites
```bash
# Required software
Python 3.11+
PostgreSQL 15+
Git
```

#### Installation
```bash
# Clone repository
git clone https://github.com/your-org/hailydb.git
cd hailydb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

#### Database Setup
```bash
# Create local database
createdb hailydb_dev

# Set database URL
export DATABASE_URL="postgresql://username:password@localhost:5432/hailydb_dev"

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

#### Configuration Files

**requirements.txt**
```
Flask==3.0.0
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
gunicorn==21.2.0
openai==1.3.0
requests==2.31.0
shapely==2.0.2
cachetools==5.3.2
trafilatura==1.6.4
geopy==2.4.0
apscheduler==3.10.4
email-validator==2.1.0
werkzeug==3.0.1
```

**pyproject.toml**
```toml
[project]
name = "hailydb"
version = "2.0.0"
description = "National Weather Service Alert Intelligence Platform"
authors = [{name = "HailyDB Team", email = "team@hailydb.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"

dependencies = [
    "flask>=3.0.0",
    "sqlalchemy>=2.0.23",
    "psycopg2-binary>=2.9.9",
    "gunicorn>=21.2.0",
    "openai>=1.3.0",
    "requests>=2.31.0",
    "shapely>=2.0.2",
    "cachetools>=5.3.2",
    "trafilatura>=1.6.4",
    "geopy>=2.4.0",
    "apscheduler>=3.10.4",
    "email-validator>=2.1.0",
    "werkzeug>=3.0.1"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0"
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### Development Commands
```bash
# Start development server
python main.py

# Run tests
pytest tests/

# Code formatting
black .

# Type checking
mypy .

# Database migrations (if using Alembic)
alembic upgrade head
```

### Testing Framework

#### Unit Tests
```python
# tests/test_api.py
import pytest
from app import app, db
from models import Alert, SPCReport

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_alerts_search(client):
    """Test alerts search endpoint"""
    response = client.get('/api/alerts/search?limit=10')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'alerts' in data
    assert 'pagination' in data
    assert 'filters' in data

def test_live_radar_alerts(client):
    """Test live radar alerts endpoint"""
    response = client.get('/api/live-radar-alerts?format=json')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'alerts' in data
    assert 'total_qualifying' in data

def test_spc_reports(client):
    """Test SPC reports endpoint"""
    response = client.get('/api/spc/reports?limit=5')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'reports' in data
    assert 'pagination' in data
```

#### Integration Tests
```python
# tests/test_integration.py
import requests
import pytest

class TestAPIIntegration:
    base_url = "http://localhost:5000"
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{self.base_url}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'healthy'
    
    def test_alert_search_pagination(self):
        """Test alert search pagination"""
        response = requests.get(f"{self.base_url}/api/alerts/search?limit=5&page=1")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['alerts']) <= 5
        assert data['page'] == 1
    
    def test_geographic_search(self):
        """Test geographic radius search"""
        response = requests.get(f"{self.base_url}/api/alerts/radius?lat=29.7604&lon=-95.3698&radius=50")
        assert response.status_code == 200
        
        data = response.json()
        assert 'alerts' in data
```

### CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: hailydb_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov black flake8 mypy
    
    - name: Run linting
      run: |
        black --check .
        flake8 .
        mypy .
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/hailydb_test
      run: |
        pytest tests/ --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deploying to Replit production..."
        # Deployment commands here
```

---

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/new-feature`
3. **Make changes and add tests**
4. **Run test suite:** `pytest tests/`
5. **Submit pull request with detailed description**

### Code Standards

#### Python Style Guide
```python
# Follow PEP 8 with Black formatting
# Line length: 100 characters
# Use type hints for all functions

def search_alerts(
    state: Optional[str] = None,
    active_only: bool = False,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Search alerts with filtering parameters.
    
    Args:
        state: State abbreviation filter
        active_only: Only return active alerts
        limit: Maximum number of results
        
    Returns:
        Dictionary containing alerts and metadata
    """
    pass
```

#### API Design Guidelines
- **RESTful endpoints** with consistent naming
- **JSON responses** with standardized structure
- **Comprehensive error handling** with descriptive messages
- **Pagination support** for all list endpoints
- **Filtering parameters** following query parameter conventions

#### Database Guidelines
- **Migration scripts** for all schema changes
- **Row-level security** where applicable
- **Performance optimization** with proper indexing
- **Data validation** at model level

### Pull Request Process

1. **Description:** Clear description of changes and motivation
2. **Testing:** All tests passing with adequate coverage
3. **Documentation:** Updated documentation for API changes
4. **Performance:** No significant performance degradation
5. **Security:** Security implications reviewed and addressed

### Issue Reporting

#### Bug Reports
```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce the behavior:
1. Call API endpoint '...'
2. With parameters '...'
3. See error

**Expected behavior**
Description of expected behavior.

**Environment**
- OS: [e.g. macOS, Linux]
- Python version: [e.g. 3.11]
- HailyDB version: [e.g. 2.0.0]

**Additional context**
Any other context about the problem.
```

#### Feature Requests
```markdown
**Feature description**
Clear description of the proposed feature.

**Use case**
Specific use case or business need.

**Proposed solution**
Detailed description of the proposed implementation.

**Alternative solutions**
Any alternative approaches considered.
```

---

## License

MIT License

Copyright (c) 2025 HailyDB Team

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to use and interact with the HailyDB API and associated tools without restriction, subject to the following conditions:

Limited-Time Free Access – For a limited and undefined period, the HailyDB API is freely accessible for public use.

Future Premium Model – The HailyDB API will transition to a tokenized access model with monthly subscription tiers. Access will require an API token purchased through our subscription service.

Support via Donations – While the API is free during this period, users are encouraged to support ongoing development via voluntary donations.

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Planned Pricing (HailyDB + HailyAI Assistant Access)
Tier    Price / Month   Key Limits & Features
Free    $0      - Limited daily API calls
- Basic storm event search (last 7 days)
- Public event map access
- No CSV export
- No HailyAI Assistant access
Basic   $19     - Up to 10k API calls/month
- 6-month historical data access
- CSV export
- Advanced event filtering
- Basic rate-limited API keys
- Email support
- No HailyAI Assistant access
Plus    $49     - Up to 50k API calls/month
- 1-year historical data access
- Advanced filtering and geospatial search
- CSV and JSON export
- Priority API processing
- HailyAI Assistant access (up to 25 queries/day)
- Saved searches & alerts
- Early access to beta features
Premium Enterprise-Based Pricing        - Custom API call quotas
- Full historical database access
- Real-time alert feed with webhooks
- Unlimited HailyAI Assistant usage for teams
- Bulk data exports
- Dedicated account manager
- Custom integrations & SLAs

---

## Support & Contact

- **Documentation:** [https://api.hailydb.com/docs](https://api.hailydb.com/docs)
- **API Status:** [https://api.hailydb.com/api/health](https://api.hailydb.com/api/health)
- **Issues:** [GitHub Issues](https://github.com/your-org/hailydb/issues)
- **Email:** support@hailydb.com

### Community

- **Discord:** [HailyDB Community](https://discord.gg/hailydb)
- **Twitter:** [@HailyDB](https://twitter.com/hailydb)
- **Blog:** [Technical Blog](https://blog.hailydb.com)

---

*Last updated: August 12, 2025*
*Version: 2.0.0*
*API Version: v1*