
# HailyDB Enhanced API Documentation

## Overview

HailyDB provides comprehensive RESTful API access to National Weather Service alerts with advanced features including radar-indicated measurements, real-time webhooks, full geometry processing, Storm Prediction Center verification, and AI-enriched summaries. Perfect for insurance claims, field operations, emergency management, and partner integrations.

**Base URL**: `https://your-hailydb.replit.app`

## 🚀 New Enhanced Features

### Feature 1: Radar-Indicated Parsing
- **Hail Size Detection**: Automatically extracts hail measurements (0.75" - 2.0"+) from Severe Thunderstorm Warnings
- **Wind Speed Analysis**: Parses radar-indicated wind speeds (58-80+ mph) from NWS text
- **Immediate Intelligence**: Provides actionable data before SPC verification
- **API Fields**: `radar_indicated.hail_inches`, `radar_indicated.wind_mph`

### Feature 2: Real-Time Webhooks System  
- **Event Triggers**: Hail size, wind speed, and damage probability thresholds
- **HTTP POST Delivery**: Reliable webhook dispatch with retry logic
- **Geographic Filtering**: State, county, and FIPS-based location targeting
- **Admin API**: Complete webhook rule management endpoints

### Feature 3: Full Geometry & County Mapping
- **FIPS Code Extraction**: Precise county-level geographic identifiers
- **Coordinate Analysis**: Geometry bounds, coverage area calculation
- **Enhanced Location Data**: County-state mapping for insurance claims
- **Spatial Intelligence**: Comprehensive geographic processing for field operations

## Authentication

No authentication required for public endpoints. Internal endpoints are for administrative use.

---

## 🚨 Alert Endpoints

### Get All Alerts
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

**Example**:
```
GET /alerts?state=TX&severity=Severe&active_only=true&per_page=25
```

**Response**:
```json
{
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.uuid",
      "event": "Tornado Warning",
      "severity": "Extreme",
      "area_desc": "Harris County, TX",
      "effective": "2025-06-03T15:30:00Z",
      "expires": "2025-06-03T16:30:00Z",
      "ai_summary": "AI-generated summary",
      "ai_tags": ["tornado", "immediate_threat"]
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 5,
    "per_page": 25,
    "total": 123
  }
}
```

### Get Single Alert
```
GET /alerts/{alert_id}
```
**Description**: Retrieve detailed information for a specific alert

**Response**:
```json
{
  "id": "alert_id", 
  "event": "Severe Thunderstorm Warning",
  "severity": "Moderate",
  "area_desc": "Harris, TX; Montgomery, TX",
  "effective": "2025-06-10T20:15:00Z",
  "expires": "2025-06-10T21:00:00Z",
  "sent": "2025-06-10T20:14:32Z",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": { /* Full NWS alert properties */ },
  "raw": { /* Complete original NWS alert data */ },
  
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
  "spc_match_method": "fips",
  "spc_report_count": 1,
  
  "enhanced_geometry": {
    "has_detailed_geometry": true,
    "coverage_area_sq_degrees": 0.125,
    "county_state_mapping": [...],
    "affected_states": ["TX"]
  },
  
  "ai_summary": "Severe thunderstorm with quarter-size hail and 70 mph winds affecting northwestern Harris County and southern Montgomery County.",
  "ai_tags": ["hail", "damaging_winds", "property_damage_risk"],
  
  "ingested_at": "2025-06-10T20:15:30Z",
  "updated_at": "2025-06-10T20:16:45Z"
}
```

### Get Alert Summaries
```
GET /alerts/summary
```
**Description**: Get recent alerts with AI-generated summaries and verification data

**Response**:
```json
{
  "summaries": [
    {
      "id": "alert_id",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "Dallas County, TX",
      "effective": "2025-06-03T14:00:00Z",
      "expires": "2025-06-03T15:00:00Z",
      "ai_summary": "AI-generated alert summary",
      "ai_tags": ["severe_thunderstorm", "hail"],
      "spc_verified": true,
      "spc_verification_summary": "AI summary of SPC verification",
      "spc_confidence_score": 0.9,
      "spc_report_count": 3,
      "verification_status": "verified_with_ai_summary"
    }
  ],
  "total_count": 20,
  "verified_count": 12,
  "ai_summary_count": 8
}
```

### Get Active Alerts
```
GET /api/alerts/active
```
**Description**: Get all currently active alerts (within effective/expires window)

**Response**:
```json
{
  "timestamp": "2025-06-03T16:00:00Z",
  "total_active": 15,
  "alerts": [
    {
      "id": "alert_id",
      "event": "High Wind Warning",
      "severity": "Moderate",
      "area_desc": "Cook County, IL",
      "effective": "2025-06-03T10:00:00Z",
      "expires": "2025-06-03T20:00:00Z",
      "ai_summary": "High winds expected",
      "ai_tags": ["high_wind", "power_outages"]
    }
  ]
}
```

### Search Alerts
```
GET /api/alerts/search
```
**Description**: Advanced search with external application-friendly parameters

**Query Parameters**:
- `state` (string) - State name or abbreviation
- `county` (string) - County name
- `area` (string) - Area description
- `severity` (string) - Alert severity
- `event_type` (string) - Event type (partial match)
- `active_only` (boolean) - Filter to active alerts only
- `page` (int) - Page number
- `limit` (int, max: 100) - Results per page

**Response**:
```json
{
  "total": 50,
  "page": 1,
  "limit": 25,
  "pages": 2,
  "filters": {
    "state": "TX",
    "severity": "Severe",
    "active_only": true
  },
  "alerts": [{ /* Alert objects */ }]
}
```

### Get Alerts by State
```
GET /api/alerts/by-state/{state}
```
**Parameters**: 
- `active_only` (boolean) - Filter to active alerts

**Response**:
```json
{
  "state": "TX",
  "total_alerts": 25,
  "alerts": [{ /* Alert objects */ }]
}
```

### Get Alerts by County
```
GET /api/alerts/by-county/{state}/{county}
```
**Parameters**: 
- `active_only` (boolean) - Filter to active alerts

**Response**:
```json
{
  "state": "TX",
  "county": "Harris",
  "total_alerts": 8,
  "alerts": [{ /* Alert objects */ }]
}
```

---

## 🌪️ SPC (Storm Prediction Center) Endpoints

### Get SPC Reports
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

**Example**:
```
GET /api/spc/reports?type=tornado&state=KS&date=2025-06-01
```

**Response**:
```json
{
  "reports": [
    {
      "id": 123,
      "report_type": "tornado",
      "report_date": "2025-06-01",
      "time_utc": "1830",
      "location": "2 SW Dodge City",
      "county": "Ford",
      "state": "KS",
      "lat": 37.7000,
      "lon": -100.0500,
      "f_scale": "EF2",
      "comments": "Tornado damaged several buildings"
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 100,
    "offset": 0,
    "has_more": false
  },
  "filters": {
    "type": "tornado",
    "state": "KS",
    "date": "2025-06-01"
  }
}
```

### View SPC Reports (Web Interface)
```
GET /spc/reports
```
**Description**: Web interface for browsing SPC reports

---

## ✅ SPC Verification & Matching Endpoints

### Get SPC Verified Matches
```
GET /spc-matches/data
```
**Description**: API endpoint for verified NWS alert to SPC report matches

**Query Parameters**:
- `hours` (int, default: 168) - Time window in hours (168 = 7 days)
- `event` (string) - Filter by alert event type
- `method` (string) - Filter by matching method: "fips_exact", "proximity"
- `confidence` (string) - Filter by confidence: "high" (≥0.8), "medium" (0.5-0.8), "low" (<0.5)
- `state` (string) - Filter by state abbreviation

**Response**:
```json
{
  "summary": {
    "verified_count": 45,
    "total_reports": 128,
    "high_confidence_count": 38,
    "verification_rate": 12.5
  },
  "matches": [
    {
      "id": "alert_id",
      "effective": "2025-06-01T20:00:00Z",
      "event": "Tornado Warning",
      "area_desc": "Ford County, KS",
      "match_method": "fips_exact",
      "confidence": 0.9,
      "report_count": 2,
      "spc_reports": [
        {
          "report_type": "tornado",
          "time_utc": "2030",
          "location": "3 N Dodge City",
          "county": "Ford",
          "state": "KS",
          "comments": "EF1 tornado"
        }
      ],
      "spc_ai_summary": "AI-generated verification summary"
    }
  ],
  "states": ["KS", "TX", "OK", "NE"]
}
```

### Get SPC Verified Matches (Web Interface)
```
GET /spc-matches
```
**Description**: Web interface for browsing verified matches

### SPC Calendar Verification
```
GET /api/spc/calendar-verification
```
**Description**: 2-month calendar view of SPC data verification status

**Query Parameters**:
- `offset` (int, default: 0) - Time offset: 0=current period, -1=previous 2 months, 1=next 2 months

**Response**:
```json
{
  "status": "success",
  "results": [
    {
      "date": "2025-06-01",
      "day": 1,
      "hailydb_count": 25,
      "spc_live_count": 25,
      "match_status": "MATCH"
    },
    {
      "date": "2025-06-02",
      "day": 2,
      "hailydb_count": 18,
      "spc_live_count": 20,
      "match_status": "MISMATCH"
    }
  ],
  "date_range": {
    "start": "2025-05-01",
    "end": "2025-06-30"
  },
  "last_updated": "2025-06-03T16:00:00Z"
}
```

---

## 🤖 AI Enrichment Endpoints

### Batch Enrichment
```
POST /api/alerts/enrich-batch
```
**Description**: Enrich a batch of unenriched alerts with AI summaries

**Request Body**:
```json
{
  "limit": 50
}
```

**Response**:
```json
{
  "status": "success",
  "enriched": 45,
  "failed": 5,
  "total_processed": 50,
  "message": "Successfully enriched 45 alerts"
}
```

### Category-Specific Enrichment
```
POST /api/alerts/enrich-by-category
```
**Description**: Enrich alerts by weather category

**Request Body**:
```json
{
  "category": "Severe Weather Alert",
  "limit": 100
}
```

**Response**:
```json
{
  "status": "success",
  "category": "Severe Weather Alert",
  "enriched": 78,
  "failed": 2,
  "total_processed": 80,
  "message": "Successfully enriched 78 'Severe Weather Alert' alerts"
}
```

### Priority Alert Enrichment
```
POST /api/alerts/enrich-priority
```
**Description**: Enrich all high-priority alerts (Severe Weather, Tropical Weather, High Wind)

**Response**:
```json
{
  "status": "success",
  "enriched": 32,
  "failed": 1,
  "total_processed": 33,
  "message": "Successfully enriched 32 priority alerts"
}
```

### Get Enrichment Statistics
```
GET /api/alerts/enrichment-stats
```
**Description**: Get comprehensive enrichment coverage statistics

**Response**:
```json
{
  "total_alerts": 1250,
  "enriched_alerts": 892,
  "enrichment_rate": 71.4,
  "categories": {
    "Severe Weather Alert": {
      "total": 245,
      "enriched": 240,
      "rate": 98.0
    },
    "Winter Weather Alert": {
      "total": 189,
      "enriched": 145,
      "rate": 76.7
    }
  },
  "priority_coverage": {
    "total_priority": 156,
    "enriched_priority": 152,
    "priority_rate": 97.4
  }
}
```

### Get Unenriched Counts
```
GET /api/alerts/unenriched-counts
```
**Description**: Get counts of alerts needing enrichment by category

**Response**:
```json
{
  "priority_alerts": 4,
  "categories": {
    "Severe Weather Alert": 5,
    "Winter Weather Alert": 44,
    "Flood Alert": 23,
    "Marine Alert": 67
  },
  "total_unenriched": 358
}
```

---

## 📊 System Monitoring & Health Endpoints

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
  },
  "ingestion": {
    "last_nws_ingestion": "2025-06-03T15:45:00Z",
    "last_spc_ingestion": "2025-06-03T14:30:00Z",
    "failed_jobs_24h": 0
  },
  "system": {
    "environment": "replit",
    "python_version": "3.11",
    "framework": "flask+sqlalchemy"
  },
  "scheduler_operations": {
    "total_operations_24h": 48,
    "successful_operations_24h": 47,
    "failed_operations_24h": 1
  }
}
```

### System Metrics
```
GET /internal/metrics
```
**Description**: Basic alert metrics for monitoring

**Response**:
```json
{
  "total_alerts": 1250,
  "enriched_alerts": 892,
  "active_alerts": 15,
  "recent_24h": 89,
  "recent_7d": 456
}
```

### Autonomous Scheduler Status
```
GET /internal/scheduler/status
```
**Description**: Get autonomous scheduler status with countdown information

**Response**:
```json
{
  "success": true,
  "scheduler": {
    "running": true,
    "thread_alive": true,
    "last_nws_poll": "2025-06-03T16:00:00Z",
    "last_spc_poll": "2025-06-03T15:30:00Z",
    "last_matching": "2025-06-03T15:45:00Z",
    "intervals": {
      "nws_minutes": 5,
      "spc_minutes": 30,
      "matching_minutes": 15
    },
    "next_operation": "nws",
    "next_countdown": 180,
    "nws_countdown": 180,
    "spc_countdown": 1620,
    "match_countdown": 720
  }
}
```

---

## 📋 Ingestion & Operation Logs

### Get Ingestion Logs
```
GET /ingestion-logs/data
```
**Description**: API endpoint for ingestion operation logs

**Query Parameters**:
- `hours` (int, default: 24) - Time window for logs
- `operation_type` (string) - Filter by: "nws_poll", "spc_poll", "spc_match"
- `success` (string) - Filter by success status: "true", "false"

**Response**:
```json
{
  "summary": {
    "success_count": 47,
    "error_count": 1,
    "total_processed": 1250,
    "total_new": 89
  },
  "logs": [
    {
      "started_at": "2025-06-03T15:45:00Z",
      "completed_at": "2025-06-03T15:45:15Z",
      "operation_type": "nws_poll",
      "trigger_method": "internal_timer",
      "success": true,
      "records_processed": 25,
      "records_new": 3,
      "error_message": null,
      "duration": 15.2
    }
  ]
}
```

### View Ingestion Logs (Web Interface)
```
GET /ingestion-logs
```
**Description**: Web interface for browsing ingestion logs

---

## 🔔 Real-Time Webhook System

### Overview

HailyDB's webhook system provides real-time notifications for weather events meeting specific criteria. Perfect for insurance claims, field operations, and emergency response systems.

### Register Webhook Rule
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

**Response**:
```json
{
  "success": true,
  "rule_id": 123,
  "webhook_url": "https://your-app.com/webhooks/weather-alerts",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX",
  "user_id": "your_application_id",
  "created_at": "2025-06-10T20:15:00Z",
  "status": "active"
}
```

### List Webhook Rules
```
GET /internal/webhook-rules
```
**Description**: Get all registered webhook rules

**Response**:
```json
{
  "webhook_rules": [
    {
      "id": 123,
      "webhook_url": "https://your-app.com/webhooks/hail-alerts",
      "event_type": "hail",
      "threshold_value": 1.0,
      "location_filter": "TX",
      "user_id": "insurance_app",
      "created_at": "2025-06-10T15:30:00Z",
      "last_triggered": "2025-06-10T20:15:00Z",
      "trigger_count": 4,
      "status": "active"
    },
    {
      "id": 124,
      "webhook_url": "https://your-app.com/webhooks/wind-alerts",
      "event_type": "wind",
      "threshold_value": 60,
      "location_filter": "OK",
      "user_id": "field_ops",
      "created_at": "2025-06-10T16:00:00Z",
      "last_triggered": "2025-06-10T19:45:00Z",
      "trigger_count": 2,
      "status": "active"
    }
  ],
  "total_rules": 2
}
```

### Get Webhook Rule Details
```
GET /internal/webhook-rules/{rule_id}
```
**Description**: Get detailed information about a specific webhook rule

**Response**:
```json
{
  "id": 123,
  "webhook_url": "https://your-app.com/webhooks/hail-alerts",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX",
  "user_id": "insurance_app",
  "created_at": "2025-06-10T15:30:00Z",
  "last_triggered": "2025-06-10T20:15:00Z",
  "trigger_count": 4,
  "status": "active",
  "recent_triggers": [
    {
      "alert_id": "urn:oid:2.49.0.1.840.0...",
      "triggered_at": "2025-06-10T20:15:00Z",
      "trigger_value": 1.25,
      "delivery_status": "delivered"
    }
  ]
}
```

### Delete Webhook Rule
```
DELETE /internal/webhook-rules/{rule_id}
```
**Description**: Remove a webhook rule

**Response**:
```json
{
  "success": true,
  "message": "Webhook rule 123 deleted successfully"
}
```

### Test Webhook Evaluation
```
POST /internal/webhook-test
```
**Description**: Test webhook evaluation and dispatch system

**Request Body**:
```json
{
  "alert_id": "urn:oid:2.49.0.1.840.0.example",
  "dry_run": true
}
```

**Response**:
```json
{
  "success": true,
  "alert_processed": true,
  "webhooks_evaluated": 2,
  "webhooks_triggered": 1,
  "webhooks_dispatched": 1,
  "results": [
    {
      "rule_id": 123,
      "triggered": true,
      "trigger_reason": "hail_size_1.25_exceeds_threshold_1.0",
      "delivery_status": "delivered",
      "response_code": 200
    }
  ]
}
```

## 📦 Webhook Payload Examples

### Hail Event Notification
When a Severe Thunderstorm Warning contains radar-indicated hail ≥ threshold:

```json
{
  "webhook_rule_id": 123,
  "trigger_type": "hail",
  "trigger_value": 1.25,
  "threshold_met": true,
  "threshold_value": 1.0,
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0.example",
    "event": "Severe Thunderstorm Warning",
    "severity": "Moderate",
    "area_desc": "Harris, TX; Montgomery, TX",
    "effective": "2025-06-10T20:15:00Z",
    "expires": "2025-06-10T21:00:00Z",
    "radar_indicated": {
      "hail_inches": 1.25,
      "wind_mph": 65
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
    "coverage_area_sq_degrees": 0.125,
    "ai_summary": "Severe thunderstorm with quarter-size hail affecting Harris and Montgomery counties.",
    "ai_tags": ["hail", "property_damage_risk"]
  },
  "location_match": {
    "filter": "TX",
    "matched_states": ["TX"],
    "matched_counties": ["Harris", "Montgomery"]
  },
  "timestamp": "2025-06-10T20:15:30Z"
}
```

### Wind Event Notification
When radar-indicated wind speed ≥ threshold:

```json
{
  "webhook_rule_id": 124,
  "trigger_type": "wind",
  "trigger_value": 70,
  "threshold_met": true,
  "threshold_value": 60,
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0.example",
    "event": "Severe Thunderstorm Warning",
    "radar_indicated": {
      "wind_mph": 70,
      "hail_inches": 0.88
    },
    "affected_states": ["OK"],
    "spc_verified": true,
    "spc_confidence_score": 0.92
  },
  "timestamp": "2025-06-10T20:16:45Z"
}
```

## 🌀 Hurricane Track Endpoints

### Get Hurricane Tracks
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
- `limit` (int, max: 1000, default: 100) - Results limit
- `offset` (int, default: 0) - Results offset for pagination

**Example**:
```
GET /api/hurricane-tracks?year=2020&landfall_only=true&category_min=3
```

**Response**:
```json
{
  "tracks": [
    {
      "id": 12345,
      "storm_id": "AL142020",
      "name": "Laura",
      "timestamp": "2020-08-27T06:00:00Z",
      "lat": 29.8,
      "lon": -93.3,
      "status": "HU",
      "category": "Cat4",
      "wind_mph": 150,
      "pressure_mb": 938,
      "distance_to_us_miles": 0,
      "landfall_approach": true,
      "created_at": "2025-06-10T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 1250,
    "limit": 100,
    "offset": 0,
    "has_more": true
  },
  "filters": {
    "year": 2020,
    "landfall_only": true,
    "category_min": 3
  },
  "summary": {
    "storms_found": 8,
    "track_points": 156,
    "landfall_storms": 8,
    "max_category": "Cat5"
  }
}
```

### Get Hurricane Storm Details
```
GET /api/hurricane-tracks/{storm_id}
```
**Description**: Get complete track data for a specific storm

**Example**:
```
GET /api/hurricane-tracks/AL142020
```

**Response**:
```json
{
  "storm_info": {
    "storm_id": "AL142020",
    "name": "Laura",
    "year": 2020,
    "max_category": "Cat4",
    "max_wind_mph": 150,
    "min_pressure_mb": 938,
    "landfall_location": "Cameron Parish, LA",
    "landfall_time": "2020-08-27T06:00:00Z",
    "total_track_points": 42,
    "duration_hours": 168
  },
  "track_points": [
    {
      "timestamp": "2020-08-20T18:00:00Z",
      "lat": 16.2,
      "lon": -34.5,
      "status": "TD",
      "category": "TD",
      "wind_mph": 35,
      "pressure_mb": 1008,
      "distance_to_us_miles": 2450
    },
    {
      "timestamp": "2020-08-27T06:00:00Z",
      "lat": 29.8,
      "lon": -93.3,
      "status": "HU",
      "category": "Cat4",
      "wind_mph": 150,
      "pressure_mb": 938,
      "distance_to_us_miles": 0,
      "landfall_approach": true
    }
  ]
}
```

### Search Hurricanes by Location
```
GET /api/hurricane-tracks/search-location
```
**Description**: Find hurricanes that passed near a specific location

**Query Parameters**:
- `lat` (float, required) - Latitude
- `lon` (float, required) - Longitude
- `radius` (float, default: 50) - Search radius in miles
- `year` (int) - Filter by year
- `category_min` (int) - Minimum hurricane category

**Example**:
```
GET /api/hurricane-tracks/search-location?lat=29.7604&lon=-95.3698&radius=100&category_min=2
```

**Response**:
```json
{
  "search_location": {
    "lat": 29.7604,
    "lon": -95.3698,
    "radius_miles": 100
  },
  "hurricanes_found": [
    {
      "storm_id": "AL142020",
      "name": "Laura",
      "year": 2020,
      "max_category": "Cat4",
      "closest_approach": {
        "distance_miles": 85.2,
        "timestamp": "2020-08-27T06:00:00Z",
        "lat": 29.8,
        "lon": -93.3,
        "wind_mph": 150,
        "category": "Cat4"
      },
      "potential_impact": "high"
    }
  ],
  "total_found": 3,
  "risk_assessment": {
    "historical_risk_level": "high",
    "category_4_or_5_count": 1,
    "landfall_within_radius": 2
  }
}
```

### Trigger Hurricane Data Ingestion
```
POST /internal/hurricane-ingest
```
**Description**: Admin endpoint to trigger hurricane data ingestion

**Response**:
```json
{
  "success": true,
  "ingestion_stats": {
    "total_storms_processed": 15,
    "total_track_points": 1250,
    "new_track_points": 45,
    "updated_track_points": 12,
    "landfall_storms": 8,
    "processing_time_seconds": 25.6
  },
  "message": "Hurricane data ingestion completed successfully"
}
```

### Get Hurricane Statistics
```
GET /api/hurricane-tracks/stats
```
**Description**: Get hurricane track ingestion and coverage statistics

**Response**:
```json
{
  "coverage": {
    "total_storms": 156,
    "total_track_points": 12450,
    "years_covered": "2020-2025",
    "landfall_storms": 45,
    "category_5_storms": 8
  },
  "recent_activity": {
    "last_ingestion": "2025-06-10T10:00:00Z",
    "storms_added_24h": 2,
    "track_points_added_24h": 48
  },
  "data_quality": {
    "completeness_percentage": 98.5,
    "us_impact_coverage": 100.0,
    "coordinate_accuracy": "high"
  }
}
```

---

## 🔧 Administrative Endpoints

### Manual Ingestion Trigger
```
POST /internal/cron
```
**Description**: Manually trigger ingestion operations

**Request Body**:
```json
{
  "action": "trigger"
}
```

**Response**:
```json
{
  "status": "triggered",
  "ingested_count": 25
}
```

### Start Autonomous Scheduler
```
POST /internal/scheduler/start
```
**Response**:
```json
{
  "success": true,
  "status": "running",
  "message": "Autonomous scheduler started"
}
```

### Stop Autonomous Scheduler
```
POST /internal/scheduler/stop
```
**Response**:
```json
{
  "success": true,
  "status": "stopped",
  "message": "Autonomous scheduler stopped"
}
```

### SPC Data Ingestion
```
POST /internal/spc-ingest
```
**Description**: Trigger systematic SPC report ingestion (T-0 through T-15 days)

**Response**:
```json
{
  "success": true,
  "total_reports": 245,
  "dates_polled": 8,
  "results": [
    {
      "date": "2025-06-03",
      "reports": 0,
      "status": "completed"
    }
  ],
  "message": "Systematic SPC ingestion completed: 245 reports processed across 8 dates"
}
```

### SPC Data Backfill
```
POST /internal/spc-backfill
```
**Description**: Force backfill SPC data for specific date range

**Request Body**:
```json
{
  "start_date": "2025-05-01",
  "end_date": "2025-05-31"
}
```

**Response**:
```json
{
  "success": true,
  "total_reports": 1250,
  "dates_processed": 31,
  "results": [
    {
      "date": "2025-05-01",
      "reports": 45,
      "status": "completed"
    }
  ],
  "message": "Backfill completed: 1250 reports processed across 31 dates"
}
```

### SPC Matching
```
POST /internal/spc-match
```
**Description**: Trigger SPC report matching with NWS alerts

**Response**:
```json
{
  "success": true,
  "processed": 100,
  "matched": 15,
  "message": "SPC matching completed: 15/100 alerts matched"
}
```

### Generate AI Summaries for Verified Matches
```
POST /internal/spc-generate-summaries
```
**Description**: Generate AI summaries for verified matches without summaries

**Response**:
```json
{
  "success": true,
  "message": "Generated 12 AI summaries for verified matches",
  "generated": 12,
  "total_processed": 50
}
```

### Generate Single AI Summary
```
POST /internal/spc-generate-summary/{alert_id}
```
**Description**: Generate AI summary for specific verified alert match

**Response**:
```json
{
  "success": true,
  "message": "AI summary generated successfully",
  "summary": "The Tornado Warning for Ford County was verified by an EF1 tornado report..."
}
```

### Force Re-upload SPC Data
```
POST /internal/spc-reupload/{date}
```
**Description**: Force re-ingestion of SPC data for specific date

**Parameters**: 
- `date` (string, YYYY-MM-DD) - Date to re-upload

**Response**:
```json
{
  "success": true,
  "message": "SPC data re-uploaded for 2025-06-01",
  "reports_processed": 25
}
```

### Enrich All Priority Alerts
```
POST /internal/enrich-all-priority
```
**Description**: Comprehensive enrichment of all priority alerts in database

**Response**:
```json
{
  "success": true,
  "message": "Successfully enriched 156 priority alerts from database",
  "enriched": 156,
  "failed": 2,
  "total_processed": 158,
  "priority_types": ["Tornado Warning", "Tornado Watch", "Severe Thunderstorm Warning"]
}
```

---

## 🔍 Data Verification Endpoints

### SPC Data Verification
```
GET /internal/spc-verify
```
**Description**: Web interface for SPC data integrity verification

**Query Parameters**:
- `start_date` (string, YYYY-MM-DD) - Start date for verification
- `end_date` (string, YYYY-MM-DD) - End date for verification
- `days` (int, default: 7) - Number of days to verify (if dates not provided)
- `format` (string) - Set to "json" for API response

### Today's SPC Verification
```
GET /internal/spc-verify-today
```
**Description**: Get recent SPC verification data for dashboard

**Response**:
```json
{
  "status": "success",
  "results": [
    {
      "date": "2025-06-03",
      "hailydb_count": 0,
      "spc_live_count": 0,
      "match_status": "MATCH"
    },
    {
      "date": "2025-06-02",
      "hailydb_count": 25,
      "spc_live_count": 28,
      "match_status": "MISMATCH"
    }
  ],
  "last_updated": "2025-06-03T16:00:00Z"
}
```

---

## 📱 Web Interface Endpoints

### Main Dashboard
```
GET /
GET /internal/dashboard
```
**Description**: Administrative dashboard with system overview

### View Alerts
```
GET /alerts
```
**Description**: Web interface for browsing and filtering alerts

### View Alert Details
```
GET /alerts/{alert_id}
```
**Description**: Detailed view of individual alert with SPC verification data

### Manual Alert Enrichment
```
POST /alerts/enrich/{alert_id}
```
**Description**: Re-run AI enrichment for specific alert (form submission)

---

## 📈 Error Responses

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (alert/resource not found)
- `500` - Internal Server Error

**Error Response Format**:
```json
{
  "status": "error",
  "message": "Detailed error description",
  "error": "Technical error details"
}
```

---

## 🔍 Data Models

### Alert Object
```json
{
  "id": "string",
  "event": "string",
  "severity": "string",
  "area_desc": "string", 
  "effective": "ISO8601 datetime",
  "expires": "ISO8601 datetime",
  "sent": "ISO8601 datetime",
  "geometry": "GeoJSON geometry",
  "properties": "object",
  "raw": "object",
  "ai_summary": "string",
  "ai_tags": ["string"],
  "spc_verified": "boolean",
  "spc_reports": ["object"],
  "spc_ai_summary": "string",
  "spc_confidence_score": "float",
  "spc_report_count": "integer",
  "ingested_at": "ISO8601 datetime"
}
```

### SPC Report Object
```json
{
  "id": "integer",
  "report_type": "string",
  "report_date": "YYYY-MM-DD",
  "time_utc": "string",
  "location": "string",
  "county": "string",
  "state": "string",
  "lat": "float",
  "lon": "float",
  "f_scale": "string",
  "speed": "string", 
  "size": "string",
  "comments": "string"
}
```

---

## 📊 Rate Limits & Best Practices

- **No rate limits** currently implemented
- **Pagination recommended** for large datasets
- **Use active_only filter** for real-time applications
- **Cache responses** when appropriate for better performance
- **Monitor /internal/status** for system health
- **Use batch enrichment** rather than individual alert enrichment

---

## 🚀 Integration Examples

### Get Current Severe Weather Alerts
```bash
curl "https://your-app.replit.app/api/alerts/search?severity=Severe&active_only=true&limit=50"
```

### Monitor Texas Tornado Activity
```bash
curl "https://your-app.replit.app/api/alerts/by-state/TX?active_only=true" | jq '.alerts[] | select(.event | contains("Tornado"))'
```

### Get Recent SPC Tornado Reports
```bash
curl "https://your-app.replit.app/api/spc/reports?type=tornado&limit=25"
```

### Check System Health
```bash
curl "https://your-app.replit.app/internal/status"
```

---

## 🛠️ Comprehensive Integration Examples

### Insurance Claims Processing System

```python
import requests
import json
from datetime import datetime, timedelta

class InsuranceClaimsAPI:
    def __init__(self, hailydb_base_url, webhook_endpoint):
        self.base_url = hailydb_base_url
        self.webhook_endpoint = webhook_endpoint
        self.setup_damage_monitoring()
    
    def setup_damage_monitoring(self):
        """Register webhooks for property damage events"""
        # Monitor significant hail events
        hail_rule = {
            "webhook_url": f"{self.webhook_endpoint}/hail-damage",
            "event_type": "hail",
            "threshold_value": 0.75,  # 3/4 inch or larger
            "location_filter": "TX,OK,KS,NE",  # High-risk states
            "user_id": "insurance_claims_system"
        }
        
        # Monitor damaging wind events
        wind_rule = {
            "webhook_url": f"{self.webhook_endpoint}/wind-damage",
            "event_type": "wind", 
            "threshold_value": 58,  # Damaging wind threshold
            "location_filter": "TX,OK,KS,NE",
            "user_id": "insurance_claims_system"
        }
        
        for rule in [hail_rule, wind_rule]:
            response = requests.post(f"{self.base_url}/internal/webhook-rules", json=rule)
            print(f"Claims monitoring active: Rule ID {response.json().get('rule_id')}")
    
    def process_damage_webhook(self, webhook_payload):
        """Process incoming damage notification"""
        alert = webhook_payload['alert']
        radar_data = alert.get('radar_indicated', {})
        trigger_type = webhook_payload['trigger_type']
        
        # Calculate damage assessment
        damage_assessment = self.assess_property_damage(radar_data, trigger_type)
        
        # Create claim preparation area
        claim_area = {
            "alert_id": alert['id'],
            "event_type": alert['event'],
            "trigger_data": {
                "type": trigger_type,
                "hail_size": radar_data.get('hail_inches'),
                "wind_speed": radar_data.get('wind_mph')
            },
            "damage_probability": damage_assessment['probability'],
            "affected_counties": alert.get('county_names', []),
            "fips_codes": alert.get('fips_codes', []),
            "coverage_bounds": alert.get('geometry_bounds'),
            "coverage_area": alert.get('coverage_area_sq_degrees', 0),
            "estimated_properties": self.estimate_properties_at_risk(alert),
            "priority_level": damage_assessment['priority'],
            "response_required": damage_assessment['probability'] >= 0.6
        }
        
        if claim_area['response_required']:
            self.initiate_claims_response(claim_area)
        
        return claim_area
    
    def assess_property_damage(self, radar_data, trigger_type):
        """Assess property damage probability and priority"""
        if trigger_type == 'hail':
            hail_size = radar_data.get('hail_inches', 0)
            if hail_size >= 2.0:  # Golf ball or larger
                return {'probability': 0.9, 'priority': 'critical'}
            elif hail_size >= 1.75:  # Half dollar
                return {'probability': 0.8, 'priority': 'high'}
            elif hail_size >= 1.25:  # Half dollar
                return {'probability': 0.6, 'priority': 'medium'}
            elif hail_size >= 1.0:  # Quarter
                return {'probability': 0.4, 'priority': 'medium'}
            else:
                return {'probability': 0.2, 'priority': 'low'}
        
        elif trigger_type == 'wind':
            wind_speed = radar_data.get('wind_mph', 0)
            if wind_speed >= 80:  # Hurricane force
                return {'probability': 0.9, 'priority': 'critical'}
            elif wind_speed >= 70:  # Significant damage
                return {'probability': 0.7, 'priority': 'high'}
            elif wind_speed >= 58:  # Damaging winds
                return {'probability': 0.5, 'priority': 'medium'}
            else:
                return {'probability': 0.2, 'priority': 'low'}
        
        return {'probability': 0.1, 'priority': 'low'}
```

### Emergency Management Integration

```javascript
class EmergencyResponseSystem {
    constructor(hailydbBaseUrl, emergencyDispatchApi) {
        this.baseUrl = hailydbBaseUrl;
        this.dispatchApi = emergencyDispatchApi;
        this.activeThreats = new Map();
        this.setupEmergencyMonitoring();
    }
    
    async setupEmergencyMonitoring() {
        // Monitor high-impact severe weather
        const severeWeatherRule = {
            webhook_url: `${this.dispatchApi}/severe-weather-alerts`,
            event_type: "damage_probability",
            threshold_value: 0.7,  // High damage probability
            user_id: "emergency_management"
        };
        
        // Monitor tornado events specifically
        const tornadoRule = {
            webhook_url: `${this.dispatchApi}/tornado-emergency`,
            event_type: "hail",  // Tornado warnings often have hail
            threshold_value: 1.5,  // Large hail indicates strong updrafts
            user_id: "emergency_management"
        };
        
        await Promise.all([
            this.registerWebhook(severeWeatherRule),
            this.registerWebhook(tornadoRule)
        ]);
    }
    
    async processEmergencyAlert(webhookPayload) {
        const alert = webhookPayload.alert;
        const threatAssessment = this.assessEmergencyThreat(alert);
        
        // Store active threat
        this.activeThreats.set(alert.id, {
            alert: alert,
            threat_level: threatAssessment.level,
            activated_at: new Date(),
            status: 'active'
        });
        
        if (threatAssessment.level >= 4) {
            await this.activateEmergencyProtocols(alert, threatAssessment);
        }
        
        await this.updateSituationalAwareness(alert, threatAssessment);
        await this.notifyEmergencyPersonnel(alert, threatAssessment);
    }
    
    assessEmergencyThreat(alert) {
        let threatScore = 0;
        const radarData = alert.radar_indicated || {};
        
        // Event type assessment
        if (alert.event.includes('Tornado')) threatScore += 4;
        else if (alert.event.includes('Severe Thunderstorm')) threatScore += 2;
        
        // Radar data assessment
        const hailSize = radarData.hail_inches || 0;
        if (hailSize >= 2.0) threatScore += 3;
        else if (hailSize >= 1.0) threatScore += 2;
        
        const windSpeed = radarData.wind_mph || 0;
        if (windSpeed >= 80) threatScore += 3;
        else if (windSpeed >= 58) threatScore += 2;
        
        // Population impact assessment
        const countyCount = alert.county_names?.length || 1;
        if (countyCount >= 3) threatScore += 1;
        
        // SPC verification bonus
        if (alert.spc_verified && alert.spc_confidence_score >= 0.8) {
            threatScore += 1;
        }
        
        const level = Math.min(threatScore, 5);
        return {
            level: level,
            category: this.getThreatCategory(level),
            response_required: level >= 3,
            evacuation_considered: level >= 4
        };
    }
    
    getThreatCategory(level) {
        const categories = {
            1: 'minimal',
            2: 'low', 
            3: 'moderate',
            4: 'high',
            5: 'extreme'
        };
        return categories[level] || 'unknown';
    }
}
```

### Field Operations Dispatch System

```python
class FieldOperationsManager:
    def __init__(self, hailydb_url, dispatch_system_url):
        self.hailydb_url = hailydb_url
        self.dispatch_url = dispatch_system_url
        self.active_operations = {}
        self.team_locations = {}
    
    def setup_field_monitoring(self):
        """Setup monitoring for field-actionable damage events"""
        monitoring_rules = [
            {
                "webhook_url": f"{self.dispatch_url}/wind-damage-dispatch",
                "event_type": "wind",
                "threshold_value": 60,  # Structural damage threshold
                "user_id": "field_operations"
            },
            {
                "webhook_url": f"{self.dispatch_url}/hail-damage-dispatch", 
                "event_type": "hail",
                "threshold_value": 1.0,  # Property damage threshold
                "user_id": "field_operations"
            }
        ]
        
        for rule in monitoring_rules:
            response = requests.post(f"{self.hailydb_url}/internal/webhook-rules", json=rule)
            rule_id = response.json().get('rule_id')
            print(f"Field monitoring rule {rule['event_type']}: {rule_id}")
    
    def process_field_dispatch(self, webhook_payload):
        """Process webhook for field team dispatch"""
        alert = webhook_payload['alert']
        trigger_type = webhook_payload['trigger_type']
        
        # Create comprehensive dispatch plan
        dispatch_plan = self.create_dispatch_plan(alert, trigger_type)
        
        # Determine deployment strategy
        if dispatch_plan['priority'] == 'critical':
            self.deploy_emergency_response_teams(dispatch_plan)
        elif dispatch_plan['priority'] == 'high':
            self.deploy_rapid_assessment_teams(dispatch_plan)
        else:
            self.schedule_routine_assessment(dispatch_plan)
        
        # Track active operation
        self.active_operations[alert['id']] = {
            'plan': dispatch_plan,
            'status': 'dispatched',
            'started_at': datetime.utcnow(),
            'teams_assigned': dispatch_plan['team_assignments']
        }
        
        return dispatch_plan
    
    def create_dispatch_plan(self, alert, trigger_type):
        """Create comprehensive field operations dispatch plan"""
        geometry_bounds = alert.get('geometry_bounds', {})
        county_names = alert.get('county_names', [])
        radar_data = alert.get('radar_indicated', {})
        
        # Calculate operational center
        center_coords = self.calculate_operational_center(geometry_bounds)
        
        # Assess operational requirements
        operational_assessment = self.assess_operational_requirements(
            radar_data, trigger_type, county_names
        )
        
        plan = {
            "alert_id": alert['id'],
            "operation_type": f"{trigger_type}_damage_assessment",
            "trigger_details": {
                "type": trigger_type,
                "value": webhook_payload.get('trigger_value'),
                "radar_data": radar_data
            },
            "operational_center": center_coords,
            "affected_areas": {
                "counties": [f"{c['county']}, {c['state']}" for c in county_names],
                "fips_codes": alert.get('fips_codes', []),
                "coverage_area_sq_degrees": alert.get('coverage_area_sq_degrees', 0)
            },
            "priority": operational_assessment['priority'],
            "estimated_response_time": operational_assessment['response_time'],
            "team_requirements": operational_assessment['teams'],
            "equipment_manifest": operational_assessment['equipment'],
            "safety_considerations": operational_assessment['safety'],
            "expected_duration_hours": operational_assessment['duration']
        }
        
        return plan
    
    def assess_operational_requirements(self, radar_data, trigger_type, counties):
        """Assess operational requirements for field deployment"""
        if trigger_type == 'hail':
            hail_size = radar_data.get('hail_inches', 0)
            if hail_size >= 2.0:
                return {
                    'priority': 'critical',
                    'response_time': 30,  # minutes
                    'teams': ['damage_assessment', 'structural_engineer', 'safety'],
                    'equipment': ['drones', 'measurement_tools', 'documentation'],
                    'safety': ['protective_gear', 'communication'],
                    'duration': 8
                }
            elif hail_size >= 1.25:
                return {
                    'priority': 'high',
                    'response_time': 60,
                    'teams': ['damage_assessment', 'documentation'],
                    'equipment': ['drones', 'measurement_tools'],
                    'safety': ['protective_gear'],
                    'duration': 6
                }
        
        elif trigger_type == 'wind':
            wind_speed = radar_data.get('wind_mph', 0)
            if wind_speed >= 75:
                return {
                    'priority': 'critical',
                    'response_time': 20,
                    'teams': ['damage_assessment', 'structural_engineer', 'safety', 'utilities'],
                    'equipment': ['drones', 'wind_meters', 'chainsaws', 'generators'],
                    'safety': ['protective_gear', 'communication', 'first_aid'],
                    'duration': 12
                }
        
        # Default moderate response
        return {
            'priority': 'medium',
            'response_time': 120,
            'teams': ['damage_assessment'],
            'equipment': ['documentation'],
            'safety': ['communication'],
            'duration': 4
        }
```

### Real-Time Monitoring Dashboard

```javascript
class HailyDBRealtimeDashboard {
    constructor(apiBaseUrl) {
        this.apiUrl = apiBaseUrl;
        this.webhookHandlers = new Map();
        this.alertCache = new Map();
        this.updateIntervals = new Map();
        this.initialize();
    }
    
    async initialize() {
        await this.setupWebhookSystem();
        await this.loadInitialData();
        this.startPeriodicUpdates();
        this.setupEventListeners();
    }
    
    async setupWebhookSystem() {
        // Register comprehensive webhook monitoring
        const webhookConfigs = [
            {
                webhook_url: `${window.location.origin}/webhooks/dashboard/severe-weather`,
                event_type: "hail",
                threshold_value: 0.75,
                user_id: "realtime_dashboard"
            },
            {
                webhook_url: `${window.location.origin}/webhooks/dashboard/wind-damage`,
                event_type: "wind",
                threshold_value: 58,
                user_id: "realtime_dashboard"
            }
        ];
        
        for (const config of webhookConfigs) {
            try {
                const response = await fetch(`${this.apiUrl}/internal/webhook-rules`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                
                const result = await response.json();
                console.log(`Dashboard webhook registered: ${result.rule_id} for ${config.event_type}`);
            } catch (error) {
                console.error(`Failed to register webhook for ${config.event_type}:`, error);
            }
        }
    }
    
    async loadInitialData() {
        try {
            // Load active alerts
            const activeResponse = await fetch(`${this.apiUrl}/api/alerts/active`);
            const activeData = await activeResponse.json();
            this.displayActiveAlerts(activeData.alerts);
            
            // Load recent SPC matches
            const spcResponse = await fetch(`${this.apiUrl}/spc-matches/data?hours=24`);
            const spcData = await spcResponse.json();
            this.displaySPCMatches(spcData.matches);
            
            // Load system status
            const statusResponse = await fetch(`${this.apiUrl}/internal/status`);
            const statusData = await statusResponse.json();
            this.displaySystemStatus(statusData);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showErrorMessage('Failed to load dashboard data');
        }
    }
    
    async processRealtimeWebhook(webhookPayload) {
        const alert = webhookPayload.alert;
        const triggerType = webhookPayload.trigger_type;
        
        // Update alert cache
        this.alertCache.set(alert.id, {
            ...alert,
            webhook_triggered: true,
            trigger_type: triggerType,
            trigger_value: webhookPayload.trigger_value,
            received_at: new Date()
        });
        
        // Update displays with animation
        this.updateAlertDisplayAnimated(alert);
        this.updateRadarDataDisplay(alert.radar_indicated);
        this.updateGeographicDisplay(alert);
        
        // Show real-time notification
        this.showRealtimeNotification(webhookPayload);
        
        // Update statistics
        this.updateDashboardStatistics();
    }
    
    displayActiveAlerts(alerts) {
        const container = document.getElementById('active-alerts-grid');
        container.innerHTML = '';
        
        alerts.forEach(alert => {
            const alertCard = this.createEnhancedAlertCard(alert);
            container.appendChild(alertCard);
        });
        
        // Update alert count
        document.getElementById('active-alert-count').textContent = alerts.length;
    }
    
    createEnhancedAlertCard(alert) {
        const card = document.createElement('div');
        card.className = `alert-card severity-${alert.severity.toLowerCase()}`;
        card.dataset.alertId = alert.id;
        
        const radarData = alert.radar_indicated || {};
        const hasRadarData = radarData.hail_inches || radarData.wind_mph;
        const isWebhookTriggered = this.alertCache.get(alert.id)?.webhook_triggered;
        
        card.innerHTML = `
            <div class="alert-header">
                <h3>${alert.event}</h3>
                <div class="alert-badges">
                    <span class="severity-badge severity-${alert.severity.toLowerCase()}">${alert.severity}</span>
                    ${alert.spc_verified ? '<span class="spc-badge">SPC ✓</span>' : ''}
                    ${isWebhookTriggered ? '<span class="webhook-badge">Live</span>' : ''}
                </div>
            </div>
            
            <div class="alert-details">
                <div class="location-info">
                    <strong>Area:</strong> ${alert.area_desc}
                </div>
                
                <div class="time-info">
                    <div><strong>Effective:</strong> ${this.formatTime(alert.effective)}</div>
                    <div><strong>Expires:</strong> ${this.formatTime(alert.expires)}</div>
                </div>
                
                ${hasRadarData ? `
                    <div class="radar-data">
                        <h4>Radar Indicated:</h4>
                        <div class="radar-measurements">
                            ${radarData.hail_inches ? `
                                <div class="measurement hail">
                                    <span class="value">${radarData.hail_inches}"</span>
                                    <span class="label">Hail</span>
                                </div>
                            ` : ''}
                            ${radarData.wind_mph ? `
                                <div class="measurement wind">
                                    <span class="value">${radarData.wind_mph}</span>
                                    <span class="label">mph Wind</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
                
                ${alert.fips_codes && alert.fips_codes.length > 0 ? `
                    <div class="geographic-data">
                        <strong>FIPS:</strong> ${alert.fips_codes.slice(0, 3).join(', ')}
                        ${alert.fips_codes.length > 3 ? `+${alert.fips_codes.length - 3}` : ''}
                    </div>
                ` : ''}
                
                ${alert.ai_summary ? `
                    <div class="ai-summary">
                        <strong>AI Summary:</strong> ${alert.ai_summary}
                    </div>
                ` : ''}
            </div>
            
            <div class="alert-actions">
                <button onclick="window.open('/alerts/${alert.id}', '_blank')" class="btn-details">
                    View Details
                </button>
            </div>
        `;
        
        return card;
    }
    
    formatTime(isoString) {
        return new Date(isoString).toLocaleString();
    }
    
    showRealtimeNotification(webhookPayload) {
        const notification = document.createElement('div');
        notification.className = 'realtime-notification';
        
        const alert = webhookPayload.alert;
        const triggerType = webhookPayload.trigger_type;
        const triggerValue = webhookPayload.trigger_value;
        
        notification.innerHTML = `
            <div class="notification-header">
                <strong>Real-Time Alert</strong>
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="notification-content">
                <div><strong>${alert.event}</strong></div>
                <div>${alert.area_desc}</div>
                <div class="trigger-info">
                    ${triggerType === 'hail' ? `Hail: ${triggerValue}"` : `Wind: ${triggerValue} mph`}
                </div>
            </div>
        `;
        
        document.getElementById('notifications-container').appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 10000);
    }
}
```

## 🔒 Security and Authentication Best Practices

### Webhook Security Implementation

```python
import hashlib
import hmac
import time

class WebhookSecurityHandler:
    def __init__(self, webhook_secret):
        self.webhook_secret = webhook_secret
    
    def verify_webhook_signature(self, payload, signature, timestamp):
        """Verify webhook payload authenticity and freshness"""
        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:  # 5 minutes tolerance
            return False
        
        # Verify signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            f"{timestamp}.{payload}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)

@app.route('/webhooks/weather-alerts', methods=['POST'])
def handle_secure_webhook():
    signature = request.headers.get('X-HailyDB-Signature')
    timestamp = request.headers.get('X-HailyDB-Timestamp')
    payload = request.get_data(as_text=True)
    
    security_handler = WebhookSecurityHandler(WEBHOOK_SECRET)
    
    if not security_handler.verify_webhook_signature(payload, signature, timestamp):
        abort(401, 'Invalid webhook signature')
    
    # Process verified webhook
    webhook_data = request.json
    process_weather_alert.delay(webhook_data)  # Async processing
    
    return '', 200
```

## 📊 Advanced Query Patterns

### Complex Filtering Examples

```bash
# Get all severe weather alerts with radar data in tornado alley states
curl "https://your-hailydb.com/api/alerts/search?state=TX,OK,KS,NE&severity=Severe,Extreme&active_only=true&limit=50" \
  | jq '.alerts[] | select(.radar_indicated != null)'

# Find hail events above damage threshold with SPC verification
curl "https://your-hailydb.com/api/alerts/search?event_type=Severe%20Thunderstorm%20Warning&limit=100" \
  | jq '.alerts[] | select(.radar_indicated.hail_inches >= 1.0 and .spc_verified == true)'

# Get hurricane tracks for specific storm
curl "https://your-hailydb.com/api/hurricane-tracks/AL142020" \
  | jq '.track_points[] | select(.category | contains("Cat"))'

# Find recent wind damage events by county
curl "https://your-hailydb.com/api/alerts/by-county/TX/Harris?active_only=false" \
  | jq '.alerts[] | select(.radar_indicated.wind_mph >= 58)'
```

### Bulk Operations

```python
def bulk_alert_processing(hailydb_url, state_list, event_types):
    """Process alerts in bulk for multiple states and event types"""
    all_alerts = []
    
    for state in state_list:
        for event_type in event_types:
            params = {
                'state': state,
                'event_type': event_type,
                'active_only': 'true',
                'limit': 100
            }
            
            response = requests.get(f"{hailydb_url}/api/alerts/search", params=params)
            if response.status_code == 200:
                alerts = response.json().get('alerts', [])
                all_alerts.extend(alerts)
    
    return all_alerts

# Usage
states = ['TX', 'OK', 'KS', 'NE', 'IA']
events = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Tornado Watch']
alerts = bulk_alert_processing("https://your-hailydb.com", states, events)
```

## 🚨 Error Handling and Resilience

### Comprehensive Error Handling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

class HailyDBClient:
    def __init__(self, base_url, timeout=30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_resilient_session()
        
    def _create_resilient_session(self):
        """Create session with automatic retries and error handling"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_alerts_with_fallback(self, **params):
        """Get alerts with comprehensive error handling"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/alerts/search",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logging.warning("Rate limit exceeded, implementing backoff")
                time.sleep(60)
                return self.get_alerts_with_fallback(**params)
            else:
                logging.error(f"API error: {response.status_code} - {response.text}")
                return {"alerts": [], "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logging.error("Request timeout")
            return {"alerts": [], "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logging.error("Connection error")
            return {"alerts": [], "error": "Connection failed"}
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return {"alerts": [], "error": str(e)}
```

---

## 📈 Performance Optimization Guidelines

### Rate Limiting and Throttling

- **API Rate Limits**: 100 requests/minute for search endpoints
- **Webhook Management**: 20 requests/minute for webhook operations
- **Use webhook notifications** instead of polling for real-time updates
- **Implement client-side caching** for frequently accessed data
- **Batch requests** when possible to reduce API calls

### Efficient Data Retrieval

```python
# Efficient: Use specific filters
params = {
    'state': 'TX',
    'event_type': 'Severe Thunderstorm Warning',
    'active_only': 'true',
    'limit': 25
}
response = requests.get(f"{base_url}/api/alerts/search", params=params)

# Less efficient: Broad queries requiring client filtering
response = requests.get(f"{base_url}/api/alerts/search?limit=1000")
filtered_alerts = [a for a in response.json()['alerts'] if a['state'] == 'TX']
```

---

*Last Updated: June 2025*
*HailyDB v2.0 Enhanced - Complete API Documentation for Insurance, Field Operations, and Emergency Management Applications*
